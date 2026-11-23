import customtkinter as ctk
import threading
import pyttsx3
import speech_recognition as sr
import pyaudio
import subprocess
import webbrowser
import datetime
import pyautogui
import psutil
import os
import re
import ctypes

import jarvis_core as core
from jarvis_core import has_any, OPEN_WORDS, NICKNAME, describe_due, restore_reminders, get_reply

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
SPEECH_LANGUAGE = "es-AR"  # idioma del micrófono (ej: "es-AR", "es-ES", "en-US")
# Voces de Windows preferidas para hablar, en orden (se busca en el id de la voz).
TTS_VOICE_PREFERENCE = ["ES-MX", "ES-ES"]

recognizer = sr.Recognizer()
recognizer.pause_threshold = 1
recognizer.energy_threshold = 200

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
def transcribe(audio):
    try:
        text = recognizer.recognize_google(audio, language=SPEECH_LANGUAGE)
        return text.lower()
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        return None

def listen():
    with sr.Microphone(device_index=mic_device_index, sample_rate=mic_sample_rate, chunk_size=1024) as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        try:
            audio = recognizer.listen(source, timeout=5)
        except sr.WaitTimeoutError:
            return None

    return transcribe(audio)

# Palabra clave del modo manos libres. Google a veces escribe "yarvis", "jarbis", etc.
WAKE_RE = re.compile(r"\b(?:j|y|ll|ch|d|g|h)[aá]r[vb][ií]s\b")

def extract_wake_command(text):
    """None si no se dijo la palabra clave; si se dijo, lo que vino después (puede ser vacío)."""
    match = WAKE_RE.search(text)
    if not match:
        return None
    return text[match.end():].strip(" ,.;:¡!¿?")

def flush_mic(source):
    """Descarta lo que el micrófono grabó mientras Jarvis hablaba (evita que se escuche a sí mismo)."""
    try:
        stream = source.stream.pyaudio_stream
        available = stream.get_read_available()
        if available:
            stream.read(available, exception_on_overflow=False)
    except Exception:
        pass

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
# SKILL: CONTROL DE LA COMPU (volumen, música, búsquedas, carpetas, bloqueo)
# No apaga ni reinicia la compu a propósito: un "apagá" mal transcrito haría perder trabajo.
# -----------------------------
VOLUME_STEP_PRESSES = 5  # cada pulsación mueve ~2%: 5 pulsaciones ≈ 10%
VOLUME_SET_RE = re.compile(r"\b(?:en|al|a)\s+(\d{1,3})\b")
MUSIC_WORDS = {"música", "musica", "canción", "cancion", "reproducción", "reproduccion"}
FOLDERS = {
    "descargas": "Downloads", "documentos": "Documents", "escritorio": "Desktop",
    "imágenes": "Pictures", "imagenes": "Pictures", "fotos": "Pictures",
    "música": "Music", "musica": "Music", "videos": "Videos", "vídeos": "Videos",
}

def words_of(command):
    return set(re.findall(r"\w+", command))

def press_key(key, times=1):
    if times <= 0:
        return True
    try:
        pyautogui.press(key, presses=times, interval=0.01)
        return True
    except Exception:
        return False

def set_volume(level):
    """Baja todo al mínimo y sube hasta el nivel pedido (cada pulsación ≈ 2%)."""
    return press_key("volumedown", 50) and press_key("volumeup", round(level / 2))

def control_volume(command):
    fallo = "Perdón, no pude tocar el volumen."
    if has_any(command, ("silenciá", "silencia", "silenciar", "mutea", "mutear", "mute")):
        return "Listo, alterné el silencio." if press_key("volumemute") else fallo

    match = VOLUME_SET_RE.search(command)
    if match:
        level = max(0, min(100, int(match.group(1))))
        return f"Listo, volumen al {level} por ciento, más o menos." if set_volume(level) else fallo
    if has_any(command, ("máximo", "maximo")):
        return "Listo, volumen al máximo." if set_volume(100) else fallo
    if has_any(command, ("mínimo", "minimo")):
        return "Listo, volumen al mínimo." if set_volume(0) else fallo

    words = words_of(command)
    if words & {"subí", "subi", "subir", "subile", "sube", "más", "aumentá", "aumenta"}:
        return "Listo, subí el volumen." if press_key("volumeup", VOLUME_STEP_PRESSES) else fallo
    if words & {"bajá", "baja", "bajar", "bajale", "menos", "disminuí", "disminui"}:
        return "Listo, bajé el volumen." if press_key("volumedown", VOLUME_STEP_PRESSES) else fallo
    return "¿Querés que suba o baje el volumen?"

def music_action(command):
    """Devuelve la tecla multimedia que corresponde, o None si no es un pedido de música."""
    words = words_of(command)
    if has_any(command, ("poné play", "pone play", "dale play", "poné pausa", "pone pausa")):
        return "playpause"
    if not (words & MUSIC_WORDS):
        return None
    if words & {"siguiente", "próxima", "proxima", "cambiá", "cambia"}:
        return "nexttrack"
    if words & {"anterior", "volvé", "volve"}:
        return "prevtrack"
    if words & {"pausá", "pausa", "pará", "seguí", "continuá", "continua", "reanudá", "reproducí", "poné", "pone"}:
        return "playpause"
    return None

def control_music(key):
    if not press_key(key):
        return "Perdón, no pude controlar la música."
    return {
        "playpause": "Listo, play o pausa.",
        "nexttrack": "Listo, siguiente canción.",
        "prevtrack": "Listo, canción anterior.",
    }[key]

def folder_name(command):
    for word in re.findall(r"\w+", command):
        if word in FOLDERS:
            return word
    return None

def open_folder(name):
    home = os.path.expanduser("~")
    for base in (home, os.path.join(home, "OneDrive")):
        path = os.path.join(base, FOLDERS[name])
        if os.path.isdir(path):
            os.startfile(path)
            return f"Abriendo {name}."
    return f"No encontré la carpeta de {name}."

def lock_screen():
    try:
        ctypes.windll.user32.LockWorkStation()
        return "Listo, bloqueando la pantalla."
    except Exception as e:
        return f"Perdón, no pude bloquear la pantalla. Error: {e}"

# -----------------------------
# COMANDOS QUE SOLO EXISTEN EN LA PC (se enchufan al cerebro)
# -----------------------------
def desktop_handler(command):
    """Comandos de la PC que van primero. Devuelve la respuesta, o None si no es uno de ellos."""
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

    elif opening and "calculadora" in command:
        subprocess.Popen("calc")
        return "Abriendo la calculadora."

    elif opening and "explorador" in command:
        subprocess.Popen("explorer")
        return "Abriendo el explorador de archivos."

    elif opening and folder_name(command) and not has_any(command, ("youtube", "github", "reddit", "gmail")):
        return open_folder(folder_name(command))

    elif has_any(command, ("bloqueá la pantalla", "bloquea la pantalla", "bloquear la pantalla",
                           "bloqueá la compu", "bloquea la compu", "bloqueá la computadora", "bloquea la computadora")):
        return lock_screen()

    elif "volumen" in command or has_any(command, ("silenciá", "silencia el", "silenciar", "mutea", "mutear")):
        return control_volume(command)

    elif music_action(command):
        return control_music(music_action(command))

    else:
        return None

def desktop_late_handler(command):
    """Comandos de la PC que se evalúan después de Wikipedia (como antes de separar el cerebro)."""
    if has_any(command, ("captura de pantalla", "pantallazo", "screenshot")):
        return take_screenshot()

    elif has_any(command, ("información del sistema", "informacion del sistema", "info del sistema", "batería", "bateria", "cpu", "memoria ram", "uso de ram")):
        return get_system_info()

    else:
        return None

core.URL_OPENER = webbrowser.open
core.DESKTOP_HANDLER = desktop_handler
core.DESKTOP_LATE_HANDLER = desktop_late_handler

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

def notify(msg):
    """Aviso de un recordatorio: se escribe en el chat y se dice en voz alta."""
    add_message("Jarvis", msg)
    speak(msg)

core.NOTIFIER = notify

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

# -----------------------------
# MANOS LIBRES: escucha siempre y se activa al decir "Jarvis" (opcional, arranca apagado)
# -----------------------------
handsfree_stop = threading.Event()
handsfree_stop.set()  # apagado al iniciar
handsfree_thread = None

def wait_for_command(source):
    """Después de decir solo 'Jarvis': contesta '¿Sí?' y espera el pedido.
    Si repite 'Jarvis' sin pedido, sigue esperando. Si no entiende, pide que lo repitas
    (hasta 3 intentos en total)."""
    add_message("Jarvis", "¿Sí?")
    speak("¿Sí?")
    flush_mic(source)
    for attempt in range(3):
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            return None
        heard = transcribe(audio)
        if not heard:
            if attempt < 2:
                add_message("Jarvis", "No te entendí, boludo. Repetilo.")
                speak("No te entendí, boludo. Repetilo.")
                flush_mic(source)
                continue
            add_message("Sistema", "No te entendí nada, boludo. Probá de nuevo.")
            return None
        after_wake = extract_wake_command(heard)
        command = heard if after_wake is None else after_wake
        if command:
            return command
        # Solo repitió "Jarvis": seguimos esperando el pedido.
    return None

def handsfree_loop():
    try:
        with sr.Microphone(device_index=mic_device_index, sample_rate=mic_sample_rate, chunk_size=1024) as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            add_message("Sistema", "Manos libres activado. Decí 'Jarvis' y después tu pedido.")
            while not handsfree_stop.is_set():
                try:
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=8)
                except sr.WaitTimeoutError:
                    continue

                text = transcribe(audio)
                command = extract_wake_command(text) if text else None
                if command is None:
                    continue  # no dijo "Jarvis": se ignora

                if not command:
                    # Dijo solo "Jarvis": responde y espera el pedido.
                    command = wait_for_command(source)
                    if not command:
                        continue

                process_and_reply(command)
                flush_mic(source)
    except Exception as e:
        add_message("Sistema", f"El manos libres se detuvo: {e}")
    finally:
        handsfree_stop.set()
        app.after(0, reset_handsfree_ui)

def reset_handsfree_ui():
    handsfree_button.configure(text="👂 Manos libres", fg_color=HANDSFREE_OFF_COLOR)
    mic_button.configure(state="normal")
    add_message("Sistema", "Manos libres apagado.")

def on_handsfree():
    global handsfree_thread
    if handsfree_thread is not None and handsfree_thread.is_alive():
        handsfree_stop.set()  # se apaga solo en un segundo o dos
        return
    handsfree_stop.clear()
    handsfree_button.configure(text="👂 Escuchando: ON", fg_color="#2e7d32")
    mic_button.configure(state="disabled")  # el micrófono lo usa el manos libres
    handsfree_thread = threading.Thread(target=handsfree_loop, daemon=True)
    handsfree_thread.start()

bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
bottom_frame.pack(padx=20, pady=(0, 20), fill="x")

entry = ctk.CTkEntry(bottom_frame, placeholder_text="Escribí un mensaje...", font=("Segoe UI", 14))
entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
entry.bind("<Return>", lambda event: on_send())

send_button = ctk.CTkButton(bottom_frame, text="Enviar", width=70, command=on_send)
send_button.pack(side="left", padx=(0, 10))

mic_button = ctk.CTkButton(bottom_frame, text="🎤 Hablar", width=90, command=on_mic)
mic_button.pack(side="left", padx=(0, 10))

handsfree_button = ctk.CTkButton(bottom_frame, text="👂 Manos libres", width=140, command=on_handsfree)
handsfree_button.pack(side="left")
HANDSFREE_OFF_COLOR = handsfree_button.cget("fg_color")

GREETING = f"Ey {NICKNAME}, acá estoy. ¿Qué hacemos hoy?"
add_message("Jarvis", GREETING)

# Recordatorios guardados: se reprograman, y se avisa de los que vencieron con Jarvis cerrado.
EXPIRED_MESSAGES = [
    f"Ey {NICKNAME}, mientras yo estaba cerrado se te pasó un recordatorio, {describe_due(due)}: {texto}."
    for due, texto in restore_reminders()
]
for message in EXPIRED_MESSAGES:
    add_message("Jarvis", message)

def startup_speech():
    speak(GREETING)
    for message in EXPIRED_MESSAGES:
        speak(message)

threading.Thread(target=startup_speech, daemon=True).start()

app.mainloop()
