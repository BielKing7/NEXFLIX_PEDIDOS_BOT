import telebot
import requests
from flask import Flask
from threading import Thread
import os

# =========================================================
# CONFIGURAÇÕES
# =========================================================

TOKEN = "8080775586:AAEAB_my0h0dLqbOfmHeF5aXe6S6YTSKRHU"

TMDB_KEY = "a169d710b2eca204f9db290256828d05"

bot = telebot.TeleBot(TOKEN)


# =========================================================
# SERVIDOR WEB PARA O RENDER
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "NEXFLIX PEDIDOS BOT ONLINE"


def run_server():
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )


# =========================================================
# /START
# SOMENTE CHAT PRIVADO
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    # Se for grupo ou supergrupo, não responde
    if message.chat.type != "private":
        return

    markup = telebot.types.InlineKeyboardMarkup()

    botao = telebot.types.InlineKeyboardButton(
        text="🔎 Procurar Filme ou Série",
        switch_inline_query_current_chat=""
    )

    markup.add(botao)

    texto = (
        "✨ **Bem-vindo(a) ao NEXFLIX - PEDIDOS!**\n\n"
        "🍿 Faça seu pedido de filme ou série "
        "para o aplicativo NEXFLIX.\n\n"
        "👇 Toque no botão abaixo para procurar."
    )

    bot.send_message(
        message.chat.id,
        texto,
        parse_mode="Markdown",
        reply_markup=markup
    )


# =========================================================
# PESQUISA INLINE
# =========================================================

@bot.inline_handler(lambda query: len(query.query) > 2)
def pesquisar(inline_query):

    try:

        nome = inline_query.query

        url = (
            "https://api.themoviedb.org/3/search/multi"
            f"?api_key={TMDB_KEY}"
            f"&query={requests.utils.quote(nome)}"
            "&language=pt-BR"
            "&include_adult=false"
        )

        resposta = requests.get(
            url,
            timeout=15
        )

        dados = resposta.json()

        resultados = dados.get("results", [])

        resultados = [
            item
            for item in resultados
            if item.get("media_type") in ["movie", "tv"]
        ]

        resultados = resultados[:15]

        respostas = []

        for indice, item in enumerate(resultados):

            titulo = (
                item.get("title")
                or item.get("name")
                or "Sem título"
            )

            data = (
                item.get("release_date")
                or item.get("first_air_date")
                or ""
            )

            ano = data[:4] if data else "----"

            if item.get("media_type") == "movie":
                tipo = "🎬 Filme"
            else:
                tipo = "📺 Série"

            poster = item.get("poster_path")

            thumbnail = None

            if poster:
                thumbnail = (
                    "https://image.tmdb.org/t/p/w92"
                    + poster
                )

            resultado = telebot.types.InlineQueryResultArticle(

                id=str(indice),

                title=f"{titulo} ({ano})",

                description=f"{tipo} • Toque para solicitar",

                thumbnail_url=thumbnail,

                input_message_content=
                telebot.types.InputTextMessageContent(

                    message_text=(
                        "🚀 **Solicitação recebida!**\n\n"
                        f"🍿 *{titulo} ({ano})*\n\n"
                        "Seu pedido foi registrado."
                    ),

                    parse_mode="Markdown"
                )
            )

            respostas.append(resultado)

        bot.answer_inline_query(
            inline_query.id,
            respostas,
            cache_time=1
        )

    except Exception as erro:

        print("Erro na pesquisa:", erro)


# =========================================================
# INICIAR
# =========================================================

if __name__ == "__main__":

    servidor = Thread(
        target=run_server,
        daemon=True
    )

    servidor.start()

    bot.remove_webhook()

    print("================================")
    print("NEXFLIX PEDIDOS BOT ONLINE")
    print("================================")
    print("Modo: CHAT PRIVADO")
    print("Grupos: DESATIVADOS")

    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30
    )
