import os
import html
import logging
import threading

import requests
import telebot

from flask import Flask

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("A variável BOT_TOKEN não foi configurada.")

if not TMDB_TOKEN:
    raise RuntimeError("A variável TMDB_TOKEN não foi configurada.")


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# ============================================================
# TELEGRAM
# ============================================================

bot = telebot.TeleBot(
    BOT_TOKEN,
    parse_mode="HTML"
)


# ============================================================
# FLASK
# ============================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "NEXFLIX PEDIDOS BOT ONLINE"


@app.route("/health")
def health():
    return "OK"


# ============================================================
# TMDB
# ============================================================

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

TMDB_HEADERS = {
    "Authorization": f"Bearer {TMDB_TOKEN}",
    "accept": "application/json"
}


# ============================================================
# COMANDO /START
# ============================================================

@bot.message_handler(commands=["start"])
def start(message):

    texto = (
        "🎬 <b>NEXFLIX</b>\n\n"
        "🔎 Este bot permite pesquisar filmes e séries "
        "diretamente pelo Telegram.\n\n"
        "🎬 <b>Filmes</b>\n"
        "<code>@NEXFLIX_PEDIDOS_BOT filme Batman</code>\n\n"
        "📺 <b>Séries</b>\n"
        "<code>@NEXFLIX_PEDIDOS_BOT serie Stranger Things</code>"
    )

    bot.send_message(
        message.chat.id,
        texto
    )


# ============================================================
# COMANDO /HELP
# ============================================================

@bot.message_handler(commands=["help"])
def help_command(message):

    texto = (
        "📚 <b>Como pesquisar</b>\n\n"
        "🎬 Filmes:\n"
        "<code>@NEXFLIX_PEDIDOS_BOT filme Batman</code>\n\n"
        "📺 Séries:\n"
        "<code>@NEXFLIX_PEDIDOS_BOT serie Stranger Things</code>"
    )

    bot.send_message(
        message.chat.id,
        texto
    )


# ============================================================
# PESQUISAR TMDB
# ============================================================

def pesquisar_tmdb(tipo, consulta):

    if tipo not in ["movie", "tv"]:
        return []

    url = f"{TMDB_BASE_URL}/search/{tipo}"

    parametros = {
        "query": consulta,
        "language": "pt-BR",
        "include_adult": "false",
        "page": 1
    }

    try:

        resposta = requests.get(
            url,
            headers=TMDB_HEADERS,
            params=parametros,
            timeout=15
        )

        resposta.raise_for_status()

        dados = resposta.json()

        return dados.get("results", [])

    except requests.RequestException as erro:

        logger.error(
            f"Erro ao consultar TMDB: {erro}"
        )

        return []

    except Exception as erro:

        logger.error(
            f"Erro inesperado: {erro}"
        )

        return []


# ============================================================
# INFORMAÇÕES
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


def obter_nota(item):

    nota = item.get("vote_average")

    if nota is None:
        return "N/A"

    try:
        return f"{float(nota):.1f}"
    except:
        return "N/A"


def obter_descricao(item):

    descricao = item.get("overview")

    if not descricao:
        return "Descrição não disponível."

    return descricao


def obter_poster(item):

    poster = item.get("poster_path")

    if not poster:
        return None

    return TMDB_IMAGE_URL + poster


# ============================================================
# TEXTO DO RESULTADO
# ============================================================

def criar_mensagem(item, tipo):

    titulo = html.escape(
        obter_titulo(item, tipo)
    )

    ano = html.escape(
        obter_ano(item, tipo)
    )

    descricao = html.escape(
        obter_descricao(item)
    )

    nota = obter_nota(item)

    if tipo == "movie":
        categoria = "🎬 FILME"
    else:
        categoria = "📺 SÉRIE"

    texto = (
        f"<b>{categoria}</b>\n\n"
        f"🎞️ <b>{titulo}</b>\n"
        f"📅 Ano: <b>{ano}</b>\n"
        f"⭐ Nota TMDB: <b>{nota}</b>\n\n"
        f"📝 <b>Descrição:</b>\n"
        f"{descricao}"
    )

    return texto


# ============================================================
# INLINE MODE
# ============================================================

@bot.inline_handler(
    lambda query: True
)
def inline_query(query):

    texto_pesquisa = query.query.strip()

    # --------------------------------------------------------
    # PESQUISA VAZIA
    # --------------------------------------------------------

    if not texto_pesquisa:

        resultado = telebot.types.InlineQueryResultArticle(
            id="ajuda",

            title="🔎 Pesquisar no NEXFLIX",

            description=(
                "Use: filme nome ou serie nome"
            ),

            input_message_content=(
                telebot.types.InputTextMessageContent(
                    message_text=(
                        "🎬 <b>NEXFLIX</b>\n\n"
                        "Use uma das opções abaixo:\n\n"
                        "🎬 <code>filme Batman</code>\n"
                        "📺 <code>serie Stranger Things</code>"
                    ),
                    parse_mode="HTML"
                )
            )
        )

        bot.answer_inline_query(
            query.id,
            [resultado],
            cache_time=1,
            is_personal=True
        )

        return

    # --------------------------------------------------------
    # IDENTIFICAR TIPO
    # --------------------------------------------------------

    pesquisa_lower = texto_pesquisa.lower()

    tipo = None
    pesquisa = ""

    comandos_filme = [
        "filme ",
        "filmes ",
        "movie "
    ]

    comandos_serie = [
        "serie ",
        "série ",
        "series ",
        "séries ",
        "tv "
    ]

    for comando in comandos_filme:

        if pesquisa_lower.startswith(comando):

            tipo = "movie"

            pesquisa = texto_pesquisa[
                len(comando):
            ].strip()

            break

    if tipo is None:

        for comando in comandos_serie:

            if pesquisa_lower.startswith(comando):

                tipo = "tv"

                pesquisa = texto_pesquisa[
                    len(comando):
                ].strip()

                break

    # --------------------------------------------------------
    # SEM TIPO
    # --------------------------------------------------------

    if tipo is None:

        resultado = telebot.types.InlineQueryResultArticle(
            id="modo_pesquisa",

            title="🎬 Escolha filmes ou séries",

            description=(
                "Digite filme ou serie antes da pesquisa"
            ),

            input_message_content=(
                telebot.types.InputTextMessageContent(
                    message_text=(
                        "🔎 <b>NEXFLIX</b>\n\n"
                        "🎬 Para filmes:\n"
                        "<code>filme Batman</code>\n\n"
                        "📺 Para séries:\n"
                        "<code>serie Stranger Things</code>"
                    ),
                    parse_mode="HTML"
                )
            )
        )

        bot.answer_inline_query(
            query.id,
            [resultado],
            cache_time=1,
            is_personal=True
        )

        return

    # --------------------------------------------------------
    # PESQUISA VAZIA
    # --------------------------------------------------------

    if not pesquisa:

        bot.answer_inline_query(
            query.id,
            [],
            cache_time=1,
            is_personal=True
        )

        return

    # --------------------------------------------------------
    # CONSULTAR TMDB
    # --------------------------------------------------------

    resultados_tmdb = pesquisar_tmdb(
        tipo,
        pesquisa
    )

    resultados_tmdb = resultados_tmdb[:10]

    resultados = []

    # --------------------------------------------------------
    # CRIAR RESULTADOS
    # --------------------------------------------------------

    for item in resultados_tmdb:

        tmdb_id = item.get("id")

        if not tmdb_id:
            continue

        titulo = obter_titulo(
            item,
            tipo
        )

        ano = obter_ano(
            item,
            tipo
        )

        nota = obter_nota(
            item
        )

        descricao = obter_descricao(
            item
        )

        poster = obter_poster(
            item
        )

        mensagem = criar_mensagem(
            item,
            tipo
        )

        if tipo == "movie":

            emoji = "🎬"
            categoria = "Filme"

        else:

            emoji = "📺"
            categoria = "Série"

        titulo_resultado = (
            f"{emoji} {titulo}"
        )

        if ano != "N/A":

            titulo_resultado += (
                f" ({ano})"
            )

        descricao_curta = (
            descricao
            .replace("\n", " ")
            .strip()
        )

        if len(descricao_curta) > 160:

            descricao_curta = (
                descricao_curta[:157]
                + "..."
            )

        descricao_resultado = (
            f"{categoria} • "
            f"⭐ {nota} • "
            f"{descricao_curta}"
        )

        # ----------------------------------------------------
        # COM IMAGEM
        # ----------------------------------------------------

        if poster:

            resultado = (
                telebot.types.InlineQueryResultPhoto(

                    id=f"{tipo}_{tmdb_id}",

                    photo_url=poster,

                    thumbnail_url=poster,

                    title=titulo_resultado,

                    description=descricao_resultado,

                    caption=mensagem,

                    parse_mode="HTML"
                )
            )

        # ----------------------------------------------------
        # SEM IMAGEM
        # ----------------------------------------------------

        else:

            resultado = (
                telebot.types.InlineQueryResultArticle(

                    id=f"{tipo}_{tmdb_id}",

                    title=titulo_resultado,

                    description=descricao_resultado,

                    input_message_content=(
                        telebot.types.InputTextMessageContent(
                            message_text=mensagem,
                            parse_mode="HTML"
                        )
                    )
                )
            )

        resultados.append(
            resultado
        )

    # --------------------------------------------------------
    # RESPONDER
    # --------------------------------------------------------

    bot.answer_inline_query(
        query.id,
        resultados,
        cache_time=10,
        is_personal=True
    )


# ============================================================
# THREAD DO BOT
# ============================================================

def iniciar_bot():

    logger.info(
        "Iniciando polling do Telegram..."
    )

    while True:

        try:

            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True
            )

        except Exception as erro:

            logger.error(
                f"Polling interrompido: {erro}"
            )


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":

    # Inicia o Telegram em segundo plano
    thread_bot = threading.Thread(
        target=iniciar_bot,
        daemon=True
    )

    thread_bot.start()

    # Porta fornecida pelo Render
    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    logger.info(
        f"Servidor iniciado na porta {port}"
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
