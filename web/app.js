(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const els = {
    login: $("login"), loginForm: $("login-form"), password: $("password"),
    loginButton: $("login-button"), loginError: $("login-error"),
    chat: $("chat"), messages: $("messages"), composer: $("composer"),
    text: $("text"), mic: $("mic"), send: $("send"),
    voiceToggle: $("voice-toggle"), logout: $("logout"),
  };

  const SPEECH_LANG = "es-AR";
  const VOICE_LANG_ORDER = ["es-AR", "es-MX", "es-US", "es-419", "es-ES"];
  const EVENTS_EVERY_MS = 8000;

  let authed = false;
  let busy = false;
  let voiceOn = readPref("voz", "1") === "1";
  let voices = [];
  let speechUnlocked = false;
  let recognition = null;
  let listening = false;
  let eventsTimer = null;

  // ------------------------------------------------------------------ utilidades
  function readPref(key, fallback) {
    try { return localStorage.getItem("jarvis_" + key) ?? fallback; } catch { return fallback; }
  }
  function writePref(key, value) {
    try { localStorage.setItem("jarvis_" + key, value); } catch { /* modo privado: no pasa nada */ }
  }

  async function api(path, body) {
    const options = body === undefined
      ? { method: "GET", credentials: "same-origin" }
      : {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-Requested-With": "jarvis" },
          body: JSON.stringify(body),
        };
    const response = await fetch(path, options);
    let data = {};
    try { data = await response.json(); } catch { /* respuesta sin JSON */ }
    return { status: response.status, ok: response.ok, data };
  }

  // Todo se escribe como texto (nunca como HTML); los links se arman a mano y solo si son http(s).
  function renderText(container, text) {
    const parts = String(text).split(/(https?:\/\/[^\s]+)/g);
    for (const part of parts) {
      if (/^https?:\/\//.test(part)) {
        try {
          const url = new URL(part);
          if (url.protocol === "http:" || url.protocol === "https:") {
            const link = document.createElement("a");
            link.href = url.href;
            link.textContent = part;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            container.appendChild(link);
            continue;
          }
        } catch { /* no es una URL válida: se muestra como texto */ }
      }
      container.appendChild(document.createTextNode(part));
    }
  }

  function addMessage(who, text, extraClass) {
    const node = document.createElement("div");
    node.className = "msg msg-" + who + (extraClass ? " " + extraClass : "");
    renderText(node, text);
    els.messages.appendChild(node);
    els.messages.scrollTop = els.messages.scrollHeight;
    return node;
  }

  // ------------------------------------------------------------------ pantallas
  function showLogin(message) {
    authed = false;
    stopEvents();
    stopListening();
    stopSpeaking();
    els.chat.hidden = true;
    els.login.hidden = false;
    els.loginError.textContent = message || "";
    els.password.value = "";
    els.password.focus();
  }

  function showChat(greeting) {
    authed = true;
    els.login.hidden = true;
    els.chat.hidden = false;
    els.messages.textContent = "";
    if (greeting) addMessage("jarvis", greeting);
    startEvents();
    els.text.focus();
  }

  // ------------------------------------------------------------------ voz de salida
  function loadVoices() {
    if (!("speechSynthesis" in window)) return;
    voices = window.speechSynthesis.getVoices();
  }
  if ("speechSynthesis" in window) {
    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);
  }

  function pickVoice() {
    for (const lang of VOICE_LANG_ORDER) {
      const found = voices.find((v) => v.lang.replace("_", "-").toLowerCase() === lang.toLowerCase());
      if (found) return found;
    }
    return voices.find((v) => v.lang.toLowerCase().startsWith("es")) || null;
  }

  // Safari en iPhone solo deja hablar después de un toque del usuario: se "desbloquea" con el primero.
  function unlockSpeech() {
    if (speechUnlocked || !("speechSynthesis" in window)) return;
    speechUnlocked = true;
    try { window.speechSynthesis.speak(new SpeechSynthesisUtterance("")); } catch { /* sin voz */ }
  }

  function stopSpeaking() {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  }

  function speak(text) {
    if (!voiceOn || !("speechSynthesis" in window)) return;
    const clean = String(text).replace(/https?:\/\/[^\s]+/g, "el link");
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = SPEECH_LANG;
    const voice = pickVoice();
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
  }

  function renderVoiceToggle() {
    els.voiceToggle.setAttribute("aria-pressed", String(voiceOn));
    els.voiceToggle.textContent = voiceOn ? "🔊" : "🔇";
  }

  // ------------------------------------------------------------------ voz de entrada
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    els.mic.title = "Tu navegador no reconoce voz: usá el micrófono del teclado";
  }

  function setListening(value) {
    listening = value;
    els.mic.classList.toggle("listening", value);
    els.mic.setAttribute("aria-label", value ? "Dejar de escuchar" : "Hablar");
  }

  function stopListening() {
    if (recognition) {
      try { recognition.abort(); } catch { /* ya estaba detenido */ }
      recognition = null;
    }
    setListening(false);
  }

  const MIC_ERRORS = {
    "not-allowed": "No tengo permiso para usar el micrófono. Habilitalo en los ajustes del navegador.",
    "service-not-allowed": "El dictado está desactivado. En el iPhone, activalo en Ajustes > General > Teclado > Activar dictado.",
    "audio-capture": "No encontré un micrófono.",
    "network": "No pude conectarme al servicio de voz.",
    "language-not-supported": "El reconocimiento de voz no soporta el idioma.",
  };

  function startListening() {
    if (!Recognition) {
      addMessage("sistema", "Este navegador no reconoce voz. Usá el micrófono del teclado para dictar.");
      return;
    }
    stopSpeaking();
    const session = new Recognition();
    recognition = session;
    session.lang = SPEECH_LANG;
    session.interimResults = true;
    session.continuous = false;
    session.maxAlternatives = 1;

    let finalText = "";
    let failed = false;

    session.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += piece; else interim += piece;
      }
      els.text.value = (finalText + interim).trim();
    };
    session.onerror = (event) => {
      failed = true;
      if (event.error !== "no-speech" && event.error !== "aborted") {
        addMessage("sistema", MIC_ERRORS[event.error] || "El micrófono falló (" + event.error + ").");
      } else if (event.error === "no-speech") {
        addMessage("sistema", "No te escuché nada, boludo. Probá de nuevo.");
      }
    };
    session.onend = () => {
      if (recognition === session) recognition = null;
      setListening(false);
      const heard = els.text.value.trim();
      if (!failed && heard) sendMessage(heard);
    };

    try {
      session.start();
      setListening(true);
    } catch {
      setListening(false);
      addMessage("sistema", "No pude empezar a escuchar. Probá de nuevo.");
    }
  }

  // ------------------------------------------------------------------ chat
  async function sendMessage(message) {
    const text = message.trim();
    if (!text || busy || !authed) return;
    unlockSpeech();
    busy = true;
    els.send.disabled = true;
    els.text.value = "";
    addMessage("yo", text);
    const thinking = addMessage("jarvis", "Pensando…", "msg-pensando");
    try {
      const result = await api("/api/chat", { message: text });
      thinking.remove();
      if (result.status === 401) {
        showLogin("Se cerró la sesión. Volvé a entrar.");
        return;
      }
      if (!result.ok) {
        addMessage("sistema", result.data.error || "Algo salió mal (" + result.status + ").");
        return;
      }
      addMessage("jarvis", result.data.reply);
      speak(result.data.reply);
    } catch {
      thinking.remove();
      addMessage("sistema", "No pude conectarme con Jarvis. Revisá tu internet y probá de nuevo.");
    } finally {
      busy = false;
      els.send.disabled = false;
    }
  }

  // ------------------------------------------------------------------ avisos (recordatorios)
  async function pullEvents() {
    if (!authed || document.visibilityState !== "visible") return;
    try {
      const result = await api("/api/events");
      if (result.status === 401) { showLogin("Se cerró la sesión. Volvé a entrar."); return; }
      for (const event of (result.data.events || [])) {
        addMessage("jarvis", event.texto);
        speak(event.texto);
      }
    } catch { /* sin conexión: se reintenta en el próximo ciclo */ }
  }
  function startEvents() {
    stopEvents();
    pullEvents();
    eventsTimer = setInterval(pullEvents, EVENTS_EVERY_MS);
  }
  function stopEvents() {
    if (eventsTimer) { clearInterval(eventsTimer); eventsTimer = null; }
  }
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") pullEvents(); });

  // ------------------------------------------------------------------ eventos de la interfaz
  els.loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    els.loginButton.disabled = true;
    els.loginError.textContent = "";
    try {
      const result = await api("/api/login", { password: els.password.value });
      if (result.ok) {
        showChat(result.data.greeting);
      } else {
        els.loginError.textContent = result.data.error || "No pude entrar.";
        els.password.select();
      }
    } catch {
      els.loginError.textContent = "No pude conectarme. Revisá tu internet.";
    } finally {
      els.loginButton.disabled = false;
    }
  });

  els.composer.addEventListener("submit", (event) => {
    event.preventDefault();
    sendMessage(els.text.value);
  });

  els.mic.addEventListener("click", () => {
    unlockSpeech();
    if (listening) { if (recognition) recognition.stop(); } else { startListening(); }
  });

  els.voiceToggle.addEventListener("click", () => {
    voiceOn = !voiceOn;
    writePref("voz", voiceOn ? "1" : "0");
    renderVoiceToggle();
    if (!voiceOn) stopSpeaking(); else unlockSpeech();
  });

  els.logout.addEventListener("click", async () => {
    try { await api("/api/logout", {}); } catch { /* igual se vuelve a la pantalla de entrada */ }
    showLogin("");
  });

  // ------------------------------------------------------------------ arranque
  renderVoiceToggle();
  (async () => {
    try {
      const result = await api("/api/state");
      if (result.data.auth) showChat(result.data.greeting); else showLogin("");
    } catch {
      showLogin("No pude conectarme con Jarvis.");
    }
  })();
})();
