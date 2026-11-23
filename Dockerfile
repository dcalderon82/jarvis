# Jarvis web: la página de chat + el cerebro, listo para correr en cualquier hosting que acepte Docker.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    JARVIS_DATA_DIR=/data \
    JARVIS_BRAIN=claude \
    JARVIS_TRUST_PROXY=1 \
    JARVIS_TZ=America/Argentina/Buenos_Aires

# tzdata: para que la hora y los recordatorios usen la zona horaria de Argentina y no la del servidor (UTC).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 jarvis \
    && mkdir -p /data && chown jarvis:jarvis /data

WORKDIR /app

COPY requirements-web.txt .
RUN pip install -r requirements-web.txt

# Solo se copian estos archivos (lista blanca). El perfil, las notas, la memoria y las claves
# nunca entran en la imagen: se entregan por variables de entorno y por el disco /data.
COPY jarvis_core.py jarvis_claude.py jarvis_web.py wsgi.py perfil.ejemplo.json entrypoint.sh ./
COPY web ./web
RUN chmod 0755 /app/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8000'), timeout=3)"

# Un solo proceso con varios hilos: el estado de Jarvis vive en memoria. El cuerpo de un pedido se limita a 16 KB.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sh", "-c", "exec waitress-serve --host=0.0.0.0 --port=${PORT} --threads=4 --max-request-body-size=16384 --channel-timeout=75 --ident=jarvis wsgi:application"]
