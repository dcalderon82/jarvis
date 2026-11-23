#!/bin/sh
# Puerta de entrada del contenedor.
# Un disco persistente suele montarse con dueño "root". Si arrancamos como root, le damos la carpeta de datos
# a "jarvis" y bajamos los privilegios: el servidor nunca corre como administrador.
set -e
if [ "$(id -u)" = "0" ]; then
  mkdir -p "$JARVIS_DATA_DIR"
  chown -R jarvis:jarvis "$JARVIS_DATA_DIR"
  exec setpriv --reuid="$(id -u jarvis)" --regid="$(id -g jarvis)" --init-groups "$@"
fi
exec "$@"
