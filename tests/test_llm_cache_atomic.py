"""La caché del LLM se escribe de forma atómica: con la Etapa 3 en paralelo, nadie lee un JSON a medio escribir."""

from __future__ import annotations

import pathlib
import threading
import time
from dataclasses import replace

from pydantic import BaseModel

from ledger import llm
from ledger.config import load_settings


class Answer(BaseModel):
    text: str


BIG = Answer(text="x" * 20_000).model_dump_json()


def test_readers_never_see_a_half_written_cache_file(tmp_path, monkeypatch):
    settings = replace(load_settings(), cache_dir=tmp_path, nvidia_for_all=False)
    monkeypatch.setattr(llm, "gemini_generate", lambda client, model, system, user, schema: BIG)

    real_write_text = pathlib.Path.write_text

    def slow_write_text(self, data, *args, **kwargs):
        # Simula un disco lento: primero media respuesta, luego la completa.
        real_write_text(self, data[: len(data) // 2], *args, **kwargs)
        time.sleep(0.3)
        return real_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", slow_write_text)

    errors: list[BaseException] = []

    def call() -> None:
        try:
            llm.complete("s", "same prompt", Answer, "pro", client=object(), settings=settings)
        except BaseException as exc:  # noqa: BLE001 - queremos ver cualquier fallo de lectura
            errors.append(exc)

    writer = threading.Thread(target=call)
    writer.start()
    time.sleep(0.1)  # el escritor ya ha dejado media respuesta en disco
    readers = [threading.Thread(target=call) for _ in range(5)]
    for t in readers:
        t.start()
    for t in (writer, *readers):
        t.join()

    assert errors == []
    assert not list(tmp_path.rglob("*.tmp"))  # no quedan temporales
