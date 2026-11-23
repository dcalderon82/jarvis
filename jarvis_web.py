"""Jarvis web: el mismo cerebro (jarvis_core.py) pero con una página de chat para usar desde el celular.

Configuración por variables de entorno (nada de esto se guarda en el repositorio):

  JARVIS_PASSWORD       contraseña para entrar (obligatoria, mínimo 10 caracteres)
  JARVIS_SECRET         clave para firmar la sesión (recomendada; si falta se genera una al arrancar)
  JARVIS_COOKIE_SECURE  "1" (por defecto) exige HTTPS para la cookie; usar "0" solo para probar en http://localhost
  JARVIS_TRUST_PROXY    "1" si está detrás de un proxy de hosting (usa la IP real en el límite de intentos)
  JARVIS_TZ             zona horaria del servidor (por defecto America/Argentina/Buenos_Aires)
  JARVIS_DAILY_LIMIT    tope de mensajes por día (por defecto 300), para no gastar de más cuando haya una API paga

Para probarlo en tu PC:
  set JARVIS_PASSWORD=una-clave-larga-y-unica
  set JARVIS_COOKIE_SECURE=0
  python jarvis_web.py
"""
import os
import time
import hmac
import secrets
import threading
import collections

# La zona horaria se fija antes de usar fechas: un servidor suele estar en UTC.
if hasattr(time, "tzset"):
    os.environ["TZ"] = os.environ.get("JARVIS_TZ", "America/Argentina/Buenos_Aires")
    time.tzset()

from flask import Flask, jsonify, request, session, send_from_directory

import jarvis_core as core

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
MIN_PASSWORD_LENGTH = 10
MAX_MESSAGE_LENGTH = 500          # los pedidos por voz son cortos; esto además limita el costo por mensaje
MAX_CONTENT_LENGTH = 8 * 1024     # tamaño máximo de cualquier pedido


class LoginLimiter:
    """Frena los intentos de adivinar la contraseña: 5 fallos seguidos bloquean esa IP por 15 minutos."""
    MAX_FAILURES = 5
    LOCK_SECONDS = 15 * 60

    def __init__(self):
        self.failures = {}      # ip -> (cantidad, bloqueado_hasta)
        self.lock = threading.Lock()

    def locked_for(self, ip, now):
        with self.lock:
            count, until = self.failures.get(ip, (0, 0))
            return max(0, int(until - now))

    def fail(self, ip, now):
        with self.lock:
            count, until = self.failures.get(ip, (0, 0))
            if until and until <= now:
                count = 0
            count += 1
            until = now + self.LOCK_SECONDS if count >= self.MAX_FAILURES else 0
            self.failures[ip] = (count, until)

    def success(self, ip):
        with self.lock:
            self.failures.pop(ip, None)


class UsageLimiter:
    """Tope de mensajes: por minuto (para sesiones que se pasan de rosca) y por día (para cuidar el gasto)."""

    def __init__(self, per_minute, per_day):
        self.per_minute, self.per_day = per_minute, per_day
        self.recent = collections.deque()
        self.day, self.day_count = None, 0
        self.lock = threading.Lock()

    def allow(self, now, today):
        with self.lock:
            if today != self.day:
                self.day, self.day_count = today, 0
            while self.recent and now - self.recent[0] > 60:
                self.recent.popleft()
            if len(self.recent) >= self.per_minute:
                return "Muy rápido, boludo. Esperá un ratito y probá de nuevo."
            if self.day_count >= self.per_day:
                return "Por hoy ya fue, llegamos al tope de mensajes. Mañana seguimos."
            self.recent.append(now)
            self.day_count += 1
            return None


def create_app(password=None, secret=None, cookie_secure=None, daily_limit=None, restore=True):
    password = password if password is not None else os.environ.get("JARVIS_PASSWORD", "")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(
            f"Definí la variable JARVIS_PASSWORD con una contraseña de al menos {MIN_PASSWORD_LENGTH} caracteres."
        )
    secret = secret or os.environ.get("JARVIS_SECRET") or secrets.token_hex(32)
    if cookie_secure is None:
        cookie_secure = os.environ.get("JARVIS_COOKIE_SECURE", "1") != "0"
    if daily_limit is None:
        daily_limit = int(os.environ.get("JARVIS_DAILY_LIMIT", "300"))

    app = Flask(__name__, static_folder=None)
    app.config.update(
        SECRET_KEY=secret,
        MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
        SESSION_COOKIE_NAME="jarvis_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
        PERMANENT_SESSION_LIFETIME=30 * 24 * 3600,
    )
    if os.environ.get("JARVIS_TRUST_PROXY") == "1":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    login_limiter = LoginLimiter()
    usage = UsageLimiter(per_minute=20, per_day=daily_limit)
    chat_lock = threading.Lock()
    events = collections.deque(maxlen=50)   # avisos de recordatorios pendientes de mostrar en la página

    # --- el cerebro, sin ganchos de escritorio: los links vuelven en la respuesta ---
    # (jarvis_core guarda un estado único por proceso: se usa una sola aplicación por proceso)
    core.URL_OPENER = None
    core.DESKTOP_HANDLER = None
    core.DESKTOP_LATE_HANDLER = None
    core.NOTIFIER = lambda msg: events.append({"texto": msg})
    if restore:
        for due, texto in core.restore_reminders():
            events.append({
                "texto": f"Ey {core.NICKNAME}, mientras yo estaba apagado se te pasó un recordatorio, "
                         f"{core.describe_due(due)}: {texto}."
            })

    # ------------------------------------------------------------------ seguridad común
    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
            "img-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
        if cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def client_ip():
        return request.remote_addr or "desconocida"

    def check_request_origin():
        """Contra pedidos falsos desde otras páginas: exige JSON, una cabecera propia y el mismo origen."""
        if request.headers.get("X-Requested-With") != "jarvis":
            return "Pedido no válido."
        if not request.is_json:
            return "Pedido no válido."
        origin = request.headers.get("Origin")
        if origin and origin.split("://", 1)[-1] != request.host:
            return "Origen no permitido."
        return None

    def fail(message, status):
        return jsonify({"error": message}), status

    @app.before_request
    def guard_posts():
        if request.method == "POST":
            problem = check_request_origin()
            if problem:
                return fail(problem, 403)

    def authed():
        return session.get("auth") is True

    # ------------------------------------------------------------------ páginas (solo archivos conocidos)
    def page(filename, mimetype=None):
        return send_from_directory(WEB_DIR, filename, mimetype=mimetype, max_age=0)

    @app.get("/")
    def index():
        return page("index.html")

    @app.get("/app.js")
    def app_js():
        return page("app.js", "text/javascript")

    @app.get("/style.css")
    def style_css():
        return page("style.css", "text/css")

    @app.get("/manifest.webmanifest")
    def manifest():
        return page("manifest.webmanifest", "application/manifest+json")

    # ------------------------------------------------------------------ API
    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/api/state")
    def state():
        if not authed():
            return jsonify({"auth": False})
        return jsonify({"auth": True, "greeting": f"Ey {core.NICKNAME}, acá estoy. ¿Qué hacemos hoy?"})

    @app.post("/api/login")
    def login():
        ip, now = client_ip(), time.time()
        wait = login_limiter.locked_for(ip, now)
        if wait:
            return fail(f"Demasiados intentos. Probá de nuevo en {wait // 60 + 1} minutos.", 429)
        data = request.get_json(silent=True) or {}
        given = data.get("password")
        if not isinstance(given, str) or not hmac.compare_digest(given.encode("utf-8"), password.encode("utf-8")):
            login_limiter.fail(ip, now)
            return fail("Contraseña incorrecta.", 401)
        login_limiter.success(ip)
        session.clear()
        session.permanent = True
        session["auth"] = True
        return jsonify({"ok": True, "greeting": f"Ey {core.NICKNAME}, acá estoy. ¿Qué hacemos hoy?"})

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.post("/api/chat")
    def chat():
        if not authed():
            return fail("Tenés que iniciar sesión.", 401)
        data = request.get_json(silent=True) or {}
        message = data.get("message")
        if not isinstance(message, str) or not message.strip():
            return fail("Escribí algo.", 400)
        message = message.strip()
        if len(message) > MAX_MESSAGE_LENGTH:
            return fail(f"Mensaje demasiado largo (máximo {MAX_MESSAGE_LENGTH} caracteres).", 413)
        limited = usage.allow(time.time(), time.strftime("%Y-%m-%d"))
        if limited:
            return fail(limited, 429)
        with chat_lock:
            reply = core.get_reply(message)
        return jsonify({"reply": reply})

    @app.get("/api/events")
    def pull_events():
        if not authed():
            return fail("Tenés que iniciar sesión.", 401)
        pending = []
        while events:
            pending.append(events.popleft())
        return jsonify({"events": pending})

    return app


if __name__ == "__main__":
    application = create_app()
    port = int(os.environ.get("PORT", "8000"))
    # En la PC se escucha solo en localhost; en un hosting lo maneja el servidor de producción (gunicorn).
    application.run(host=os.environ.get("JARVIS_HOST", "127.0.0.1"), port=port, threaded=True)
