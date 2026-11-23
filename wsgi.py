"""Punto de entrada para el servidor de producción (waitress), dentro del contenedor.

En tu PC no hace falta: ahí alcanza con `python jarvis_web.py`.
Jarvis guarda su estado (conversación, notas, recordatorios) en memoria y en archivos, así que se corre UN solo
proceso con varios hilos (no varios procesos): eso es lo que hace `waitress-serve` en el Dockerfile.
"""
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

from jarvis_web import create_app  # noqa: E402  (el registro se configura antes para ver los avisos del arranque)

application = create_app()
logging.getLogger("jarvis").info("Cerebro: %s", application.config["BRAIN"])
