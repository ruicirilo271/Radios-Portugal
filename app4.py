from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Capacidade do histórico
MAX_HISTORY = 4

# Buscar artista e título da música via API externa
def get_radio_info(radio_url):
    api_url = f"https://radio-metadata-api-main.vercel.app/radio_info/?radio_url={radio_url}"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            artist = data.get('artist') or data.get('songtitle') or 'Desconhecido'
            song = data.get('song') or data.get('title') or 'Desconhecido'
            # Processando corretamente o histórico de músicas
            song_history = [
                f"{entry['song']['artist']} - {entry['song']['title']}" 
                for entry in data.get('song_history', []) 
                if entry.get('song') and entry['song'].get('artist') and entry['song'].get('title')
            ]
            return artist.strip(), song.strip(), song_history
    except requests.RequestException as e:
        print(f"[ERRO] Erro de requisição: {e}")
    return 'Desconhecido', 'Desconhecido', []

# Buscar capa do álbum no iTunes
def get_album_cover(artist, title):
    if artist == 'Desconhecido' or title == 'Desconhecido':
        return None
    search_term = f"{artist} {title}".replace(' ', '+')
    api_url = f"https://itunes.apple.com/search?term={search_term}&entity=song&limit=1"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['resultCount'] > 0:
                return data['results'][0].get('artworkUrl100', '').replace('100x100', '300x300')
    except requests.RequestException as e:
        print(f"[ERRO] Erro ao buscar capa no iTunes: {e}")
    return None

# Buscar letra da música
def get_lyrics(artist, title):
    try:
        lyrics_api_url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
        response = requests.get(lyrics_api_url)
        if response.status_code == 200:
            data = response.json()
            return data.get('lyrics', 'Letra não encontrada')
    except requests.RequestException as e:
        print(f"[ERRO] Erro ao buscar letra da música: {e}")
    return 'Letra não encontrada'

@app.route('/', methods=['GET', 'POST'])
def index():
    url = 'https://de1.api.radio-browser.info/json/stations/bycountry/Portugal'
    try:
        response = requests.get(url, timeout=10)
        radios = response.json() if response.status_code == 200 else []
    except requests.RequestException:
        radios = []

    radios_mp3 = [
        radio for radio in radios if 'url_resolved' in radio and (
            radio['url_resolved'].endswith('.mp3') or
            'audio/mpeg' in radio.get('codec', '').lower() or
            'mp3' in radio.get('codec', '').lower()
        )
    ]

    selected_url = None
    selected_radio = None
    artist = title = album_cover = None
    song_history = []
    lyrics = None

    if request.method == 'POST':
        selected_url = request.form.get('station')
        selected_radio = next((r for r in radios_mp3 if r['url_resolved'] == selected_url), None)
        if selected_radio:
            artist, title, song_history = get_radio_info(selected_radio['url_resolved'])
            album_cover = get_album_cover(artist, title)
            lyrics = get_lyrics(artist, title)

            # Limitando o histórico para 4 músicas
            song_history = song_history[:MAX_HISTORY]

    return render_template('index.html', radios=radios_mp3, selected_url=selected_url,
                           selected_radio=selected_radio, artist=artist,
                           song=title, album_cover=album_cover, song_history=song_history,
                           lyrics=lyrics)

@app.route('/get_radio_info', methods=['GET'])
def get_radio_info_ajax():
    radio_url = request.args.get('radio_url')
    if radio_url:
        artist, title, song_history = get_radio_info(radio_url)
        album_cover = get_album_cover(artist, title)
        lyrics = get_lyrics(artist, title)

        # Limitando o histórico para 4 músicas
        song_history = song_history[:MAX_HISTORY]

        return jsonify({
            'artist': artist,
            'song': title,
            'album_cover': album_cover or "https://placehold.co/300x300/cccccc/000000?text=Sem+Capa",
            'lyrics': lyrics,
            'song_history': song_history
        })
    return jsonify({
        'artist': 'Desconhecido',
        'song': 'Desconhecido',
        'album_cover': "https://placehold.co/300x300/cccccc/000000?text=Sem+Capa",
        'lyrics': 'Letra não encontrada',
        'song_history': []
    })

if __name__ == '__main__':
    app.run(debug=True)




















