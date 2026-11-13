"""Pinned multilingual NLI with a content-addressed local logit cache.

Truth labels are never inputs. Threshold calibration reuses raw logits, so a
change in a decision threshold cannot invalidate or leak into model inference.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
import unicodedata

import numpy as np


class LocalNLI:
    def __init__(self, cache: Path, model: str, revision: str, max_length: int = 128,
                 batch_size: int = 32, threads: int = 4):
        self.model = model
        self.revision = revision
        self.max_length = max_length
        self.batch_size = batch_size
        self.threads = threads
        cache.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(cache / "nli_logits.sqlite3")
        self.db.execute("CREATE TABLE IF NOT EXISTS nli_logits ("
                        "key BLOB PRIMARY KEY, entail REAL NOT NULL, "
                        "neutral REAL NOT NULL, contradict REAL NOT NULL)")
        self.schema = json.dumps(["nli-logits-v1", model, revision, max_length],
                                 ensure_ascii=False, separators=(",", ":"))
        self.logical_pairs = 0

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def clean(text):
        return " ".join(unicodedata.normalize("NFKC", str(text)).split())

    def logits(self, premises, hypotheses):
        if len(premises) != len(hypotheses):
            raise ValueError("Each premise must have one hypothesis")
        pairs = [(self.clean(p), self.clean(h)) for p, h in zip(premises, hypotheses)]
        keys = [hashlib.sha256(json.dumps([self.schema, p, h], ensure_ascii=False,
                                         separators=(",", ":")).encode()).digest()
                for p, h in pairs]
        unique = dict(zip(keys, pairs))
        found = {}
        ordered = sorted(unique)
        for start in range(0, len(ordered), 800):
            chunk = ordered[start:start + 800]
            query = ("SELECT key,entail,neutral,contradict FROM nli_logits WHERE key IN ("
                     + ",".join("?" for _ in chunk) + ")")
            found.update((row[0], row[1:]) for row in self.db.execute(query, chunk))
        missing = [key for key in ordered if key not in found]
        self.logical_pairs += len(keys)
        if missing:
            self._infer(missing, unique, found)
        return np.asarray([found[key] for key in keys], dtype=np.float32).reshape(-1, 3)

    def _infer(self, missing, unique, found):
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        torch.manual_seed(42)
        torch.set_num_threads(self.threads)
        options = {
            "revision": self.revision,
            "cache_dir": str((Path(os.environ.get("HF_HOME", ".cache/huggingface")) / "hub").resolve()),
            "local_files_only": os.environ.get("HF_HUB_OFFLINE", "").lower() in {"1", "true", "yes"},
        }
        tokenizer = AutoTokenizer.from_pretrained(self.model, use_fast=True, **options)
        model = AutoModelForSequenceClassification.from_pretrained(self.model, **options).eval()
        labels = {str(label).lower(): int(i) for i, label in model.config.id2label.items()}
        columns = [next(value for label, value in labels.items() if name in label)
                   for name in ["entail", "neutral", "contrad"]]
        missing.sort(key=lambda key: (max(len(unique[key][0]), len(unique[key][1])), key))
        started = time.perf_counter()
        with torch.inference_mode():
            for start in range(0, len(missing), self.batch_size):
                chunk = missing[start:start + self.batch_size]
                premises = [unique[key][0] for key in chunk]
                hypotheses = [unique[key][1] for key in chunk]
                encoded = tokenizer(premises, hypotheses, padding=True, truncation=True,
                                    max_length=self.max_length, return_tensors="pt")
                values = model(**encoded).logits[:, columns].cpu().numpy()
                rows = [(key, *map(float, value)) for key, value in zip(chunk, values)]
                self.db.executemany("INSERT OR REPLACE INTO nli_logits VALUES (?,?,?,?)", rows)
                found.update((row[0], row[1:]) for row in rows)
                if start % (self.batch_size * 16) == 0 or start + len(chunk) >= len(missing):
                    self.db.commit()
                    print("nli_local: " + json.dumps({
                        "nuevos": min(start + len(chunk), len(missing)),
                        "total_nuevos": len(missing),
                        "segundos": round(time.perf_counter() - started, 2),
                    }), flush=True)
        self.db.commit()


def softmax(values):
    values = values - values.max(axis=-1, keepdims=True)
    exp = np.exp(values)
    return exp / exp.sum(axis=-1, keepdims=True)


ROOT_SUPPORT = "Este texto afirma que algo es verdad."
ROOT_REJECT = "Este texto niega que algo sea verdad."


def root_probabilities(engine, texts):
    n = len(texts)
    logits = engine.logits(list(texts) + list(texts), [ROOT_SUPPORT] * n + [ROOT_REJECT] * n)
    return softmax(np.column_stack((logits[:n, 0], logits[n:, 0])))
