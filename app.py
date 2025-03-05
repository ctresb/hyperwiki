import asyncio
import aiohttp
import requests
import re
import random
import threading
import urllib.parse
from flask import Flask, request, render_template_string, redirect, url_for, jsonify
import mwparserfromhell
from bs4 import BeautifulSoup

app = Flask(__name__)

MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <title>Hipertradução de Artigos</title>
  <style>
  .plainlinks.hlist.navbar.mini {
  display: none;}
    body { font-family: Arial, sans-serif; background-color: #f8f9fa; margin: 0; padding-top: 60px; }
    .navbar { position: fixed; top: 0; left: 0; width: 100%; 
              background-color: #f8f9fa; display: flex; align-items: center; 
              padding: 10px 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .navbar img { height: 40px; margin-right: 15px; }
    .navbar .author { font-size: 14px; color: gray; margin-right: auto; }
    .container { max-width: 800px; margin: auto; padding: 20px; background: white; 
                 border: 1px solid #ddd; text-align: center; }
    input[type="text"], input[type="number"] { width: 80%; padding: 10px; 
                                               font-size: 16px; margin-bottom: 10px; }
    button { padding: 10px; font-size: 16px; cursor: pointer; }
  </style>
</head>
<body>
  <div class="navbar">
    <img src="/static/logo.png" alt="Logo">
    <span class="author">Feito por: <a href="https://bsky.app/profile/ctresb.com">C3B </a>& <a href="https://www.nekoraita.art.br/">Nekoraita</a></span>
  </div>
  <div class="container">
    <h1>Insira um link da Wikipédia</h1>
    <form method="POST" action="/start">
      <input type="text" name="article_url" placeholder="Cole o link do artigo da Wikipédia" required>
      <br>
      <input type="number" name="lang_count" placeholder="Quantidade de línguas" 
             min="1" value="4" required>
      <br>
      <button type="submit">HIPERTRADUZIR</button>
    </form>
    <div>
    <h2> Feito por: </h2>
    <a href="https://bsky.app/profile/ctresb.com">
    <img src="https://cdn.bsky.app/img/avatar/plain/did:plc:ypynu36vspziz6xdrta3b42c/bafkreihvj6ojjqyqa3svvljudvllna6av5jepcveyjorisyfr6hyusjkr4@jpeg" alt="C3B" style="width: 50px; height: 50px; border-radius: 50%;">
    <p> C3B </p>
    </a>
    <a href="https://www.nekoraita.art.br/">
    <img src="https://cdn.bsky.app/img/avatar/plain/did:plc:lea2b2fmxkarz5nkrdfmqjd2/bafkreih4epacsxssdehgckifvmhpprbrogcjdc5gaqxzush32d2j4ua5mu@jpeg" alt="Nekoraita" style="width: 50px; height: 50px; border-radius: 50%;">
    <p> NEKORAITA </p>
    </a>
    </div>
  </div>
</body>
</html>
"""

PROGRESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <title>Progresso da Hipertradução</title>
  <style>
  .plainlinks.hlist.navbar.mini {
  display: none;}
    body { font-family: Arial, sans-serif; background-color: #f8f9fa; margin: 0; 
           padding-top: 60px; text-align: center; }
    .navbar { position: fixed; top: 0; left: 0; width: 100%; background-color: #f8f9fa;
              display: flex; align-items: center; padding: 10px 20px; 
              box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .navbar img { height: 40px; margin-right: 15px; }
    .navbar .author { font-size: 14px; color: gray; margin-right: auto; }
    .container { max-width: 800px; margin: auto; padding: 20px; background: white; 
                 border: 1px solid #ddd; }
  </style>
  <script>
    function pollProgress() {
      fetch('/progress')
        .then(response => response.json())
        .then(data => {
          document.getElementById("progress").innerText = 
              "Traduzindo: " + data.processed + " de " + data.total + " textos processados.";
          if (data.result) {
            window.location.href = "/result";
          } else {
            setTimeout(pollProgress, 1000);
          }
        });
    }
    window.onload = pollProgress;
  </script>
</head>
<body>
  <div class="navbar">
    <img src="/static/logo.png" alt="Logo">
    <span class="author">Feito por: <a href="https://bsky.app/profile/ctresb.com">C3B </a>& <a href="https://www.nekoraita.art.br/">Nekoraita</a></span>
  </div>
  <div class="container">
    <h1>HIPERTRADUZINDO...</h1>
    <p id="progress">Iniciando...</p>
  </div>
</body>
</html>
"""

RESULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt">
<head>
  <meta charset="UTF-8">
  <title>Artigo HIPERTRADUZIDO</title>
  <style>
  .plainlinks.hlist.navbar.mini {
  display: none;}
    body { font-family: Arial, sans-serif; background-color: #f8f9fa; margin: 0; 
           padding-top: 60px; }
           body a {
           margin: 0 5px;}
    .navbar { position: fixed; top: 0; left: 0; width: 100%; background-color: #f8f9fa;
              display: flex; align-items: center; padding: 10px 20px; 
              box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .navbar img { height: 40px; margin-right: 15px; }
    .navbar .author { font-size: 14px; color: gray; margin-right: auto; }
    .container { max-width: 800px; margin: auto; padding: 20px; background: white; 
                 border: 1px solid #ddd; }
    h1, h2 { border-bottom: 1px solid #aaa; }
  </style>
</head>
<body>
  <div class="navbar">
    <img src="/static/logo.png" alt="Logo">
    <span class="author">Feito por: <a href="https://bsky.app/profile/ctresb.com">C3B </a>& <a href="https://www.nekoraita.art.br/">Nekoraita</a></span>
  </div>
  <div class="container">
    <h2>Artigo HIPERTRADUZIDO</h2>
    <div>{{ html_content|safe }}</div>
  </div>
</body>
</html>
"""

supportedLangs = [
    "af", "sq", "am", "ar", "hy", "az", "eu", "bn", "bs", "bg", "ca", "ceb",
    "zh-CN", "zh-TW", "co", "hr", "cs", "da", "nl", "en", "eo", "et", "fi",
    "fr", "fy", "gl", "ka", "de", "el", "gu", "ht", "ha", "haw", "iw", "hi",
    "hmn", "hu", "is", "id", "ga", "ja", "jw", "kn", "kk", "km", "ko", "ku",
    "lo", "lv", "lt", "lb", "mk", "mg", "ms", "ml", "mt", "mi", "mr", "mn",
    "ne", "no", "ny", "ps", "fa", "pl", "pt", "pa", "ro", "ru", "sm", "gd",
    "sr", "st", "sn", "sd", "si", "sk", "sl", "so", "es", "sw", "sv", "tl",
    "tg", "ta", "te", "th", "tr", "uk", "ur", "uz", "vi", "cy", "xh", "yi",
    "yo", "zu"
]

translation_progress = {
    "total": 0, 
    "processed": 0,
    "result": None
}

def get_wikitext(article_url):
    """Obtém o wikitext de um artigo da Wikipédia a partir da URL."""
    match = re.search(r"/wiki/([^#?]+)", article_url)
    if not match:
        return None
    article_title = match.group(1)
    wikitext_url = (
        "https://pt.wikipedia.org/w/api.php"
        "?action=query&format=json&prop=revisions&rvprop=content"
        f"&titles={article_title}&rvslots=main"
    )
    headers = {"User-Agent": "MeuScriptWikiConversor/1.0"}
    resp = requests.get(wikitext_url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_info in pages.items():
            if page_id != "-1":
                return page_info["revisions"][0]["slots"]["main"]["*"]
    return None

def convert_wikitext_to_html(wikitext):
    """Converte wikitext para HTML usando a API da Wikipédia."""
    url = "https://pt.wikipedia.org/api/rest_v1/transform/wikitext/to/html"
    headers = {
        "User-Agent": "MeuScriptWikiConversor/1.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(url, data={"wikitext": wikitext}, headers=headers)
    if response.status_code == 200:
        return response.text
    return None

import aiohttp
import asyncio

async def async_translate(text, src, tgt, session):
    """
    Traduz 'text' de src para tgt, usando a API do Google Translate de forma assíncrona.
    """
    encoded_text = urllib.parse.quote(text)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src}&tl={tgt}&dt=t&q={encoded_text}"
    async with session.get(url) as response:
        data = await response.json()
        if isinstance(data, list) and isinstance(data[0], list):
            return ''.join(seg[0] for seg in data[0] if seg[0] is not None)
        else:
            raise Exception("Resposta inválida da API.")

async def async_hypertranslate_fixed(text, count=4):
    """
    Monta uma cadeia aleatória de idiomas (além de 'pt'), com no mínimo 8 passos,
    e traduz o texto de forma encadeada, gerando um efeito 'doidão'.
    """
    chain_length = max(count + 2, 8)
    non_pt = [lang for lang in supportedLangs if lang != "pt"]
    random_chain = random.sample(non_pt, chain_length - 2)
    chain = ["pt"] + random_chain + ["pt"]
    print("Cadeia usada:", chain)

    current_text = text
    async with aiohttp.ClientSession() as session:
        for i in range(len(chain) - 1):
            current_text = await async_translate(current_text, chain[i], chain[i+1], session)
    return current_text

async def process_node_async(node, count):
    """
    Traduz o texto de 'node' usando a função hypertranslate assíncrona.
    """
    original = node.string
    try:
        translated_text = await async_hypertranslate_fixed(original, count)
        print("Original:", original)
        print("Hipertraduzido:", translated_text)
        return translated_text
    except Exception as e:
        print("Erro na tradução:", e)
        return original

async def hypertranslate_html_async(html, count=4):
    """
    Percorre todos os nós de texto no HTML, traduzindo cada um em paralelo via asyncio.
    """
    soup = BeautifulSoup(html, 'html.parser')
    text_nodes = [el for el in soup.find_all(string=True) 
                  if el.parent.name not in ['script','style'] and el.strip()]
    translation_progress["total"] = len(text_nodes)
    translation_progress["processed"] = 0

    tasks = [asyncio.create_task(process_node_async(node, count)) for node in text_nodes]
    results = await asyncio.gather(*tasks)

    for node, res in zip(text_nodes, results):
        node.replace_with(res)
        translation_progress["processed"] += 1

    return str(soup)

def process_translation(article_url, lang_count):
    global translation_progress
    translation_progress["result"] = None

    wikitext = get_wikitext(article_url)
    if not wikitext:
        translation_progress["result"] = "<p>Erro ao obter o artigo.</p>"
        return

    original_html = convert_wikitext_to_html(wikitext)
    if not original_html:
        translation_progress["result"] = "<p>Erro ao converter para HTML.</p>"
        return

    hyper_html = asyncio.run(hypertranslate_html_async(original_html, count=lang_count))
    translation_progress["result"] = hyper_html

@app.route("/", methods=["GET"])
def main():
    return render_template_string(MAIN_TEMPLATE)

@app.route("/start", methods=["POST"])
def start():
    article_url = request.form.get("article_url")
    try:
        lang_count = int(request.form.get("lang_count", 4))
    except ValueError:
        lang_count = 4

    translation_progress["total"] = 0
    translation_progress["processed"] = 0
    translation_progress["result"] = None

    thread = threading.Thread(target=process_translation, args=(article_url, lang_count))
    thread.start()
    return redirect(url_for("progress_page"))

@app.route("/progress-page", methods=["GET"])
def progress_page():
    return render_template_string(PROGRESS_TEMPLATE)

@app.route("/progress", methods=["GET"])
def progress():
    return jsonify(translation_progress)

@app.route("/result", methods=["GET"])
def result():
    if translation_progress["result"]:
        return render_template_string(RESULT_TEMPLATE, 
                                      html_content=translation_progress["result"])
    else:
        return redirect(url_for("progress_page"))

if __name__ == "__main__":
    import threading
    import webbrowser

    def open_browser():
        webbrowser.open("http://127.0.0.1:5000/")

    threading.Timer(1, open_browser).start()
    app.run(debug=True)