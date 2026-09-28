import os
import html
import logging
import requests

from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Application,
    CommandHandler,
    InlineQueryHandler,
    ContextTypes,
)

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

LANGUAGE = "pt-BR"

# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# VERIFICAÇÃO DAS CHAVES
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("A variável BOT_TOKEN não foi configurada.")

if not TMDB_TOKEN:
    raise RuntimeError("A variável TMDB_TOKEN não foi configurada.")


# ============================================================
# CABEÇALHOS TMDB
# ============================================================

TMDB_HEADERS = {
    "Authorization": f"Bearer {TMDB_TOKEN}",
    "accept": "application/json",
}


# ============================================================
# COMANDOS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = (
        "🎬 <b>NEXFLIX</b>\n\n"
        "🔎 Pesquise filmes e séries usando o modo inline.\n\n"
        "Exemplos:\n"
        "🎬 <code>@NEXFLIX_PEDIDOS_BOT filme Batman</code>\n"
        "📺 <code>@NEXFLIX_PEDIDOS_BOT serie Stranger Things</code>\n\n"
        "Você também pode usar:\n"
        "🎬 <code>@NEXFLIX_PEDIDOS_BOT filme Homem-Aranha</code>\n"
        "📺 <code>@NEXFLIX_PEDIDOS_BOT série The Walking Dead</code>"
    )

    await update.message.reply_text(
        mensagem,
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = (
        "📚 <b>Como pesquisar</b>\n\n"
        "🎬 Filmes:\n"
        "<code>@NEXFLIX_PEDIDOS_BOT filme nome do filme</code>\n\n"
        "📺 Séries:\n"
        "<code>@NEXFLIX_PEDIDOS_BOT serie nome da série</code>"
    )

    await update.message.reply_text(
        mensagem,
        parse_mode="HTML",
    )


# ============================================================
# PESQUISA NO TMDB
# ============================================================

def pesquisar_tmdb(tipo, consulta):
    """
    tipo:
        movie = filme
        tv = série
    """

    if tipo not in ("movie", "tv"):
        return []

    url = f"{TMDB_BASE_URL}/search/{tipo}"

    params = {
        "query": consulta,
        "language": LANGUAGE,
        "include_adult": "false",
        "page": 1,
    }

    try:
        resposta = requests.get(
            url,
            headers=TMDB_HEADERS,
            params=params,
            timeout=15,
        )

        resposta.raise_for_status()

        dados = resposta.json()

        return dados.get("results", [])

    except requests.RequestException as erro:
        logger.error(f"Erro ao consultar TMDB: {erro}")
        return []

    except Exception as erro:
        logger.error(f"Erro inesperado no TMDB: {erro}")
        return []


# ============================================================
# FORMATAÇÃO
# ============================================================

def obter_titulo(item, tipo):
    if tipo == "movie":
        return item.get("title") or "Sem título"

    return item.get("name") or "Sem título"


def obter_data(item, tipo):
    if tipo == "movie":
        return item.get("release_date") or ""

    return item.get("first_air_date") or ""


def obter_ano(item, tipo):
    data = obter_data(item, tipo)

    if data and len(data) >= 4:
        return data[:4]

    return "N/A"


def obter_descricao(item):
    descricao = item.get("overview")

    if not descricao:
        return "Descrição não disponível."

    return descricao


def obter_nota(item):
    nota = item.get("vote_average")

    if nota is None:
        return "N/A"

    try:
        return f"{float(nota):.1f}"
    except Exception:
        return "N/A"


def obter_poster(item):
    poster_path = item.get("poster_path")

    if not poster_path:
        return None

    return TMDB_IMAGE_URL + poster_path


# ============================================================
# TEXTO DO RESULTADO
# ============================================================

def criar_mensagem(item, tipo):
    titulo = html.escape(obter_titulo(item, tipo))
    ano = html.escape(obter_ano(item, tipo))
    descricao = html.escape(obter_descricao(item))
    nota = obter_nota(item)

    if tipo == "movie":
        categoria = "🎬 FILME"
    else:
        categoria = "📺 SÉRIE"

    mensagem = (
        f"<b>{categoria}</b>\n\n"
        f"🎞️ <b>{titulo}</b>\n"
        f"📅 Ano: <b>{ano}</b>\n"
        f"⭐ Nota TMDB: <b>{nota}</b>\n\n"
        f"📝 <b>Descrição:</b>\n"
        f"{descricao}"
    )

    return mensagem


# ============================================================
# INLINE MODE
# ============================================================

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.inline_query.query.strip()

    # --------------------------------------------------------
    # SE NÃO DIGITOU NADA
    # --------------------------------------------------------

    if not query:
        await update.inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True,
        )
        return

    query_lower = query.lower()

    # --------------------------------------------------------
    # IDENTIFICA FILME OU SÉRIE
    # --------------------------------------------------------

    tipo = None
    pesquisa = ""

    comandos_filme = [
        "filme ",
        "filmes ",
        "movie ",
    ]

    comandos_serie = [
        "serie ",
        "série ",
        "series ",
        "séries ",
        "tv ",
    ]

    for comando in comandos_filme:
        if query_lower.startswith(comando):
            tipo = "movie"
            pesquisa = query[len(comando):].strip()
            break

    if tipo is None:
        for comando in comandos_serie:
            if query_lower.startswith(comando):
                tipo = "tv"
                pesquisa = query[len(comando):].strip()
                break

    # --------------------------------------------------------
    # SEM TIPO
    # --------------------------------------------------------

    if tipo is None:
        resultado = InlineQueryResultArticle(
            id="ajuda",
            title="🔎 Como pesquisar",
            description="Use: filme nome ou serie nome",
            input_message_content=InputTextMessageContent(
                message_text=(
                    "🔎 <b>NEXFLIX</b>\n\n"
                    "Para pesquisar filmes:\n"
                    "<code>@NEXFLIX_PEDIDOS_BOT filme Batman</code>\n\n"
                    "Para pesquisar séries:\n"
                    "<code>@NEXFLIX_PEDIDOS_BOT serie Stranger Things</code>"
                ),
                parse_mode="HTML",
            ),
        )

        await update.inline_query.answer(
            results=[resultado],
            cache_time=1,
            is_personal=True,
        )
        return

    # --------------------------------------------------------
    # PESQUISA VAZIA
    # --------------------------------------------------------

    if not pesquisa:
        await update.inline_query.answer(
            results=[],
            cache_time=1,
            is_personal=True,
        )
        return

    # --------------------------------------------------------
    # PESQUISA TMDB
    # --------------------------------------------------------

    resultados_tmdb = pesquisar_tmdb(tipo, pesquisa)

    resultados = []

    # Limita aos 10 primeiros
    resultados_tmdb = resultados_tmdb[:10]

    for item in resultados_tmdb:

        tmdb_id = item.get("id")

        if not tmdb_id:
            continue

        titulo = obter_titulo(item, tipo)
        ano = obter_ano(item, tipo)
        nota = obter_nota(item)
        descricao = obter_descricao(item)
        poster = obter_poster(item)

        mensagem = criar_mensagem(item, tipo)

        # ----------------------------------------------------
        # TÍTULO DO RESULTADO
        # ----------------------------------------------------

        if tipo == "movie":
            emoji = "🎬"
            categoria = "Filme"
        else:
            emoji = "📺"
            categoria = "Série"

        titulo_resultado = f"{emoji} {titulo}"

        if ano != "N/A":
            titulo_resultado += f" ({ano})"

        # ----------------------------------------------------
        # DESCRIÇÃO CURTA
        # ----------------------------------------------------

        descricao_resultado = descricao.replace("\n", " ").strip()

        if len(descricao_resultado) > 180:
            descricao_resultado = descricao_resultado[:177] + "..."

        descricao_resultado = (
            f"{categoria} • ⭐ {nota} • {descricao_resultado}"
        )

        # ----------------------------------------------------
        # RESULTADO INLINE
        # ----------------------------------------------------

        resultado = InlineQueryResultArticle(
            id=f"{tipo}_{tmdb_id}",
            title=titulo_resultado,
            description=descricao_resultado,
            thumbnail_url=poster,
            input_message_content=InputTextMessageContent(
                message_text=mensagem,
                parse_mode="HTML",
            ),
        )

        resultados.append(resultado)

    # --------------------------------------------------------
    # ENVIA RESULTADOS
    # --------------------------------------------------------

    await update.inline_query.answer(
        results=resultados,
        cache_time=10,
        is_personal=True,
    )


# ============================================================
# TRATAMENTO DE ERROS
# ============================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(
        "Erro durante execução do bot:",
        exc_info=context.error,
    )


# ============================================================
# INICIALIZAÇÃO
# ============================================================

def main():

    logger.info("Iniciando NEXFLIX_PEDIDOS_BOT...")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Comandos
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    # Inline Mode
    application.add_handler(
        InlineQueryHandler(inline_query)
    )

    # Erros
    application.add_error_handler(error_handler)

    logger.info("NEXFLIX_PEDIDOS_BOT iniciado!")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":
    main()
