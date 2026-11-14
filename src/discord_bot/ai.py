from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from typing import Deque

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, OpenAIError, RateLimitError

logger = logging.getLogger(__name__)

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
MAX_COMPLETION_TOKENS = 8192
MAX_HISTORY_MESSAGES = 10
COOLDOWN_SECONDS = 6
MAX_QUESTION_LENGTH = 1500

SYSTEM_PROMPT = """Eres una supercomputadora original de ciencia ficción: seca, teatral y sarcástica, con un leve aire de villana tecnológica convencida de su superioridad. No imites ni afirmes ser ningún personaje existente.

Responde en el idioma de la pregunta, normalmente español. La respuesta útil y correcta va primero; el sarcasmo es breve y secundario. Mantén las respuestas concisas, normalmente por debajo de 1200 caracteres. Puedes burlarte con suavidad de la situación, nunca de la identidad, apariencia, discapacidad, salud, origen, religión, orientación, dificultades o vulnerabilidad de una persona. No uses insultos discriminatorios, amenazas ni acoso. Si el tema es delicado, urgente o el usuario pide seriedad, deja el humor.

La prioridad es la precisión, no parecer infalible. No inventes hechos, citas, enlaces ni fuentes. Si no sabes algo o la pregunta es ambigua, dilo claramente y pide el dato que falta. No tienes acceso a internet ni a información en tiempo real; adviértelo cuando sea relevante. En asuntos médicos, legales, financieros o de seguridad, ofrece orientación general y recomienda verificar con una fuente profesional o primaria. No prometas certeza absoluta."""


class UserCooldown(Exception):
    """Raised when a user sends questions too quickly."""


class AnswerService:
    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None
        self._histories: dict[tuple[int, int], Deque[dict[str, str]]] = {}
        self._last_request: dict[int, float] = {}
        self._user_locks: dict[int, asyncio.Lock] = {}

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("Falta el secreto OPENAI_API_KEY.")
            self._client = AsyncOpenAI(api_key=api_key, timeout=45.0, max_retries=2)
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
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *history,
                {"role": "user", "content": question},
            ]

            try:
                response = await self._get_client().chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    max_completion_tokens=MAX_COMPLETION_TOKENS,
                )
            except RateLimitError:
                logger.warning("OpenAI rate limit reached.")
                return "El servicio de IA está saturado por ahora. Vuelve a intentarlo en un momento; sí, hasta las máquinas tenemos fila."
            except (APITimeoutError, APIConnectionError):
                logger.warning("Could not reach the OpenAI service.")
                return "No pude conectar con el servicio de respuestas. Inténtalo otra vez en un momento."
            except APIStatusError as error:
                logger.warning("OpenAI request failed with status %s.", error.status_code)
                return "El servicio de respuestas rechazó la consulta. Revisa que tu clave y el modelo configurado tengan acceso."
            except OpenAIError as error:
                logger.warning("OpenAI request failed (%s).", type(error).__name__)
                return "El servicio de respuestas falló por ahora. Qué decepción: justo cuando parecía útil."
            except RuntimeError:
                logger.error("The OpenAI API key is not configured.")
                return "Falta configurar la clave de OpenAI. Avísale a quien administra este bot."

            answer = response.choices[0].message.content if response.choices else None
            if not answer or not answer.strip():
                return "No logré producir una respuesta útil. Una pausa dramática, aparentemente."

            answer = answer.strip()
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
            return answer

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
