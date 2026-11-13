"""Typed decision boundary for local heuristics and optional TypeSafe Jev.

The pipeline sends a list of :class:`DecisionInput` values to ``decidir``.  Each
input has a finite set of labels and returns one ``(label, probability)`` pair.
Results are cached by the complete request in SQLite so repeated evaluation
runs do not make another external call.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
import warnings
from functools import cached_property
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from dotenv import load_dotenv


DEFAULT_DB = Path(".cache/decisores.sqlite3")
DEFAULT_API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
DEFAULT_USD_PER_MILLION_INPUT = 0.042
CACHE_SCHEMA_VERSION = 3
PARAMS = {
    "max_workers": 4,
    "retries": 2,
    "timeout_s": 15.0,
    "nli_model": None,
    "nli_revision": None,
    "nli_max_por_lote": 256,
}


@dataclass(frozen=True)
class DecisionInput:
    """One bounded decision request.

    ``kind`` controls the local fallback.  ``stance`` recognizes ``apoya`` and
    ``rechaza``.  ``choice`` selects among arbitrary ``labels``.  The labels
    are part of the cache key because Jev sees them as the criteria.
    """

    text: str
    labels: tuple[str, ...] = ("apoya", "rechaza")
    kind: str = "choice"
    context: Mapping[str, Any] = field(default_factory=dict)



@dataclass
class DecisionStats:
    """Run accounting.

    ``api_fresh`` counts successful external calls. ``logical_ia`` counts
    requested decisions whose result came from Jev, including cache hits and
    duplicate inputs resolved by one call. ``usd_ia`` covers fresh calls only.
    """
    requested: int = 0
    cache_hits: int = 0
    local_decisions: int = 0
    api_fresh: int = 0
    logical_ia: int = 0
    failed_api_decisions: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    api_seconds: float = 0.0
    usd_ia: float = 0.0

    @property
    def fresh_decisions(self) -> int:
        return self.api_fresh + self.local_decisions

    @property
    def fraccion_ia(self) -> float:
        return self.logical_ia / self.requested if self.requested else 0.0

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({"fresh_decisions": self.fresh_decisions, "fraccion_ia": self.fraccion_ia})
        return result


class DecisionEngine:
    """Persistent, deterministic decision service used by the pipeline."""

    def __init__(
        self,
        mode: str = "local",
        cache_path: str | Path = DEFAULT_DB,
        api_key: str | None = None,
        api_url: str = DEFAULT_API_URL,
        model: str | None = None,
        retries: int | None = None,
        timeout_s: float | None = None,
        max_workers: int | None = None,
    ) -> None:
        if mode not in {"local", "jev"}:
            raise ValueError("mode debe ser 'local' o 'jev'")
        if mode == "jev":
            load_dotenv(Path(__file__).resolve().with_name(".env"), override=False, interpolate=False)
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY", "")
        self.mode = "jev" if mode == "jev" and self.api_key else "local"
        if mode == "jev" and not self.api_key:
            warnings.warn("DECISOR=jev solicitado sin TYPESAFE_API_KEY. Se usa el decisor local.", RuntimeWarning, stacklevel=2)
        self.api_url = api_url
        self.model = model or os.getenv("TYPESAFE_MODEL", DEFAULT_MODEL)
        self.retries = max(0, PARAMS["retries"] if retries is None else retries)
        self.timeout_s = float(os.getenv("TYPESAFE_TIMEOUT_S", PARAMS["timeout_s"])) if timeout_s is None else timeout_s
        self.max_workers = max(1, int(os.getenv("TYPESAFE_MAX_WORKERS", PARAMS["max_workers"])) if max_workers is None else max_workers)
        self.stats = DecisionStats()
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.cache_path)
        self._db.execute("CREATE TABLE IF NOT EXISTS decisions (cache_key TEXT PRIMARY KEY, label TEXT NOT NULL, probability REAL NOT NULL, source TEXT NOT NULL, created_at REAL NOT NULL)")
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "DecisionEngine":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _key(self, item: DecisionInput) -> str:
        payload = {"schema": CACHE_SCHEMA_VERSION, "mode": self.mode, "model": self.model, "url": self.api_url, "text": item.text, "labels": item.labels, "kind": item.kind, "context": item.context}
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

    def decide(self, lote: Iterable[DecisionInput]) -> list[tuple[str, float]]:
        """Return one deterministic label and probability for each input."""
        items = list(lote)
        self.stats.requested += len(items)
        results: list[tuple[str, float] | None] = [None] * len(items)
        pending: dict[str, DecisionInput] = {}
        positions: dict[str, list[int]] = {}
        for index, item in enumerate(items):
            key = self._key(item)
            row = self._db.execute("SELECT label, probability, source FROM decisions WHERE cache_key = ?", (key,)).fetchone()
            if row:
                self.stats.cache_hits += 1
                results[index] = (str(row[0]), float(row[1]))
                if row[2] == "jev":
                    self.stats.logical_ia += 1
            else:
                pending[key] = item
                positions.setdefault(key, []).append(index)

        def resolve(entry: tuple[str, DecisionInput]) -> tuple[str, tuple[str, float], str, dict[str, Any]]:
            key, item = entry
            if self.mode == "jev":
                inicio = time.perf_counter()
                try:
                    result, telemetry = self._jev(item)
                    return key, result, "jev", telemetry
                except (OSError, RuntimeError, ValueError, TypeError, KeyError):
                    return key, self._local(item), "local", {
                        "failed_api": 1, "api_seconds": time.perf_counter() - inicio,
                    }
            return key, self._local(item), "local", {}

        entries = list(pending.items())
        resolved = list(map(resolve, entries)) if self.mode == "local" else []
        if self.mode == "jev" and entries:
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(entries))) as pool:
                resolved = list(pool.map(resolve, entries))
        for key, result, source, telemetry in resolved:
            self.stats.local_decisions += source == "local"
            self.stats.api_fresh += source == "jev"
            self.stats.logical_ia += len(positions[key]) if source == "jev" else 0
            self.stats.failed_api_decisions += int(telemetry.get("failed_api", 0))
            self.stats.input_tokens += int(telemetry.get("input_tokens", 0))
            self.stats.output_tokens += int(telemetry.get("output_tokens", 0))
            self.stats.api_seconds += float(telemetry.get("api_seconds", 0.0))
            for index in positions[key]:
                results[index] = result
            # A local fallback after a Jev failure is deliberately not cached
            # under the Jev key. The next run can retry the external decision.
            if not telemetry.get("failed_api"):
                self._db.execute(
                    "INSERT OR REPLACE INTO decisions(cache_key, label, probability, source, created_at) VALUES (?, ?, ?, ?, ?)",
                    (key, result[0], result[1], source, time.time()),
                )
        self._db.commit()
        self.stats.usd_ia = self.stats.input_tokens * float(os.getenv("TYPESAFE_USD_PER_MILLION_INPUT", DEFAULT_USD_PER_MILLION_INPUT)) / 1_000_000
        return [result for result in results if result is not None]

    def decide_local(self, lote: Iterable[DecisionInput]) -> list[tuple[str, float]]:
        items = list(lote)
        resultados = [self._local(item) for item in items]
        self.stats.local_decisions += len(items)
        if PARAMS["nli_model"]:
            elegidos = [i for i, item in enumerate(items) if item.kind in {"stance", "claim"}]
            elegidos = elegidos[:PARAMS["nli_max_por_lote"]]
            for i in elegidos:
                item = items[i]
                if item.kind == "stance":
                    texto = f"Afirmación: {item.context.get('afirmacion', '')}\nComentario: {item.text}"
                    opciones = {"apoya": "respalda la afirmación", "rechaza": "refuta la afirmación"}
                    plantilla = "El comentario {}."
                else:
                    texto = item.text
                    opciones = {"afirmacion": "una afirmación concreta", "reaccion": "una reacción sin afirmación"}
                    plantilla = "El texto expresa {}."
                inverso = {valor: clave for clave, valor in opciones.items()}
                respuesta = self._nli(texto, list(inverso), hypothesis_template=plantilla)
                resultados[i] = inverso[respuesta["labels"][0]], float(respuesta["scores"][0])
        return resultados

    @cached_property
    def _nli(self):
        from transformers import pipeline

        return pipeline("zero-shot-classification", model=PARAMS["nli_model"],
                        revision=PARAMS["nli_revision"], device=-1)

    def _local(self, item: DecisionInput) -> tuple[str, float]:
        labels = item.labels or ("ninguna",)
        text = _normalize(item.text)
        kind = item.kind.lower()
        if kind in {"stance", "postura"} and {"apoya", "rechaza"} <= set(labels):
            reject = sum(marker in text for marker in _REJECT_MARKERS)
            support = sum(marker in text for marker in _SUPPORT_MARKERS)
            if reject > support:
                return "rechaza", min(0.99, 0.62 + 0.08 * reject)
            return "apoya", min(0.99, 0.58 + 0.08 * support)
        if kind in {"claim", "afirmacion"}:
            reaction = sum(marker in text for marker in ("jaja", "qué vergüenza", "gracias", "tal cual", "exacto"))
            labels = tuple(label for label in labels if label in {"afirmacion", "reaccion", "ninguna"}) or labels
            if "reaccion" in labels and reaction and len(text.split()) <= 6:
                return "reaccion", 0.8
            if "afirmacion" in labels:
                return "afirmacion", 0.68 if len(text.split()) >= 5 else 0.42
        if kind in {"relation", "relacion"}:
            contradiction = any(marker in text for marker in _REJECT_MARKERS)
            accompaniment = any(marker in text for marker in _SUPPORT_MARKERS)
            if contradiction and "contradice" in labels:
                return "contradice", 0.84
            if accompaniment and "acompaña" in labels:
                return "acompaña", 0.82
            if "independiente" in labels:
                return "independiente", 0.55
        scores = {label: 0.0 for label in labels}
        for label in labels:
            tokens = set(_normalize(label).split())
            scores[label] = len(tokens & set(text.split()))
        winner = max(labels, key=lambda label: (scores[label], -labels.index(label)))
        total = sum(scores.values())
        return winner, (scores[winner] / total if total else 1.0 / len(labels))

    def _jev(self, item: DecisionInput) -> tuple[tuple[str, float], dict[str, Any]]:
        criterios = {
            "apoya": "El comentario respalda la afirmación de referencia.",
            "rechaza": "El comentario niega o refuta la afirmación de referencia.",
        } if item.kind == "stance" else {}
        criteria = {label: criterios.get(label, label) for label in item.labels}
        body = {
            "state": {"text": item.text, **dict(item.context)},
            "model": self.model,
            "questions": {
                "decision": {
                    "type": "choice",
                    "instructions": "Clasifica el comentario según su relación con la afirmación de referencia."
                    if item.kind == "stance" else "Elige la opción que describe el texto.",
                    "criteria": criteria,
                }
            },
        }
        started = time.perf_counter()
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.api_url,
            data=raw,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        response_data: dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                    response_data = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code not in (408, 429) and error.code < 500:
                    break
                if attempt < self.retries:
                    time.sleep(0.25 * (2**attempt))
            except (urllib.error.URLError, TimeoutError) as error:
                last_error = error
                if attempt < self.retries:
                    time.sleep(0.25 * (2**attempt))
        if response_data is None:
            raise RuntimeError("falló la solicitud a Jev") from last_error
        usage = response_data.get("usage", {})
        telemetry = {
            "input_tokens": int(usage.get("input_tokens", 0) or 0),
            "output_tokens": int(usage.get("output_tokens", 0) or 0),
            "api_seconds": time.perf_counter() - started,
        }
        answer = response_data.get("answers", {}).get("decision", {})
        label = str(answer.get("choice", ""))
        if label not in item.labels:
            raise ValueError("Jev devolvió una etiqueta fuera de las opciones")
        probabilities = answer.get("probabilities", {})
        probability = float(probabilities.get(label, answer.get("confidence", 0.0)) or 0.0)
        return (label, max(0.0, min(1.0, probability))), telemetry


_REJECT_MARKERS = ("mentira", "falso", "fake", "no es cierto", "sin pruebas", "inventan", "verso", "trucho", "nada que ver")
_SUPPORT_MARKERS = ("cierto", "verdad", "totalmente", "apoyo", "correcto", "exacto", "tal cual")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9áéíóúüñ ]", " ", text.lower())).strip()


def decidir(
    lote: Iterable[DecisionInput],
    *,
    mode: str = "local",
    cache_path: str | Path = DEFAULT_DB,
    **kwargs: Any,
) -> list[tuple[str, float]]:
    """Convenience wrapper matching the pipeline's ``decidir(lote)`` contract."""
    with DecisionEngine(mode=mode, cache_path=cache_path, **kwargs) as engine:
        return engine.decide(lote)


__all__ = ["DecisionEngine", "DecisionInput", "DecisionStats", "decidir"]
