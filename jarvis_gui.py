import customtkinter as ctk
import threading
import ollama
import pyttsx3
import speech_recognition as sr
import pyaudio
import subprocess
import webbrowser
import datetime
import requests
import xml.etree.ElementTree as ET
import pyautogui
import psutil
import pyjokes
import os
import json
import re

# -----------------------------
# PERFIL (se lee de perfil.json; copiá perfil.ejemplo.json y completalo)
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_profile():
    for filename in ("perfil.json", "perfil.ejemplo.json"):
        try:
            with open(os.path.join(BASE_DIR, filename), encoding="utf-8") as f:
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
# FIND WORKING MIC (WASAPI + native sample rate)
# -----------------------------
p = pyaudio.PyAudio()
wasapi_index = None
for i in range(p.get_host_api_count()):
    info = p.get_host_api_info_by_index(i)
    if "WASAPI" in info["name"]:
        wasapi_index = i
        break

mic_device_index = p.get_host_api_info_by_index(wasapi_index)["defaultInputDevice"]
device_info = p.get_device_info_by_index(mic_device_index)
mic_sample_rate = int(device_info["defaultSampleRate"])
p.terminate()

# -----------------------------
# SETTINGS
# -----------------------------
MODEL = PROFILE.get("modelo", "llama3.2")  # modelo de Ollama (se cambia en perfil.json)
SPEECH_LANGUAGE = "es-AR"  # idioma del micrófono (ej: "es-AR", "es-ES", "en-US")
# Voces de Windows preferidas para hablar, en orden (se busca en el id de la voz).
TTS_VOICE_PREFERENCE = ["ES-MX", "ES-ES"]

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

recognizer = sr.Recognizer()
recognizer.pause_threshold = 1
recognizer.energy_threshold = 200

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
    return prompt

conversation = [{"role": "system", "content": build_system_prompt()}]

# -----------------------------
# TEXT TO SPEECH
# -----------------------------
def speak(text):
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    for preferred in TTS_VOICE_PREFERENCE:
        match = next((v for v in voices if preferred in v.id.upper()), None)
        if match:
            engine.setProperty("voice", match.id)
            break
    engine.setProperty("rate", 175)
    engine.say(text)
    engine.runAndWait()
    engine.stop()

# -----------------------------
# SPEECH RECOGNITION
# -----------------------------
def listen():
    with sr.Microphone(device_index=mic_device_index, sample_rate=mic_sample_rate, chunk_size=1024) as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=5)
        except sr.WaitTimeoutError:
            return None

    try:
        text = recognizer.recognize_google(audio, language=SPEECH_LANGUAGE)
        return text.lower()
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        return None

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
    webbrowser.open(url)
    return f"Abriendo Google Maps para {place}."

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
# SKILL: SCREENSHOT (offline, no key)
# -----------------------------
def take_screenshot():
    try:
        folder = os.path.join(os.path.expanduser("~"), "Desktop", "jarvis", "screenshots")
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(folder, f"screenshot_{timestamp}.png")

        img = pyautogui.screenshot()
        img.save(filepath)

        return f"Captura de pantalla guardada en {filepath}."
    except Exception as e:
        return f"Perdón, no pude tomar la captura de pantalla. Error: {e}"

# -----------------------------
# SKILL: SYSTEM INFO (offline, no key)
# -----------------------------
def get_system_info():
    try:
        battery = psutil.sensors_battery()
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent

        parts = [f"El uso de CPU es del {cpu} por ciento", f"El uso de RAM es del {ram} por ciento"]

        if battery:
            plugged = "conectada al cargador" if battery.power_plugged else "usando batería"
            parts.append(f"la batería está al {battery.percent} por ciento, {plugged}")

        return ". ".join(parts) + "."
    except Exception as e:
        return f"Perdón, no pude obtener la información del sistema. Error: {e}"

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

    webbrowser.open(url)
    return f"Abriendo {site}."

# -----------------------------
# SKILL: NOTAS (se guardan en notas.json, que no se sube a git)
# -----------------------------
NOTES_FILE = os.path.join(BASE_DIR, "notas.json")
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
# SKILL: RECORDATORIOS (viven mientras Jarvis esté abierto)
# -----------------------------
NUMBER_WORDS = {
    "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "quince": 15, "veinte": 20,
    "treinta": 30, "media": 0.5, "medio": 0.5,
}
UNIT_SECONDS = {"segundo": 1, "minuto": 60, "hora": 3600}
TIME_RE = re.compile(r"\ben (\d+|" + "|".join(NUMBER_WORDS) + r") (segundos?|minutos?|horas?)\b")
REMIND_RE = re.compile(r"\b(?:record[aá]me|acord[aá]me|avis[aá]me)\b")
REMINDERS = []

def fire_reminder(entry):
    if entry in REMINDERS:
        REMINDERS.remove(entry)
    msg = f"Ey {NICKNAME}, te acuerdo: {entry['texto']}."
    add_message("Jarvis", msg)
    speak(msg)

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
    entry = {"texto": text, "hora": due.strftime("%H:%M")}
    timer = threading.Timer(seconds, fire_reminder, args=(entry,))
    timer.daemon = True
    entry["timer"] = timer
    REMINDERS.append(entry)
    timer.start()
    return f"Dale, en {when.group(1)} {when.group(2)} te acuerdo: {text}."

def list_reminders():
    if not REMINDERS:
        return "No tenés recordatorios pendientes."
    items = [f"a las {r['hora']}: {r['texto']}" for r in REMINDERS]
    palabra = "recordatorio" if len(REMINDERS) == 1 else "recordatorios"
    return f"Tenés {len(REMINDERS)} {palabra} pendientes. " + ". ".join(items) + "."

# -----------------------------
# SKILLS ROUTER
# -----------------------------
OPEN_WORDS = ("abre", "abrí", "abri", "abrir", "abrime")

def has_any(command, words):
    return any(w in command for w in words)

def handle_command(command):
    opening = has_any(command, OPEN_WORDS)

    if opening and "chrome" in command:
        subprocess.Popen("start chrome", shell=True)
        return "Abriendo Chrome."

    elif opening and has_any(command, ("bloc de notas", "notepad")):
        subprocess.Popen("notepad")
        return "Abriendo el Bloc de notas."

    elif opening and has_any(command, ("vs code", "vscode", "visual studio code")):
        subprocess.Popen("code", shell=True)
        return "Abriendo VS Code."

    elif REMIND_RE.search(command):
        return set_reminder(command)

    elif has_any(command, ("qué recordatorios", "que recordatorios", "mis recordatorios")):
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

    elif "wikipedia" in command or has_any(command, ("quién es", "quien es", "quién fue", "quien fue", "qué es", "que es")):
        for trigger in ["wikipedia", "quién es", "quien es", "quién fue", "quien fue", "qué es", "que es"]:
            if trigger in command:
                topic = command.split(trigger)[-1].strip()
                if topic:
                    return get_wikipedia_summary(topic)
        return None

    elif has_any(command, ("captura de pantalla", "pantallazo", "screenshot")):
        return take_screenshot()

    elif has_any(command, ("información del sistema", "informacion del sistema", "info del sistema", "batería", "bateria", "cpu", "memoria ram", "uso de ram")):
        return get_system_info()

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

# -----------------------------
# CORE: process a message (typed or spoken), return reply text
# -----------------------------
def get_reply(user_input):
    skill_reply = handle_command(user_input)
    if skill_reply:
        return skill_reply

    conversation.append({"role": "user", "content": user_input})
    try:
        response = ollama.chat(model=MODEL, messages=conversation)
        reply = response["message"]["content"]
    except Exception as e:
        return "Perdón, no puedo conectarme a Ollama. Asegurate de que esté corriendo."

    conversation.append({"role": "assistant", "content": reply})
    return reply

# =====================================================
# GUI
# =====================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Jarvis")
app.geometry("600x700")

chat_box = ctk.CTkTextbox(app, width=560, height=550, font=("Segoe UI", 14))
chat_box.pack(padx=20, pady=(20, 10))
chat_box.configure(state="disabled")

def add_message(sender, text):
    chat_box.configure(state="normal")
    chat_box.insert("end", f"{sender}: {text}\n\n")
    chat_box.configure(state="disabled")
    chat_box.see("end")

def process_and_reply(user_input):
    add_message("You", user_input)
    reply = get_reply(user_input)
    add_message("Jarvis", reply)
    speak(reply)

def on_send():
    text = entry.get().strip()
    if not text:
        return
    entry.delete(0, "end")
    threading.Thread(target=process_and_reply, args=(text,), daemon=True).start()

def on_mic():
    def listen_and_process():
        add_message("Sistema", "Escuchando...")
        heard = listen()
        if heard is None:
            add_message("Sistema", "No te entendí nada, boludo. Probá de nuevo.")
            return
        process_and_reply(heard)

    threading.Thread(target=listen_and_process, daemon=True).start()

bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
bottom_frame.pack(padx=20, pady=(0, 20), fill="x")

entry = ctk.CTkEntry(bottom_frame, placeholder_text="Escribí un mensaje...", font=("Segoe UI", 14))
entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
entry.bind("<Return>", lambda event: on_send())

send_button = ctk.CTkButton(bottom_frame, text="Enviar", width=70, command=on_send)
send_button.pack(side="left", padx=(0, 10))

mic_button = ctk.CTkButton(bottom_frame, text="🎤 Hablar", width=90, command=on_mic)
mic_button.pack(side="left")

GREETING = f"Ey {NICKNAME}, acá estoy. ¿Qué hacemos hoy?"
add_message("Jarvis", GREETING)
threading.Thread(target=speak, args=(GREETING,), daemon=True).start()

app.mainloop()