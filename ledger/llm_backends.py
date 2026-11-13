"""Backends de LLM. CONJUNTO.

- Gemini (google-genai): salida estructurada nativa con `response_schema`.
- NVIDIA Nemotron (API compatible con OpenAI en build.nvidia.com): el esquema va en el prompt y la
  respuesta se limpia (bloques <think>, vallas ```json) antes de validarla con pydantic.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

from ledger.config import Settings


class LLMError(RuntimeError):
    pass


# --------------------------------------------------------------------------- Gemini


def gemini_client(settings: Settings) -> Any:
    if not settings.gemini_api_key:
        raise LLMError("Falta GEMINI_API_KEY. Copia .env.example a .env y rellénala.")
    from google import genai  # import diferido: los tests no necesitan el SDK

    return genai.Client(api_key=settings.gemini_api_key)


def gemini_generate(client: Any, model: str, system: str, user: str, schema: type[BaseModel] | None) -> str:
    from google.genai import types

    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0,
        response_mime_type="application/json" if schema else "text/plain",
        response_schema=schema,
    )
    response = client.models.generate_content(model=model, contents=user, config=config)
    if not response.text:
        raise LLMError(f"Respuesta vacía de {model}")
    return response.text


# --------------------------------------------------------------------------- NVIDIA Nemotron

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def nvidia_client(settings: Settings) -> Any:
    if not settings.nvidia_api_key:
        raise LLMError("Falta NVIDIA_API_KEY (build.nvidia.com). Cada persona usa su propia clave.")
    if not settings.nvidia_model:
        raise LLMError("Falta NVIDIA_MODEL: copia el ID exacto de Nemotron 3.5 Super VL desde build.nvidia.com.")
    from openai import OpenAI

    return OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)


def schema_instruction(schema: type[BaseModel]) -> str:
    return (
        "\n\nRespond ONLY with a JSON object, no prose and no markdown fences, "
        f"matching this JSON Schema:\n{json.dumps(schema.model_json_schema())}"
    )


def clean_json_text(raw: str) -> str:
    """Quita el razonamiento <think> y las vallas de código que Nemotron a veces añade."""
    text = _THINK_BLOCK.sub("", raw).strip()
    return _FENCE.sub("", text).strip()


def nvidia_generate(client: Any, model: str, system: str, user: str, schema: type[BaseModel] | None) -> str:
    system_prompt = system + (schema_instruction(schema) if schema else "")
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user}],
    )
    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise LLMError(f"Respuesta vacía de {model}")
    return clean_json_text(content) if schema else content
