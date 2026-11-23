"""Conecta el cerebro de Jarvis (jarvis_core.py) con la API de Claude, usando el SDK oficial de Anthropic.

Lo usa la versión web. Se configura con variables de entorno (la clave NUNCA va en el repositorio):

  ANTHROPIC_API_KEY          clave de la API (obligatoria; se crea en la consola de Anthropic)
  JARVIS_CLAUDE_MODEL        modelo (por defecto claude-sonnet-5-5)
  JARVIS_CLAUDE_EFFORT       cuánto "piensa" antes de contestar: low | medium | high (por defecto low: es un chat)
  JARVIS_CLAUDE_MAX_TOKENS   tope de tokens por respuesta (por defecto 3000; las respuestas son cortas)
  JARVIS_CLAUDE_FALLBACKS    "1" (por defecto) activa el respaldo automático si un modelo se niega a responder

En los registros solo quedan el modelo, la cantidad de tokens y el id del pedido: ni la clave ni los mensajes.
"""
import logging
import os
import re

import anthropic

log = logging.getLogger("jarvis.claude")

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_EFFORT = "low"
DEFAULT_MAX_TOKENS = 3000
TIMEOUT_SECONDS = 45.0          # un celular no espera 10 minutos (el valor por defecto del SDK)
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Modelos que aceptan cada opción (Haiku 5.5 no tiene respaldo del lado del servidor).
MODELS_WITH_EFFORT = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"}
MODELS_WITH_FALLBACKS = {"claude-opus-5-5", "claude-sonnet-5-5"}


class LLMError(Exception):
    """Falla del modelo. `user_message` es lo que ve quien escribe; `detail` es solo para los registros."""

    def __init__(self, user_message, detail=""):
        super().__init__(detail or user_message)
        self.user_message = user_message


def split_conversation(conversation):
    """Separa el prompt del sistema de los turnos, con la forma que pide la API:
    sin mensajes vacíos, empezando por el usuario y terminando en un mensaje del usuario."""
    system = "\n\n".join(m["content"] for m in conversation if m["role"] == "system")
    turns = [
        {"role": m["role"], "content": m["content"]}
        for m in conversation
        if m["role"] in ("user", "assistant") and str(m["content"]).strip()
    ]
    while turns and turns[0]["role"] != "user":
        turns.pop(0)  # tras recortar el historial puede quedar una respuesta suelta al principio
    if not turns or turns[-1]["role"] != "user":
        raise LLMError("Algo salió mal armando la conversación. Probá de nuevo.", "la conversación no termina en un mensaje del usuario")
    return system, turns


def friendly_error(exc):
    """Traduce una falla de la API a un mensaje claro (en el tono de Jarvis) y un detalle para los registros."""
    if isinstance(exc, anthropic.AuthenticationError):
        return LLMError("Tengo un problema para entrar a mi cerebro: la clave de la API no anda. Hay que revisarla en el servidor.", "401")
    if isinstance(exc, anthropic.PermissionDeniedError):
        return LLMError("Mi clave de la API no tiene permiso para esto. Hay que revisarla en la consola de Anthropic.", "403")
    if isinstance(exc, anthropic.NotFoundError):
        return LLMError("El modelo configurado no existe. Hay que revisar JARVIS_CLAUDE_MODEL.", "404")
    if isinstance(exc, anthropic.RateLimitError):
        return LLMError("Estoy recibiendo demasiados pedidos. Esperá un ratito y probá de nuevo.", "429")
    if isinstance(exc, anthropic.BadRequestError):
        text = str(exc).lower()
        if "credit balance" in text or "credit" in text and "low" in text:
            return LLMError("Se acabó el crédito de la API. Hay que recargarlo en la consola de Anthropic.", "400 sin crédito")
        return LLMError("Algo salió mal con el pedido al modelo. Probá de nuevo.", "400")
    if isinstance(exc, (anthropic.APITimeoutError, anthropic.APIConnectionError)):
        return LLMError("No pude conectarme con mi cerebro. Probá de nuevo en un rato.", type(exc).__name__)
    if isinstance(exc, anthropic.APIStatusError):
        if exc.status_code >= 500:
            return LLMError("Mi cerebro está saturado en este momento. Probá de nuevo en un rato.", str(exc.status_code))
        return LLMError("Algo salió mal con el modelo. Probá de nuevo.", str(exc.status_code))
    return LLMError("Algo salió mal con mi cerebro. Probá de nuevo.", type(exc).__name__)


def extract_reply(response):
    """Saca el texto de la respuesta (ignora los bloques de razonamiento) y trata los casos raros."""
    if response.stop_reason == "refusal":
        raise LLMError("Eso no te lo puedo responder, boludo.", "refusal")
    if response.stop_reason == "model_context_window_exceeded":
        raise LLMError("La charla se hizo demasiado larga. Probá con 'borrá la memoria' para empezar de cero.", "contexto excedido")
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if not text:
        raise LLMError("No se me ocurrió qué responder. Probá de nuevo.", f"respuesta vacía (stop_reason={response.stop_reason})")
    return text


def make_chat(model=None, api_key=None, base_url=None, effort=None, max_tokens=None,
              fallbacks=None, max_retries=2, timeout=TIMEOUT_SECONDS):
    """Devuelve una función chat(conversation) -> texto, lista para enchufar en jarvis_core.LLM_CHAT."""
    model = model or os.environ.get("JARVIS_CLAUDE_MODEL") or DEFAULT_MODEL
    effort = effort or os.environ.get("JARVIS_CLAUDE_EFFORT") or DEFAULT_EFFORT
    max_tokens = int(max_tokens or os.environ.get("JARVIS_CLAUDE_MAX_TOKENS") or DEFAULT_MAX_TOKENS)
    if fallbacks is None:
        fallbacks = os.environ.get("JARVIS_CLAUDE_FALLBACKS", "1") != "0"
    state = {"fallbacks": bool(fallbacks) and model in MODELS_WITH_FALLBACKS}

    # El SDK toma la clave de ANTHROPIC_API_KEY y la URL de ANTHROPIC_BASE_URL si no se las pasamos.
    client = anthropic.Anthropic(api_key=api_key, base_url=base_url, max_retries=max_retries, timeout=timeout)

    def send(params):
        if state["fallbacks"]:
            return client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **params)
        return client.messages.create(**params)

    def chat(conversation):
        system, turns = split_conversation(conversation)
        params = {"model": model, "max_tokens": max_tokens, "system": system, "messages": turns}
        if model in MODELS_WITH_EFFORT and effort:
            params["output_config"] = {"effort": effort}
        try:
            try:
                response = send(params)
            except anthropic.BadRequestError as exc:
                # Si el rechazo es por el respaldo automático, se sigue sin él (y se deja de usar).
                if state["fallbacks"] and re.search(r"fallback|beta", str(exc), re.I):
                    log.warning("La API rechazó el respaldo automático; se desactiva y se reintenta sin él.")
                    state["fallbacks"] = False
                    response = send(params)
                else:
                    raise
        except LLMError:
            raise
        except anthropic.APIError as exc:
            problem = friendly_error(exc)
            log.error("Falla de la API de Claude: %s (id del pedido: %s)", problem, getattr(exc, "request_id", None))
            raise problem from exc

        usage = response.usage
        chat.last = {
            "model": response.model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "stop_reason": response.stop_reason,
            "request_id": getattr(response, "_request_id", None),
        }
        log.info("Claude ok: modelo=%s tokens entrada=%s salida=%s stop=%s id=%s", response.model,
                 usage.input_tokens, usage.output_tokens, response.stop_reason, chat.last["request_id"])
        return extract_reply(response)

    chat.last = None
    chat.model = model
    return chat
