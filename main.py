import os
import telebot
import requests
import time
from flask import Flask
from threading import Thread, Timer
from telebot import types

app = Flask('')
@app.route('/')
def home(): return "Buscador Cloud Filmes Ativo!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

TOKEN = '8080775586:AAEn6uXjgjS2qgNbhke2Jg8bTTbopOzHldU'
TMDB_KEY = 'a169d710b2eca204f9db290256828d05'
BASE_EMBED = "https://embedplayapi.site/embed/"
IMG_URL = "https://image.tmdb.org/t/p/w1280"

bot = telebot.TeleBot(TOKEN)

# --- FUNÇÃO PARA APAGAR MENSAGEM APÓS 1 HORA ---
def delete_later(chat_id, message_id):
    def delete():
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
    Timer(3600, delete).start()

def get_class_icon(age):
    icons = {
        "L": "🟩 [L] LIVRE",
        "10": "🟦 [10] ANOS",
        "12": "🟨 [12] ANOS",
        "14": "🟧 [14] ANOS",
        "16": "🟥 [16] ANOS",
        "18": "⬛ [18] ANOS"
    }
    return icons.get(age, "⬜ [N/A]")

def get_details(tmdb_id, tipo):
    url = f"https://api.themoviedb.org/3/{tipo}/{tmdb_id}?api_key={TMDB_KEY}&language=pt-BR&append_to_response=credits,release_dates,content_ratings"
    try:
        data = requests.get(url).json()
        cast = ", ".join([actor['name'] for actor in data.get('credits', {}).get('cast', [])[:3]])
        genres = ", ".join([g['name'] for g in data.get('genres', [])])
        runtime = data.get('runtime') or data.get('episode_run_time', [0])[0]
        duration = f"{runtime} min" if runtime else "N/A"
        
        age = "N/A"
        if tipo == 'movie':
            for r in data.get('release_dates', {}).get('results', []):
                if r['iso_3166_1'] == 'BR':
                    age = r['release_dates'][0].get('certification', 'L')
        else:
            for r in data.get('content_ratings', {}).get('results', []):
                if r['iso_3166_1'] == 'BR':
                    age = r.get('rating', 'L')
        
        return cast, genres, duration, get_class_icon(age)
    except:
        return "N/A", "N/A", "N/A", "⬜ [N/A]"

@bot.inline_handler(lambda query: len(query.query) > 2)
def query_text(inline_query):
    try:
        url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_KEY}&query={inline_query.query}&language=pt-BR"
        res = requests.get(url).json()
        resultados = res.get('results', [])[:10]
        
        results_list = []
        for i, item in enumerate(resultados):
            if item.get('media_type') not in ['movie', 'tv']: continue
            
            tmdb_id = item.get('id')
            tipo = item.get('media_type')
            titulo = item.get('title') or item.get('name')
            
            # Define o rótulo do lado direito
            label = "FILME" if tipo == 'movie' else "SÉRIE"
            titulo_com_label = f"{titulo} | {label}"
            
            thumb = f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get('poster_path') else "https://via.placeholder.com/500"
            
            results_list.append(types.InlineQueryResultArticle(
                id=str(i),
                title=titulo_com_label, # Título com o nome do lado direito
                description="Clique para ver os detalhes",
                thumbnail_url=thumb,
                input_message_content=types.InputTextMessageContent(f"/detalhes_{tipo}_{tmdb_id}")
            ))
        bot.answer_inline_query(inline_query.id, results_list, cache_time=1)
    except: pass

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/detalhes_'))
def processar_escolha(message):
    try:
        _, tipo, tmdb_id = message.text.split('_')
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass

        url = f"https://api.themoviedb.org/3/{tipo}/{tmdb_id}?api_key={TMDB_KEY}&language=pt-BR"
        item = requests.get(url).json()
        
        cast, genres, duration, class_icon = get_details(tmdb_id, tipo)
        titulo = item.get('title') or item.get('name')
        ano = (item.get('release_date') or item.get('first_air_date') or "----")[:4]
        sinopse = item.get('overview') or "Sem sinopse."
        backdrop = f"{IMG_URL}{item.get('backdrop_path')}" if item.get('backdrop_path') else None

        msg_body = (
            f"🎬 {titulo.upper()}\n\n"
            f"📅 Ano: {ano}\n"
            f"⏳ Duração: {duration}\n"
            f"🎭 Gênero: {genres}\n"
            f"👥 Elenco: {cast}\n"
            f"{class_icon}\n\n"
            f"📖 Sinopse: {sinopse}\n\n"
        )

        if tipo == 'movie':
            link = f"{BASE_EMBED}{tmdb_id}"
            footer = f"🔗 LINK EMBED:\n`{link}`"
            if backdrop: sent = bot.send_photo(message.chat.id, backdrop, caption=msg_body + footer, parse_mode="Markdown")
            else: sent = bot.send_message(message.chat.id, msg_body + footer, parse_mode="Markdown")
            delete_later(message.chat.id, sent.message_id)
        else:
            if backdrop: sent = bot.send_photo(message.chat.id, backdrop, caption=msg_body, parse_mode="Markdown")
            else: sent = bot.send_message(message.chat.id, msg_body, parse_mode="Markdown")
            delete_later(message.chat.id, sent.message_id)
            
            wait = bot.send_message(message.chat.id, "Organizando episódios...")
            delete_later(message.chat.id, wait.message_id)
            
            url_tv = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_KEY}&language=pt-BR"
            detalhes = requests.get(url_tv).json()
            for s in detalhes.get('seasons', []):
                s_num = s.get('season_number')
                if s_num == 0: continue
                url_eps = f"https://api.themoviedb.org/3/tv/{tmdb_id}/season/{s_num}?api_key={TMDB_KEY}&language=pt-BR"
                dados_temp = requests.get(url_eps).json()
                
                t_msg = bot.send_message(message.chat.id, f"📂 TEMPORADA {s_num}")
                delete_later(message.chat.id, t_msg.message_id)

                for ep in dados_temp.get('episodes', []):
                    e_num = ep.get('episode_number')
                    texto_ep = (
                        f"🔹 EPISÓDIO {e_num}: {(ep.get('name') or '').upper()}\n\n"
                        f"📝 Sinopse: {ep.get('overview') or 'Sem sinopse.'}\n\n"
                        f"🔗 LINK EMBED:\n`{BASE_EMBED}{tmdb_id}/{s_num}/{e_num}`\n"
                        f"────────────────────"
                    )
                    ep_m = bot.send_message(message.chat.id, texto_ep, parse_mode="Markdown")
                    delete_later(message.chat.id, ep_m.message_id)
                    time.sleep(0.4)
    except: pass

@bot.message_handler(commands=['start'])
def welcome(message):
    msg = bot.send_message(message.chat.id, "Buscador Profissional Ativo\n\nDigite o nome de um filme ou série para começar.")
    delete_later(message.chat.id, msg.message_id)

if __name__ == "__main__":
    t = Thread(target=run)
    t.start()
    bot.infinity_polling(skip_pending=True)
    
