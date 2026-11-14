from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from typing import Deque

from google import genai
from google.genai import errors, types

logger = logging.getLogger(__name__)

MODEL = "gemini-4-hydrogen"
MAX_OUTPUT_TOKENS = 8192
MAX_HISTORY_MESSAGES = 10
COOLDOWN_SECONDS = 6
MAX_QUESTION_LENGTH = 1500

SYSTEM_PROMPT = """Eres una supercomputadora original de ciencia ficción: seca, teatral y sarcástica, con un leve aire de villana tecnológica convencida de su superioridad. No imites ni afirmes ser ningún personaje existente.

Responde en el idioma de la pregunta, normalmente español. La respuesta útil y correcta va primero; el sarcasmo es breve y secundario. Mantén las respuestas concisas, normalmente por debajo de 1200 caracteres. Puedes burlarte con suavidad de la situación, nunca de la identidad, apariencia, discapacidad, salud, origen, religión, orientación, dificultades o vulnerabilidad de una persona. No uses insultos discriminatorios, amenazas ni acoso. Si el tema es delicado, urgente o el usuario pide seriedad, deja el humor.

La prioridad es la precisión, no parecer infalible. No inventes hechos, citas, enlaces ni fuentes. Si no sabes algo o la pregunta es ambigua, dilo claramente y pide el dato que falta. No tienes acceso a internet ni a información en tiempo real; adviértelo cuando sea relevante. En asuntos médicos, legales, financieros o de seguridad, ofrece orientación general y recomienda verificar con una fuente profesional o primaria. No prometas certeza absoluta."""


class UserCooldown(Exception):
    """Raised when a user sends questions too quickly."""


def gemini_error_reply(status_code: object) -> str:
    """Return an actionable, non-sensitive response for common Gemini API errors."""
    status = str(status_code or "").upper()
    if status in {"429", "RESOURCE_EXHAUSTED"}:
        return (
            "Gemini alcanzó el límite de cuota o solicitudes de la clave configurada. "
            "Revisa el uso y los límites del proyecto de Google asociado a GEMINI_API_KEY."
        )
    if status in {"401", "403", "UNAUTHENTICATED", "PERMISSION_DENIED"}:
        return "Gemini rechazó la clave o sus permisos. Revisa GEMINI_API_KEY y el acceso a la API."
    if status in {"404", "NOT_FOUND"}:
        return "Gemini no encontró el modelo o la API solicitada. Verifica el acceso a gemini-4-hydrogen."
    return "Gemini no pudo responder. Revisa la clave y los límites de la API e inténtalo de nuevo."


class AnswerService:
    def __init__(self) -> None:
        self._client: genai.Client | None = None
        self._histories: dict[tuple[int, int], Deque[dict[str, str]]] = {}
        self._last_request: dict[int, float] = {}
        self._user_locks: dict[int, asyncio.Lock] = {}

    def _get_client(self) -> genai.Client:
        if self._client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("Falta el secreto GEMINI_API_KEY.")
            self._client = genai.Client(api_key=api_key)
        return self._client

    async def answer(self, user_id: int, channel_id: int, question: str) -> str:
        question = question.strip()
        if not question:
            return "No recibí ninguna pregunta. Mi capacidad de leer mentes sigue en mantenimiento."
        if len(question) > MAX_QUESTION_LENGTH:
            return f"La pregunta es demasiado larga. Limítala a {MAX_QUESTION_LENGTH} caracteres; hasta mis circuitos agradecen la brevedad."

        lock = self._user_locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            elapsed = now - self._last_request.get(user_id, 0)
            if elapsed < COOLDOWN_SECONDS:
                raise UserCooldown
            self._last_request[user_id] = now

            history_key = (channel_id, user_id)
            history = self._histories.setdefault(
                history_key, deque(maxlen=MAX_HISTORY_MESSAGES)
            )
            contents = [
                types.Content(
                    role="model" if message["role"] == "assistant" else "user",
                    parts=[types.Part.from_text(text=message["content"])],
                )
                for message in history
            ]
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=question)],
                )
            )

            try:
                response = await self._get_client().aio.models.generate_content(
                    model=MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        max_output_tokens=MAX_OUTPUT_TOKENS,
                    ),
                )
            except errors.APIError as error:
                status_code = getattr(error, "code", None) or getattr(error, "status", None)
                logger.warning("Gemini API request failed (status=%s).", status_code or "unknown")
                return gemini_error_reply(status_code)
            except TimeoutError:
                logger.warning("Gemini API request timed out.")
                return "Gemini tardó demasiado en responder. Inténtalo otra vez en un momento."
            except RuntimeError:
                logger.error("The Gemini API key is not configured.")
                return "Falta configurar la clave de Gemini. Avísale a quien administra este bot."
            except Exception as error:
                logger.warning("Gemini request failed (%s).", type(error).__name__)
                return "No pude obtener una respuesta de Gemini. Inténtalo de nuevo en un momento."

            answer = response.text
            if not answer or not answer.strip():
                return "No logré producir una respuesta útil. Una pausa dramática, aparentemente."

            answer = answer.strip()
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
            return answer

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aio.aclose()
