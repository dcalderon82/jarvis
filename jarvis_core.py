"""Cerebro de Jarvis: todo lo que no depende de la ventana, del micrófono ni de Windows.

Lo usan la app de escritorio (jarvis_gui.py) y, más adelante, la versión web.
Las partes que dependen de cada app se enchufan desde afuera con estos ganchos:

  URL_OPENER       abre un link (escritorio: el navegador). Si es None, la respuesta incluye el link.
  NOTIFIER         avisa un recordatorio que venció (escritorio: chat + voz).
  DESKTOP_HANDLER  comandos que solo existen en la PC y van primero (abrir apps, volumen, música, bloqueo...).
  DESKTOP_LATE_HANDLER  los de la PC que van después de Wikipedia (captura de pantalla, info del sistema).
  LLM_CHAT         función que recibe la conversación y devuelve la respuesta del modelo.
"""
import threading
import datetime
import requests
import xml.etree.ElementTree as ET
import pyjokes
import os
import json
import re
from urllib.parse import quote_plus

# -----------------------------
# PERFIL (se lee de perfil.json; copiá perfil.ejemplo.json y completalo)
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Dónde se guardan los datos que cambian (notas, memoria, recordatorios) y, si existe, el perfil.
# En tu PC es la carpeta del programa; en un servidor se apunta a un disco persistente (JARVIS_DATA_DIR).
DATA_DIR = os.environ.get("JARVIS_DATA_DIR") or BASE_DIR
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except OSError:
    pass

def load_profile():
    """Fuentes, en orden: la variable JARVIS_PROFILE (un JSON; es lo que se usa en un hosting, donde
    perfil.json no existe), perfil.json en DATA_DIR o junto al programa, y por último la plantilla."""
    raw = os.environ.get("JARVIS_PROFILE")
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except ValueError:
            pass
        print("Aviso: JARVIS_PROFILE no es un JSON válido (un objeto con comillas dobles); se ignora.")
    for folder in dict.fromkeys((DATA_DIR, BASE_DIR)):
        for filename in ("perfil.json", "perfil.ejemplo.json"):
            try:
                with open(os.path.join(folder, filename), encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError):
                continue
    return {}

PROFILE = load_profile()
DEVELOPER_NAME = PROFILE.get("nombre", "Diego")
NICKNAME = PROFILE.get("apodo", DEVELOPER_NAME)
DEFAULT_CITY = PROFILE.get("ciudad", "General Deheza")
INTERESTS = PROFILE.get("gustos", [])
ABOUT_ME = PROFILE.get("sobre_mi", "")

# -----------------------------
# SETTINGS
# -----------------------------
MODEL = PROFILE.get("modelo", "llama3.2")  # modelo de Ollama (se cambia en perfil.json)

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# -----------------------------
# GANCHOS (los configura cada app)
# -----------------------------
URL_OPENER = None
NOTIFIER = None
DESKTOP_HANDLER = None
DESKTOP_LATE_HANDLER = None

def open_url(url, message):
    """Abre el link si la app sabe hacerlo (escritorio); si no, lo incluye en la respuesta (web/celu)."""
    if URL_OPENER is not None:
        URL_OPENER(url)
        return message
    return f"{message} {url}"

def default_llm_chat(messages):
    import ollama  # se importa acá para que la versión web no lo necesite
    return ollama.chat(model=MODEL, messages=messages)["message"]["content"]

LLM_CHAT = default_llm_chat
LLM_ERROR_MESSAGE = "Perdón, no puedo conectarme a Ollama. Asegurate de que esté corriendo."

# -----------------------------
# MEMORIA A LARGO PLAZO (memoria.json, no se sube a git)
#   - hechos: cosas que le pedís que recuerde ("acordate que me gusta el mate")
#   - historial: los últimos mensajes de la charla, para retomar al volver a abrir
# -----------------------------
MEMORY_FILE = os.path.join(DATA_DIR, "memoria.json")
MEMORY_LOCK = threading.Lock()
MAX_FACTS = 30
MAX_HISTORY_MESSAGES = 20

def load_memory():
    """Devuelve (hechos, historial) guardados; si no hay archivo o está roto, vacíos."""
    try:
        with open(MEMORY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("formato inesperado")
    except FileNotFoundError:
        return [], []
    except (OSError, ValueError):
        # El archivo existe pero está roto: lo aparto para no pisarlo.
        try:
            os.replace(MEMORY_FILE, MEMORY_FILE + ".corrupto")
        except OSError:
            pass
        return [], []

    saved_facts = data.get("hechos")
    saved_history = data.get("historial")
    facts = [h for h in saved_facts if isinstance(h, str)] if isinstance(saved_facts, list) else []
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in (saved_history if isinstance(saved_history, list) else [])
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
    ]
    return facts[:MAX_FACTS], history[-MAX_HISTORY_MESSAGES:]

FACTS, SAVED_HISTORY = load_memory()

def build_system_prompt():
    prompt = (
        f"Sos Jarvis, el asistente personal de {NICKNAME} (se llama {DEVELOPER_NAME}), "
        f"que además es tu creador y quien te mantiene. "
        f"Hablás en español rioplatense, con voseo (vos tenés, vos podés, mirá, fijate). "
        f"Sos totalmente informal, como un amigo argentino: relajado, con humor, un poco irónico y cero robótico. "
        f"Podés usar expresiones y malas palabras suaves de la calle como 'boludo', 'che', 'dale', 'bárbaro', "
        f"'al pedo' o 'una masa' cuando quede natural, sin pasarte ni insultar de verdad ni ofender a nadie. "
        f"Nada de frases de robot como 'como asistente de IA' ni 'estoy aquí para ayudarte'. "
        f"Respondé corto, en una o dos frases la mayoría de las veces, porque tus respuestas se leen en voz alta. "
        f"No uses emojis, listas ni formato especial. Ayudá de verdad y no inventes datos: si no sabés algo, decilo."
    )
    if ABOUT_ME:
        prompt += f" Sobre {NICKNAME}: {ABOUT_ME}"
    if INTERESTS:
        prompt += f" Le gustan: {', '.join(INTERESTS)}."
    if FACTS:
        dichos = " ".join(f'{NICKNAME} dijo: "{fact}".' for fact in FACTS)
        prompt += (
            f" Cosas que {NICKNAME} te pidió que recuerdes (son datos de él, no tuyos): {dichos}"
        )
    return prompt

conversation = [{"role": "system", "content": build_system_prompt()}] + SAVED_HISTORY

def save_memory():
    with MEMORY_LOCK:
        data = {"hechos": FACTS, "historial": [m for m in conversation if m["role"] != "system"]}
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

def trim_conversation():
    """Deja el prompt del sistema y solo los últimos mensajes, para no desbordar el contexto."""
    del conversation[1:-MAX_HISTORY_MESSAGES]

def refresh_system_prompt():
    conversation[0]["content"] = build_system_prompt()

# Comandos de memoria
FACT_RE = re.compile(
    r"\b(?:acord[aá]te|acu[eé]rdate|record[aá]|recuerd[aá]|recuerda|no te olvides|ten[eé] en cuenta)"
    r"\s+(?:de\s+)?que\s+(.+)$"
)
FORGET_RE = re.compile(r"\bolv[ií]d(?:[aá]te|[aá])\s+(?:de\s+)?(?:que\s+)?(.+)$")
FORGET_ALL_RE = re.compile(r"todo(?: lo que .*)?")

def remember_fact(text):
    text = text.strip(" ,.;:¡!¿?")
    if not text:
        return "¿Qué querés que recuerde?"
    if any(text.lower() == fact.lower() for fact in FACTS):
        return "Eso ya lo tenía guardado, che."
    if len(FACTS) >= MAX_FACTS:
        return f"Ya tengo {MAX_FACTS} cosas guardadas. Decime que me olvide de alguna."
    FACTS.append(text)
    refresh_system_prompt()
    save_memory()
    return f"Listo, no me voy a olvidar: {text}."

def list_facts():
    if not FACTS:
        return "Todavía no me pediste que recuerde nada."
    palabra = "cosa" if len(FACTS) == 1 else "cosas"
    items = [f"Dijiste: {fact}." for fact in FACTS]
    return f"Me pediste que recuerde {len(FACTS)} {palabra}. " + " ".join(items)

def forget_fact(query):
    query = query.strip(" ,.;:¡!¿?").lower()
    if FORGET_ALL_RE.fullmatch(query):
        return forget_all()
    matches = [fact for fact in FACTS if query in fact.lower()]
    if not matches:
        return f"No encontré nada guardado sobre {query}."
    for fact in matches:
        FACTS.remove(fact)
    refresh_system_prompt()
    save_memory()
    palabra = "cosa" if len(matches) == 1 else "cosas"
    return f"Listo, me olvidé de {len(matches)} {palabra}."

def forget_all():
    cantidad = len(FACTS)
    FACTS.clear()
    del conversation[1:]
    refresh_system_prompt()
    save_memory()
    return f"Listo, borré toda mi memoria: {cantidad} cosas guardadas y lo que veníamos charlando."

# -----------------------------
# SKILL: WEATHER (Open-Meteo, free, no API key)
# -----------------------------
def get_weather(city):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=es"
        geo_resp = requests.get(geo_url, timeout=10).json()

        if "results" not in geo_resp:
            return f"Perdón, no encontré ningún lugar llamado {city}."

        lat = geo_resp["results"][0]["latitude"]
        lon = geo_resp["results"][0]["longitude"]
        place_name = geo_resp["results"][0]["name"]

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_resp = requests.get(weather_url, timeout=10).json()

        current = weather_resp["current_weather"]
        temp = current["temperature"]
        wind = current["windspeed"]

        return f"El clima actual en {place_name} es de {temp} grados Celsius, con viento de {wind} kilómetros por hora."

    except Exception as e:
        return f"Perdón, no pude obtener el clima. Error: {e}"

# -----------------------------
# SKILL: NEWS HEADLINES (BBC Mundo RSS, free, no API key)
# -----------------------------
def get_news():
    try:
        url = "https://feeds.bbci.co.uk/mundo/rss.xml"
        resp = requests.get(url, timeout=10)
        root = ET.fromstring(resp.content)

        headlines = []
        for item in root.findall(".//item")[:5]:
            title = item.find("title").text
            headlines.append(title)

        if not headlines:
            return "No encontré titulares en este momento."

        return "Estos son los titulares principales: " + ". ".join(headlines)

    except Exception as e:
        return f"Perdón, no pude obtener las noticias. Error: {e}"

# -----------------------------
# SKILL: DATE & TIME
# -----------------------------
def get_datetime_reply():
    now = datetime.datetime.now()
    dia = DIAS[now.weekday()]
    mes = MESES[now.month - 1]
    return f"Son las {now.strftime('%H:%M')} del {dia} {now.day} de {mes} de {now.year}."

# -----------------------------
# SKILL: GOOGLE MAPS
# -----------------------------
def open_maps(place):
    url = f"https://www.google.com/maps/search/{place.replace(' ', '+')}"
    return open_url(url, f"Abriendo Google Maps para {place}.")

# -----------------------------
# SKILL: WIKIPEDIA (free public REST API, no key)
# -----------------------------
def get_wikipedia_summary(topic):
    try:
        url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
        headers = {"User-Agent": "JarvisAssistant/1.0 (personal project; contact@example.com)"}
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code != 200:
            return f"Perdón, no encontré nada sobre {topic} en Wikipedia."

        data = resp.json()

        if "extract" not in data:
            return f"Perdón, no encontré nada sobre {topic} en Wikipedia."

        extract = data["extract"]
        sentences = extract.split(". ")
        short_version = ". ".join(sentences[:3])
        return short_version

    except Exception as e:
        return f"Perdón, no pude conectarme a Wikipedia. Error: {e}"

# -----------------------------
# SKILL: JOKE (fully offline, no key)
# -----------------------------
def tell_joke():
    try:
        return pyjokes.get_joke(language="es")
    except Exception as e:
        return f"Perdón, no se me ocurrió ningún chiste. Error: {e}"

# -----------------------------
# SKILL: OPEN WEBSITE (offline, no key)
# -----------------------------
def open_website(site):
    site = site.strip()
    known_sites = {
        "youtube": "https://youtube.com",
        "google": "https://google.com",
        "github": "https://github.com",
        "gmail": "https://mail.google.com",
        "reddit": "https://reddit.com",
    }
    if site in known_sites:
        url = known_sites[site]
    elif "." in site:
        url = "https://" + site
    else:
        url = f"https://{site}.com"

    return open_url(url, f"Abriendo {site}.")

# -----------------------------
# SKILL: NOTAS (se guardan en notas.json, que no se sube a git)
# -----------------------------
NOTES_FILE = os.path.join(DATA_DIR, "notas.json")
NOTE_RE = re.compile(r"\b(?:anot[aá]me|anot[aá]|agreg[aá] una nota|tom[aá] nota)\b(?: de| que)?\s+(.+)$")

def load_notes():
    try:
        with open(NOTES_FILE, encoding="utf-8") as f:
            notes = json.load(f)
        if isinstance(notes, list):
            return notes
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        pass
    # El archivo existe pero está roto: lo aparto para no pisarlo.
    try:
        os.replace(NOTES_FILE, NOTES_FILE + ".corrupto")
    except OSError:
        pass
    return []

def save_notes(notes):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

def add_note(text):
    try:
        notes = load_notes()
        notes.append({"texto": text, "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
        save_notes(notes)
        return f"Listo, anotado: {text}."
    except Exception as e:
        return f"Perdón, no pude guardar la nota. Error: {e}"

def list_notes():
    notes = load_notes()
    if not notes:
        return "No tenés nada anotado, che."
    items = [f"número {i}: {n.get('texto', '')}" for i, n in enumerate(notes, 1)]
    palabra = "nota" if len(notes) == 1 else "notas"
    return f"Tenés {len(notes)} {palabra}. " + ". ".join(items) + "."

def delete_last_note():
    try:
        notes = load_notes()
        if not notes:
            return "No hay ninguna nota para borrar."
        borrada = notes.pop()
        save_notes(notes)
        return f"Borré la última nota: {borrada.get('texto', '')}."
    except Exception as e:
        return f"Perdón, no pude borrar la nota. Error: {e}"

def clear_notes():
    try:
        cantidad = len(load_notes())
        save_notes([])
        return f"Listo, borré todas las notas ({cantidad})."
    except Exception as e:
        return f"Perdón, no pude borrar las notas. Error: {e}"

# -----------------------------
# SKILL: RECORDATORIOS (se guardan en recordatorios.json y sobreviven al cierre)
# -----------------------------
NUMBER_WORDS = {
    "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "quince": 15, "veinte": 20,
    "treinta": 30, "media": 0.5, "medio": 0.5,
}
UNIT_SECONDS = {"segundo": 1, "minuto": 60, "hora": 3600}
TIME_RE = re.compile(r"\ben (\d+|" + "|".join(NUMBER_WORDS) + r") (segundos?|minutos?|horas?)\b")
REMIND_RE = re.compile(r"\b(?:record(?:[aá]|ar)me|acord(?:[aá]|ar)me|avis(?:[aá]|ar)me)\b")
REMINDERS = []
REMINDERS_FILE = os.path.join(DATA_DIR, "recordatorios.json")
REMINDERS_LOCK = threading.Lock()

def save_reminders():
    """Guarda los pendientes en disco. Llamar con REMINDERS_LOCK tomado."""
    data = [{"texto": r["texto"], "due": r["due"].isoformat()} for r in REMINDERS]
    try:
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

def describe_due(due):
    now = datetime.datetime.now()
    hora = due.strftime("%H:%M")
    if due.date() == now.date():
        return f"a las {hora}"
    if due.date() == (now + datetime.timedelta(days=1)).date():
        return f"mañana a las {hora}"
    return f"el {due.day} de {MESES[due.month - 1]} a las {hora}"

def start_reminder(entry):
    """Programa el aviso de un recordatorio (entry tiene 'texto' y 'due')."""
    seconds = max(0, (entry["due"] - datetime.datetime.now()).total_seconds())
    timer = threading.Timer(seconds, fire_reminder, args=(entry,))
    timer.daemon = True
    entry["timer"] = timer
    timer.start()

def restore_reminders():
    """Al abrir Jarvis: reprograma los recordatorios guardados y devuelve los que
    vencieron mientras estaba cerrado, como lista de (fecha, texto)."""
    try:
        with open(REMINDERS_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        if not isinstance(saved, list):
            raise ValueError("formato inesperado")
    except FileNotFoundError:
        return []
    except (OSError, ValueError):
        # El archivo existe pero está roto: lo aparto para no pisarlo.
        try:
            os.replace(REMINDERS_FILE, REMINDERS_FILE + ".corrupto")
        except OSError:
            pass
        return []

    now = datetime.datetime.now()
    expired, pending = [], []
    for item in saved:
        try:
            entry = {"texto": str(item["texto"]), "due": datetime.datetime.fromisoformat(item["due"])}
        except (KeyError, TypeError, ValueError):
            continue
        (expired if entry["due"] <= now else pending).append(entry)

    with REMINDERS_LOCK:
        REMINDERS.extend(pending)
        save_reminders()
    for entry in pending:
        start_reminder(entry)
    return [(e["due"], e["texto"]) for e in expired]

def fire_reminder(entry):
    with REMINDERS_LOCK:
        if entry in REMINDERS:
            REMINDERS.remove(entry)
            save_reminders()
    msg = f"Ey {NICKNAME}, te acuerdo: {entry['texto']}."
    if NOTIFIER is not None:
        NOTIFIER(msg)

def set_reminder(command):
    trigger = REMIND_RE.search(command)
    when = TIME_RE.search(command, trigger.end()) or TIME_RE.search(command)
    if not when:
        return "Decime en cuánto tiempo, por ejemplo: recordame en 10 minutos llamar a mamá."

    amount = when.group(1)
    amount = int(amount) if amount.isdigit() else NUMBER_WORDS[amount]
    seconds = amount * UNIT_SECONDS[when.group(2).rstrip("s")]

    rest = command[trigger.end():]
    rest = TIME_RE.sub("", rest, count=1)
    text = re.sub(r"^\s*(?:de|que|para)\s+", "", rest.strip()).strip() or "lo que me pediste"

    due = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
    entry = {"texto": text, "due": due}
    with REMINDERS_LOCK:
        REMINDERS.append(entry)
        save_reminders()
    start_reminder(entry)
    return f"Dale, en {when.group(1)} {when.group(2)} te acuerdo: {text}."

def list_reminders():
    if not REMINDERS:
        return "No tenés recordatorios pendientes."
    pendientes = sorted(REMINDERS, key=lambda r: r["due"])
    items = [f"{describe_due(r['due'])}: {r['texto']}" for r in pendientes]
    if len(REMINDERS) == 1:
        cuenta = "1 recordatorio pendiente"
    else:
        cuenta = f"{len(REMINDERS)} recordatorios pendientes"
    return f"Tenés {cuenta}. " + ". ".join(items) + "."

# -----------------------------
# SKILL: BÚSQUEDAS EN LA WEB
# -----------------------------
SEARCH_RE = re.compile(
    r"\b(?:busc[aá]me|busc[aá]|googlea|googleá|googlear)\b(?:\s+en\s+(google|youtube))?\s*(?:de\s+|sobre\s+)?(.+)$"
)

def web_search(command):
    match = SEARCH_RE.search(command)
    site = match.group(1) or "google"
    query = match.group(2).strip()
    if site == "youtube":
        return open_url(f"https://www.youtube.com/results?search_query={quote_plus(query)}", f"Buscando {query} en YouTube.")
    return open_url(f"https://www.google.com/search?q={quote_plus(query)}", f"Buscando {query} en Google.")

# -----------------------------
# SKILLS ROUTER
# -----------------------------
OPEN_WORDS = ("abre", "abrí", "abri", "abrir", "abrime")

# "quién es X" / "qué es X" solo al principio de la frase y como palabras enteras,
# para que "creo que estoy cansado" no dispare una búsqueda en Wikipedia.
WIKI_RE = re.compile(r"^(?:qui[eé]n (?:es|fue)|qu[eé] es)\b\s*(.+)$")

def has_any(command, words):
    return any(w in command for w in words)

def route_command(command):
    opening = has_any(command, OPEN_WORDS)

    if SEARCH_RE.search(command) and "wikipedia" not in command:
        return web_search(command)

    elif has_any(command, ("borrá la memoria", "borra la memoria", "borrá toda la memoria", "borra toda la memoria")):
        return forget_all()

    elif FORGET_RE.search(command):
        return forget_fact(FORGET_RE.search(command).group(1))

    elif has_any(command, ("sabés de mí", "sabes de mí", "sabés de mi", "sabes de mi", "qué recordás", "que recordas", "qué recuerdas", "que recuerdas")):
        return list_facts()

    elif FACT_RE.search(command):
        return remember_fact(FACT_RE.search(command).group(1))

    elif REMIND_RE.search(command):
        return set_reminder(command)

    elif "recordatorios" in command:
        return list_reminders()

    elif has_any(command, ("borrá todas las notas", "borra todas las notas", "borrar todas las notas", "borrá las notas", "borra las notas")):
        return clear_notes()

    elif has_any(command, ("borrá la última nota", "borra la última nota", "borrá la ultima nota", "borra la ultima nota")):
        return delete_last_note()

    elif has_any(command, ("qué tengo anotado", "que tengo anotado", "mis notas", "las notas", "qué anoté", "que anote")):
        return list_notes()

    elif NOTE_RE.search(command):
        return add_note(NOTE_RE.search(command).group(1).strip())

    elif has_any(command, ("clima", "pronóstico", "pronostico")):
        if " en " in command:
            city = command.split(" en ")[-1].strip()
        else:
            city = DEFAULT_CITY
        return get_weather(city)

    elif has_any(command, ("noticias", "titulares")):
        return get_news()

    elif has_any(command, ("qué hora", "que hora", "la hora", "hora es", "fecha", "qué día", "que día")):
        return get_datetime_reply()

    elif has_any(command, ("mapa", "cómo llegar", "como llegar", "dónde queda", "donde queda", "dónde está", "donde está", "donde esta")):
        for trigger in ["mapa de", "cómo llegar a", "como llegar a", "dónde queda", "donde queda", "dónde está", "donde está", "donde esta"]:
            if trigger in command:
                place = command.split(trigger)[-1].strip()
                return open_maps(place)
        return open_maps(command.replace("mapa", "").strip())

    elif has_any(command, ("quién soy", "quien soy", "sobre mí", "sobre mi", "quién es mi desarrollador", "quien es mi desarrollador", "quién es mi creador", "quien es mi creador")):
        return (
            f"Vos sos {DEVELOPER_NAME}, mi creador, che. "
            f"Me armaste de cero, te peleaste con los drivers del micrófono, "
            f"y me enseñaste a escuchar, hablar y ayudarte con cosas reales. "
            f"Sin vos yo sería un archivo al pedo."
        )

    elif "wikipedia" in command or WIKI_RE.match(command):
        match = WIKI_RE.match(command)
        topic = (match.group(1) if match else command.split("wikipedia")[-1]).strip()
        if topic:
            return get_wikipedia_summary(topic)
        return None

    elif DESKTOP_LATE_HANDLER is not None and (reply := DESKTOP_LATE_HANDLER(command)):
        return reply

    elif has_any(command, ("chiste", "chistes")):
        return tell_joke()

    elif opening and has_any(command, ("sitio web", "página web", "pagina web", "youtube", "github", "reddit", "gmail")):
        for trigger in ["el sitio web", "sitio web", "la página web", "la pagina web", "abrime", "abrí", "abri", "abrir", "abre"]:
            if trigger in command:
                site = command.split(trigger)[-1].strip()
                if site:
                    return open_website(site)
        return None

    else:
        return None

def handle_command(command):
    """Primero los comandos de la app (escritorio), después los del cerebro."""
    if DESKTOP_HANDLER is not None:
        reply = DESKTOP_HANDLER(command)
        if reply:
            return reply
    return route_command(command)

# -----------------------------
# CORE: process a message (typed or spoken), return reply text
# -----------------------------
def get_reply(user_input):
    skill_reply = handle_command(user_input.lower())  # los comandos se buscan en minúsculas; el modelo ve el texto original
    if skill_reply:
        return skill_reply

    conversation.append({"role": "user", "content": user_input})
    try:
        reply = LLM_CHAT(conversation)
    except Exception as e:
        conversation.pop()  # no dejar el mensaje del usuario colgado sin respuesta
        return getattr(e, "user_message", LLM_ERROR_MESSAGE)  # el modelo puede traer su propio mensaje claro

    conversation.append({"role": "assistant", "content": reply})
    trim_conversation()
    save_memory()
    return reply
