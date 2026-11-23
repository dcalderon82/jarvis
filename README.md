# 🤖 Jarvis — Asistente de voz con IA

Un asistente de voz de escritorio hecho desde cero en Python, con una interfaz oscura inspirada en el J.A.R.V.I.S. de Iron Man. Habla **español rioplatense**, con onda y sin ser un robot. Funciona con herramientas gratuitas y locales: no necesita APIs pagas.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/LLM-Ollama-black?style=flat)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-1f6feb?style=flat)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Qué hace

Jarvis entiende comandos escritos y hablados:

- 💬 **Charla con naturalidad**: usa un modelo local (Ollama), así las conversaciones son privadas y gratis. Responde en voseo, informal y con humor
- 🎙️ **Escucha y responde por voz**, en español
- 👂 **Modo manos libres**: un botón lo deja escuchando y se activa cuando decís "Jarvis" (ver la nota de privacidad más abajo)
- 📝 **Notas por voz**: "anotá comprar pan", "qué tengo anotado", "borrá la última nota"
- ⏰ **Recordatorios**: "recordame en 10 minutos llamar a mamá", "qué recordatorios tengo"
- 🌦️ **Clima** de cualquier ciudad (Open-Meteo, sin clave)
- 📰 **Noticias** (BBC Mundo, por RSS)
- 📖 **Preguntas "quién es / qué es"** con resúmenes de Wikipedia en español
- 🕐 **Hora y fecha**
- 🗺️ **Google Maps** para un lugar o cómo llegar
- 📸 **Capturas de pantalla** a pedido
- 📊 **Info del sistema**: CPU, RAM y batería
- 😂 **Chistes** (en español)
- 🚀 **Abre apps y sitios**: Chrome, VS Code, Bloc de notas, YouTube, GitHub, Gmail, Reddit
- 🙋 **Te conoce**: lee tu nombre, tu ciudad y tus gustos desde un perfil

### Ejemplos de lo que podés decir

| Decí | Qué pasa |
|---|---|
| "Qué hora es" | Te dice la hora y la fecha |
| "Clima en Córdoba" | Te cuenta el clima de Córdoba |
| "Quién es Messi" | Resumen de Wikipedia |
| "Abrí YouTube" | Abre el sitio |
| "Anotá llamar al dentista" | Guarda una nota |
| "Recordame en 5 minutos sacar el pan" | Te avisa a los 5 minutos, en el chat y en voz |
| "Contame un chiste" | Un chiste de programadores |

---

## 🛠️ Tecnologías

| Para qué | Librería |
|---|---|
| Modelo de lenguaje | `ollama` (local) |
| Interfaz | `customtkinter` |
| Voz a texto | `SpeechRecognition` + `PyAudio` (Google, `es-AR`) |
| Texto a voz | `pyttsx3` (voces de Windows en español) |
| Clima | API REST de Open-Meteo |
| Noticias | RSS de BBC Mundo |
| Consultas | API REST de Wikipedia (es) |
| Info del sistema | `psutil` |
| Capturas | `pyautogui` |
| Chistes | `pyjokes` |

---

## ⚙️ Instalación

### Requisitos
- Python 3.12 o superior
- [Ollama](https://ollama.com) instalado y corriendo, con un modelo descargado. Recomendado:
  ```bash
  ollama pull llama3.1:8b
  ```
  (`llama3.2` es más liviano y rápido, pero sigue peor las instrucciones.)
- Una **voz de Windows en español** para que Jarvis hable. Se instala en *Configuración → Hora e idioma → Voz*. Jarvis busca primero la mexicana (Sabina) y después la de España (Helena).

### Instalar

```bash
git clone https://github.com/<tu-usuario>/jarvis.git
cd jarvis
python -m venv venv
venv\Scripts\activate        # Windows
pip install customtkinter ollama pyttsx3 SpeechRecognition pyaudio requests pyautogui psutil pyjokes
```

### Crear tu perfil

Copiá la plantilla y completala con tus datos:

```bash
copy perfil.ejemplo.json perfil.json
```

```json
{
  "nombre": "Tu nombre",
  "apodo": "Como querés que te diga Jarvis",
  "ciudad": "Tu ciudad",
  "gustos": ["algo que te guste"],
  "sobre_mi": "Una o dos frases sobre vos.",
  "modelo": "llama3.1:8b"
}
```

`perfil.json` es personal y está en el `.gitignore`, así que no se sube a GitHub. Si no existe, Jarvis usa la plantilla.

### Ejecutar

```bash
python jarvis_gui.py
```

Escribí un mensaje, tocá **🎤 Hablar** para hablarle una vez, o activá **👂 Manos libres** y decí "Jarvis".

---

## 👂 Modo manos libres

El botón **👂 Manos libres** arranca apagado. Al activarlo, Jarvis escucha de forma continua:

- "Jarvis, qué hora es" → lo procesa directo.
- Solo "Jarvis" → contesta "¿Sí?" y espera tu pedido.
- Si no entiende lo que dijiste, te pide que lo repitas (hasta 3 intentos).
- Lo que se diga sin la palabra "Jarvis" se ignora.

> ⚠️ **Privacidad:** el reconocimiento de voz usa el servicio de Google. Mientras el modo manos libres está activo, todo lo que se hable cerca del micrófono se envía a Google para transcribirlo, no solo tus pedidos. Por eso es opcional y arranca apagado.

---

## 🐞 Problemas resueltos

Armarlo dejó a la vista varias rarezas del audio en Windows que vale la pena documentar:

- **Detección de WASAPI**: `PyAudio` necesitó buscar explícitamente el host WASAPI para encontrar el micrófono por defecto y su frecuencia de muestreo nativa en Windows con drivers Realtek, en vez de asumir el dispositivo 0.
- **Motor de voz que dejaba de andar**: crear el motor (`pyttsx3.init()`) de nuevo en cada llamada a `speak()` evitó que dejara de funcionar en silencio después de unas pocas veces.
- **Ollama y el PATH**: Ollama tiene que estar corriendo como servicio y accesible antes de que el cliente de Python se conecte; si falla, Jarvis avisa con un mensaje amigable.
- **Transcripciones imperfectas**: Google a veces escribe "recordarme" por "recordame" o recorta palabras ("recordatorios tengo" por "qué recordatorios tengo"). Los comandos aceptan esas variantes.
- **Eco en el manos libres**: mientras Jarvis habla, el micrófono podría escucharse a sí mismo, así que después de hablar se descarta lo que grabó.

Se incluyen scripts de prueba (`test_wasapi.py`, `test_all_devices.py`, `test_mic.py`, `test_pyaudio.py`, `test_stream.py`, `test_record_and_save.py`) que sirvieron para aislar y confirmar el micrófono y la frecuencia correctos. Ojo: `test_mic.py` y `test_record_and_save.py` reconocen en inglés.

---

## 📁 Estructura del proyecto

```
jarvis/
├── jarvis_gui.py            # aplicación principal
├── perfil.ejemplo.json      # plantilla del perfil (copiala a perfil.json)
├── perfil.json              # tus datos (no se sube a git)
├── notas.json               # tus notas (se crea solo, no se sube a git)
├── test_wasapi.py           # diagnóstico de WASAPI
├── test_all_devices.py      # recorre todos los dispositivos de entrada
├── test_mic.py              # prueba básica de micrófono y reconocimiento
├── test_pyaudio.py          # lista los dispositivos de PyAudio
├── test_stream.py           # prueba de apertura y lectura del stream
├── test_record_and_save.py  # graba, guarda y transcribe
└── README.md
```

---

## 🔭 Ideas a futuro

- [ ] Recordatorios que sobrevivan al cierre de Jarvis
- [ ] Memoria de conversaciones entre sesiones
- [ ] Controlar la compu: volumen, música, buscar en Google
- [ ] Empaquetar como `.exe` para distribuirlo más fácil
- [ ] Más habilidades (calendario, domótica)

---

## 📄 Licencia

MIT: sentite libre de hacer un fork y construir sobre esto.
