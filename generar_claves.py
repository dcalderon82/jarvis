"""Ayuda para el despliegue: genera valores seguros y arma el perfil en el formato que pide el hosting.

Uso (en tu PC):
    python generar_claves.py

Imprime en esta ventana, para que los copies al panel del hosting:
  - una contraseña de entrada al azar (podés usar otra, pero que sea larga y única),
  - el perfil en JSON de una sola línea (sale de tu perfil.json; es lo que va en JARVIS_PROFILE).

No guarda nada en ningún archivo y no envía nada a ningún lado. La clave de la API de Claude NO la genera:
esa se crea en la consola de Anthropic.
"""
import json
import os
import secrets

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("=== JARVIS_PASSWORD (contraseña de entrada; guardala en tu gestor de contraseñas) ===")
print(secrets.token_urlsafe(18))
print()

profile_path = os.path.join(BASE_DIR, "perfil.json")
print("=== JARVIS_PROFILE (tu perfil, en una línea) ===")
try:
    with open(profile_path, encoding="utf-8") as f:
        profile = json.load(f)
    if not isinstance(profile, dict):
        raise ValueError("perfil.json debe ser un objeto")
    # El modelo de Ollama no se usa online (allá piensa Claude): se saca para no confundir.
    profile.pop("modelo", None)
    print(json.dumps(profile, ensure_ascii=False, separators=(",", ":")))
except FileNotFoundError:
    print("No encontré perfil.json. Copiá perfil.ejemplo.json a perfil.json, completalo y volvé a correr esto.")
except ValueError as error:
    print(f"perfil.json no es un JSON válido: {error}")
print()
print("Recordá: ni la contraseña, ni el perfil, ni la clave de la API van en el código ni en GitHub: solo en el panel del hosting.")
