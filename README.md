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
- ⏰ **Recordatorios**: "recordame en 10 minutos llamar a mamá", "qué recordatorios tengo". Se guardan en disco: si cerrás Jarvis, al abrirlo se reprograman, y los que vencieron mientras estaba cerrado te los avisa al arrancar
- 🧠 **Memoria a largo plazo**: "acordate que mi perro se llama Toby" y se acuerda aunque cierres Jarvis. También retoma lo que venían charlando (los últimos mensajes). "Qué sabés de mí" lista lo que le pediste, "olvidate de que…" borra un dato y "borrá la memoria" borra todo
- 🎛️ **Controla tu compu**: "subí el volumen", "poné el volumen en 30", "silenciá", "pausá la música", "siguiente canción", "buscá en Google recetas de pizza", "abrí descargas", "abrí la calculadora", "bloqueá la pantalla". No apaga ni reinicia la compu a propósito, porque un comando mal transcrito te haría perder trabajo sin guardar
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
| "Poné el volumen en 30" | Deja el volumen cerca del 30 % (cada pulsación mueve ~2 %, es aproximado) |
| "Pausá la música" / "siguiente canción" | Usa las teclas multimedia de Windows |
| "Buscá en YouTube música relajante" | Abre la búsqueda en el navegador |
| "Acordate que me gusta el mate" | Lo guarda en su memoria para siempre |
| "Qué sabés de mí" | Lista lo que le pediste que recuerde |
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

## 🌐 Versión web (para usar desde el celular)

`jarvis_web.py` sirve el mismo cerebro (`jarvis_core.py`) con una página de chat pensada para el celular: se puede escribir o hablar, y Jarvis contesta por escrito y en voz alta. Se instala aparte, sin nada de escritorio:

```bash
pip install -r requirements-web.txt
```

Para probarla en tu PC (en PowerShell):

```powershell
$env:JARVIS_PASSWORD = "una-clave-larga-y-unica"   # obligatoria, mínimo 10 caracteres
$env:JARVIS_COOKIE_SECURE = "0"                     # solo para probar en http://localhost
python jarvis_web.py                                # http://127.0.0.1:8000
```

| Variable | Para qué |
|---|---|
| `JARVIS_PASSWORD` | Contraseña de entrada (obligatoria) |
| `JARVIS_SECRET` | Clave para firmar la sesión (recomendada; si falta se genera una al arrancar) |
| `JARVIS_COOKIE_SECURE` | `1` (por defecto) exige HTTPS; `0` solo para probar en localhost |
| `JARVIS_TRUST_PROXY` | `1` si está detrás del proxy de un hosting |
| `JARVIS_TZ` | Zona horaria (por defecto `America/Argentina/Buenos_Aires`) |
| `JARVIS_DAILY_LIMIT` | Tope de mensajes por día (por defecto 300) |
| `ANTHROPIC_API_KEY` | Tu clave de la API de Claude: con ella Jarvis piensa con Claude (ver más abajo) |
| `JARVIS_BRAIN` | `claude` u `ollama`. Por defecto, `claude` si hay clave; si no, `ollama` (solo para probar en tu PC) |
| `JARVIS_CLAUDE_MODEL` | Modelo de Claude (por defecto `claude-sonnet-5-5`) |
| `JARVIS_CLAUDE_EFFORT` | Cuánto razona antes de contestar: `low` (por defecto, es un chat), `medium` o `high` |
| `JARVIS_CLAUDE_MAX_TOKENS` | Tope de tokens por respuesta (por defecto 3000) |
| `JARVIS_CLAUDE_FALLBACKS` | `1` (por defecto) activa el respaldo automático si un modelo se niega a responder; `0` lo apaga |

### 🧠 El cerebro online: la API de Claude

Online no hay Ollama: Jarvis piensa con la API de Claude, usando el SDK oficial (`anthropic`). Es de **pago por uso**, así que conviene cuidar el gasto:

1. Creá una cuenta en la consola de Anthropic y generá una **clave de la API**. La clave es como una contraseña: no la pegues en el código, en el chat ni en el repositorio. Va solo en la variable de entorno `ANTHROPIC_API_KEY`.
2. En la consola, **fijá un tope de gasto mensual**. Es tu red de seguridad principal; el tope de 300 mensajes por día de Jarvis es la segunda.
3. Probá la clave con un solo pedido chiquito (cuesta una fracción de centavo):

```powershell
$env:ANTHROPIC_API_KEY = "tu-clave"     # solo vale para esta ventana de PowerShell
python probar_claude.py
```

Los modelos se eligen por costo y capacidad: Sonnet 5.5 (por defecto) es un buen equilibrio para un chat; Opus 5.5 es el más capaz y el más caro; Haiku 5.5 es el más barato. Los mensajes viajan a Anthropic para que el modelo responda, junto con tu perfil y los datos que le pediste recordar.

**Privacidad:** en los registros del servidor solo quedan el modelo, los tokens y el id del pedido, nunca tu clave ni tus mensajes. Eso vale mientras no actives `ANTHROPIC_LOG=debug`: el SDK, en ese modo, registra el contenido de los pedidos. No lo uses en producción.

**Seguridad:** entra solo con contraseña; 5 intentos fallidos bloquean esa IP por 15 minutos; la sesión es una cookie `HttpOnly`; los pedidos exigen JSON, una cabecera propia y el mismo origen; hay topes de 20 mensajes por minuto y 300 por día; y solo se sirven los 4 archivos de la página (nunca tus notas, tu memoria ni tu perfil).

**Qué cambia respecto del escritorio:** los comandos de la PC (volumen, música, carpetas, bloqueo, capturas, info del sistema) no existen en la web. Las búsquedas y los mapas devuelven un link para tocar. Los recordatorios avisan en la página mientras esté abierta y el servidor, encendido. La voz usa el reconocimiento de tu navegador (en iPhone funciona en Safari; si falla, probá el dictado del teclado).

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
├── jarvis_core.py           # el "cerebro": perfil, memoria, notas, recordatorios y comandos (sin ventana ni micrófono)
├── jarvis_gui.py            # app de escritorio: ventana, micrófono, voz y comandos de la PC
├── jarvis_web.py            # servidor web para usar Jarvis desde el celular
├── jarvis_claude.py         # conecta el cerebro con la API de Claude (versión online)
├── probar_claude.py         # prueba tu clave de la API con un pedido chiquito
├── web/                     # la página de chat (index.html, app.js, style.css)
├── requirements-web.txt     # dependencias de la versión web
├── perfil.ejemplo.json      # plantilla del perfil (copiala a perfil.json)
├── perfil.json              # tus datos (no se sube a git)
├── notas.json               # tus notas (se crea solo, no se sube a git)
├── recordatorios.json       # recordatorios pendientes (se crea solo, no se sube a git)
├── memoria.json             # memoria a largo plazo (se crea sola, no se sube a git)
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

- [ ] Empaquetar como `.exe` para distribuirlo más fácil
- [ ] Más habilidades (calendario, domótica)

---

## 📄 Licencia

MIT: sentite libre de hacer un fork y construir sobre esto.
