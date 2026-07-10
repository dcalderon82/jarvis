# 🤖 Jarvis — AI Voice Assistant

A desktop AI voice assistant built from scratch in Python, with a dark, HUD-style interface inspired by Iron Man's J.A.R.V.I.S. Runs entirely on free/local tools — no paid APIs required.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/LLM-Ollama%20(llama3.2)-black?style=flat)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-1f6feb?style=flat)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

Jarvis understands both typed and spoken commands and can:

- 💬 **Chat naturally** — powered by a local LLM (Ollama, `llama3.2`), so conversations stay private and free
- 🎙️ **Listen and respond** via voice (speech-to-text + text-to-speech)
- 🌦️ **Check the weather** for any city (Open-Meteo API, no key needed)
- 📰 **Read news headlines** (BBC RSS feed)
- 📖 **Answer "who is / what is" questions** via live Wikipedia summaries
- 🕐 **Tell the time and date**
- 🗺️ **Open Google Maps** for a place or get directions
- 📸 **Take and save screenshots** on command
- 📊 **Report system info** — CPU, RAM, and battery status
- 😂 **Tell a joke**
- 🚀 **Launch apps and sites** — Chrome, VS Code, Notepad, YouTube, GitHub, Gmail, Reddit
- 🧠 **Know who its developer is** — a small personality touch, aware it was built by its creator

---

## 🛠️ Tech Stack

| Purpose | Library |
|---|---|
| LLM / chat | `ollama` (llama3.2, local) |
| GUI | `customtkinter` |
| Speech-to-text | `SpeechRecognition` + `PyAudio` |
| Text-to-speech | `pyttsx3` |
| Weather | Open-Meteo REST API |
| News | BBC RSS feed |
| Knowledge lookup | Wikipedia REST API |
| System info | `psutil` |
| Screenshots | `pyautogui` |
| Jokes | `pyjokes` |

---

## ⚙️ Setup

### Prerequisites
- Python 3.12+
- [Ollama](https://ollama.com) installed and running, with the `llama3.2` model pulled:
  ```bash
  ollama pull llama3.2
  ```

### Install

```bash
git clone https://github.com/<your-username>/jarvis.git
cd jarvis
python -m venv venv
venv\Scripts\activate        # Windows
pip install customtkinter ollama pyttsx3 SpeechRecognition pyaudio requests pyautogui psutil pyjokes
```

### Run

```bash
python jarvis_gui.py
```

Type a message, or hit **🎤 Talk** to speak to Jarvis directly.

> Edit the `DEVELOPER_NAME` and `DEFAULT_CITY` constants at the top of `jarvis_gui.py` to personalize it.

---

## 🐞 Notable Debugging & Fixes

Building this surfaced some real Windows audio quirks worth documenting:

- **WASAPI host API detection** — `PyAudio` needed explicit WASAPI host lookup to correctly find the default input device and its native sample rate on Windows with Realtek drivers, instead of assuming device index 0.
- **pyttsx3 engine reuse bug** — reinitializing the TTS engine (`pyttsx3.init()`) fresh on every `speak()` call avoided a bug where the engine would silently stop working after the first few calls.
- **Ollama PATH issues** — Ollama needed to be running as a background service and accessible on PATH before the Python client could connect; connection failures are now caught with a friendly fallback message.

Included test scripts (`test_wasapi.py`, `test_all_devices.py`, `test_mic.py`, `test_pyaudio.py`, `test_stream.py`, `test_record_and_save.py`) were used along the way to isolate and confirm the correct working microphone and sample rate.

---

## 📁 Project Structure

```
jarvis/
├── jarvis_gui.py          # main application
├── test_wasapi.py         # WASAPI host API diagnostics
├── test_all_devices.py    # scan all input-capable devices
├── test_mic.py            # basic mic + recognition test
├── test_pyaudio.py        # list all PyAudio devices
├── test_stream.py         # raw stream open/read test
├── test_record_and_save.py# record + save + transcribe test
└── README.md
```

---

## 🔭 Roadmap / Ideas

- [ ] Wake-word activation ("Hey Jarvis")
- [ ] Persistent conversation memory across sessions
- [ ] Package as a standalone `.exe` for easier distribution
- [ ] Add more skills (reminders, calendar, smart home)

---

## 📄 License

MIT — feel free to fork and build on it.
