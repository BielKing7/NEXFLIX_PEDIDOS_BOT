import os
import telebot
import requests
import time
from telebot import types
from flask import Flask
from threading import Thread

# --- SERVIDOR WEB ---
app = Flask('')

@app.route('/')
def home(): 
    return "Servidor Cloud Filmes Online"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURAÇÃO ---
TOKEN = '8080775586:AAEJWOiP3ecgGvrw4ITYJsl_hd57ZCQ4o1E'
TMDB_KEY = 'a169d710b2eca204f9db290256828d05'
MEU_ID = '4417386384'
ID_TOPICO_PEDIDOS = 7 

bot = telebot.TeleBot(TOKEN)

# --- COMANDO START (CORRIGIDO PARA PRIVADO E GRUPO) ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    botao_busca = types.InlineKeyboardButton(
        text="Procurar Filme ou Serie", 
        switch_inline_query_current_chat=""
    )
    markup.add(botao_busca)

    texto_start = (
        "✨ **Bem-vindo(a) ao CLOUD FILMES - PEDIDOS!**\n\n"
        "Para fazer um pedido, clique no botão abaixo e digite o nome do conteúdo.\n\n"
        "⚠️ **Atenção:** No grupo, use este botão apenas no tópico de Pedidos!"
    )
    
    try:
        # Se a mensagem vier de um grupo (supergroup), enviamos com o ID do tópico
        if message.chat.type in ['group', 'supergroup']:
            bot.send_message(
                message.chat.id, 
                texto_start, 
                parse_mode="Markdown", 
                reply_markup=markup,
                message_thread_id=message.message_thread_id
            )
        else:
            # Se for no privado, envia normal (como no seu primeiro código)
            bot.send_message(message.chat.id, texto_start, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        print(f"Erro no Start: {e}")

# --- MODO INLINE ---
@bot.inline_handler(lambda query: len(query.query) > 2)
def query_text(inline_query):
    try:
        nome_busca = inline_query.query
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={nome_busca}&language=pt-BR"
        res = requests.get(url).json()
        resultados = res.get('results', [])[:15]

        res_inline = []
        for i, item in enumerate(resultados):
            titulo = item.get('title') or item.get('name')
            data = item.get('release_date') or item.get('first_air_date') or "----"
            ano = data[:4]
            tipo = "🎬 Filme" if item.get('media_type') == 'movie' else "📺 Série"
            thumb = f"https://image.tmdb.org/t/p/w92{item.get('poster_path')}" if item.get('poster_path') else None
            
            r = types.InlineQueryResultArticle(
                id=str(i),
                title=f"{titulo} ({ano})",
                description=f"{tipo} - Toque para solicitar",
                thumbnail_url=thumb,
                input_message_content=types.InputTextMessageContent(
                    message_text=f"🚀 **Solicitação recebida! Seu pedido vai ser adicionado em breve no aplicativo CLOUD FILMES.**\n\n_{titulo} ({ano})_",
                    parse_mode="Markdown"
                )
            )
            res_inline.append(r)
        bot.answer_inline_query(inline_query.id, res_inline, cache_time=1)
    except Exception as e:
        print(f"Erro Inline: {e}")

# --- PROCESSAMENTO DO PEDIDO (COM TRAVA DE TÓPICO) ---
@bot.message_handler(func=lambda m: m.text and "Solicitação recebida!" in m.text)
def processar_pedido_profissional(message):
    try:
        # Só processa se for no tópico 5 (se estiver em um grupo)
        if message.chat.type in ['group', 'supergroup'] and message.message_thread_id != ID_TOPICO_PEDIDOS:
            return

        partes = message.text.split('\n\n')
        if len(partes) < 2: return
        
        conteudo = partes[-1].strip('_')
        nome_limpo = conteudo.split(' (')[0]
        
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={nome_limpo}&language=pt-BR"
        res_tmdb = requests.get(url).json().get('results', [])
        
        if res_tmdb:
            detalhes = res_tmdb[0]
            titulo = detalhes.get('title') or detalhes.get('name')
            data = detalhes.get('release_date') or detalhes.get('first_air_date') or "----"
            ano = data[:4]
            tipo = "🎬 Filme" if detalhes.get('media_type') == 'movie' else "📺 Série"
            sinopse = detalhes.get('overview', 'Sinopse não disponível.')
            img_path = detalhes.get('backdrop_path') or detalhes.get('poster_path')
            img_url = f"https://image.tmdb.org/t/p/w780{img_path}" if img_path else None
            user = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name
            
            texto_admin = (
                f"🍿 **SISTEMA DE SOLICITAÇÃO - CLOUD FILMES**\n\n"
                f"📂 **Tipo:** {tipo}\n\n"
                f"📌 **Título:** {titulo}\n\n"
                f"📅 **Ano:** {ano}\n\n"
                f"👤 **Solicitante:** {user}"
            )

            if img_url:
                bot.send_photo(MEU_ID, img_url, caption=texto_admin, parse_mode="Markdown")
            else:
                bot.send_message(MEU_ID, texto_admin, parse_mode="Markdown")

        # Faxina automática
        time.sleep(20)
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except: pass
    except Exception as e:
        print(f"Erro ao processar: {e}")

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    bot.remove_webhook()
    print("Bot online!")
    bot.infinity_polling()
