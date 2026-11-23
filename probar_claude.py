"""Prueba tu clave de la API de Claude con UN pedido chiquito (cuesta una fracción de centavo).

En PowerShell:
    $env:ANTHROPIC_API_KEY = "tu-clave"     # solo vale para esta ventana; no se guarda en ningún archivo
    python probar_claude.py

Usa exactamente el mismo camino que la versión web (jarvis_claude.py), así que si acá anda, allá también.
La clave nunca se muestra ni se guarda.
"""
import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("Falta la variable ANTHROPIC_API_KEY.")
    print('En PowerShell:  $env:ANTHROPIC_API_KEY = "tu-clave"   y después   python probar_claude.py')
    sys.exit(1)

import jarvis_claude

chat = jarvis_claude.make_chat()
conversation = [
    {"role": "system", "content": "Sos Jarvis, un asistente argentino, informal, que contesta corto."},
    {"role": "user", "content": "Decime hola en una sola frase, en voseo."},
]
print(f"Probando con el modelo {chat.model}...")
try:
    reply = chat(conversation)
except jarvis_claude.LLMError as error:
    print("FALLÓ:", error.user_message)
    print("Detalle técnico:", error)
    sys.exit(2)

info = chat.last
print("OK. Jarvis contestó:", reply)
print(f"Modelo que respondió: {info['model']} | tokens de entrada: {info['input_tokens']} | de salida: {info['output_tokens']}")
