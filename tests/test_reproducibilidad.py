"""Reference measurements must be stable without hiding actual runtime."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import eval as evaluator
import pipeline


class ReproducibilidadTest(unittest.TestCase):
    def test_reference_reuses_only_times_and_invalidates_on_input_or_params(self):
        with TemporaryDirectory() as root:
            root = Path(root)
            data, cache = root / "data", root / "cache"
            data.mkdir()
            for name in pipeline.ARCHIVOS:
                (data / f"{name}.csv").write_text("id\na\n")
            cost = {"segundos": 10.0, "hardware": "test", "usd_ia": 0}
            metrics = {"segundos": 10.0, "etapas": {"cargar": 2.0},
                       "decisor": "local", "params": {"seed": 42}, "calidad": {"n": 1}}
            first = pipeline.reporte_referencia(data, cache, cost, metrics)
            current = {**metrics, "segundos": 20.0, "etapas": {"cargar": 3.0}}
            second = pipeline.reporte_referencia(data, cache, {**cost, "segundos": 20.0}, current)
            self.assertEqual(first, second)
            changed = pipeline.reporte_referencia(data, cache, cost, {**current, "calidad": {"n": 2}})
            self.assertEqual(changed[1]["calidad"], {"n": 2})
            previous = first
            for change in ("input", "params"):
                with self.subTest(change=change):
                    if change == "input":
                        (data / "comentarios.csv").write_text("id\nb\n")
                    else:
                        current = {**current, "params": {"seed": 43}}
                    result = pipeline.reporte_referencia(data, cache, {**cost, "segundos": 20.0}, current)
                    self.assertEqual(result[0]["segundos"], 20.0)
                    self.assertNotEqual(previous[0]["medicion"]["huella"], result[0]["medicion"]["huella"])
                    previous = result

    def test_api_costs_are_never_reused(self):
        cost, metrics = {"segundos": 10, "usd_ia": 0.5}, {"decisor": "jev"}
        self.assertEqual(pipeline.reporte_referencia(Path("absent"), Path("absent"), cost, metrics),
                         (cost, metrics))

    def test_evaluator_penalizes_current_measurement(self):
        with TemporaryDirectory() as root:
            output = Path(root)
            (output / "metricas.json").write_text(json.dumps({"segundos": 100, "etapas": {"cargar": 80}}))
            result = SimpleNamespace(returncode=0, stdout='telemetria: {"segundos": 3, "etapas": {"cargar": 1}}\n')
            with patch.object(evaluator.subprocess, "run", return_value=result):
                metrics = evaluator.invoke_pipeline(Path("data"), output, "local", 300)
            score = {"narrativas": {"puntos": 10}, "coordinacion": {"puntos": 5}}
            self.assertEqual(metrics["etapas"], {"cargar": 1})
            self.assertAlmostEqual(evaluator.combined(score, metrics), 15 - 0.003)


if __name__ == "__main__":
    unittest.main()
