"""Run the pipeline on the practice set and two time-based validation splits.

The evaluator keeps split inputs under the output directory, invokes the official
scorer, and appends one auditable row to ``experiments.tsv``.  It never reads
truth data from the pipeline process.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import pandas as pd


METRIC_WEIGHTS = {
    "seconds_penalty": 0.001,
    "usd_per_thousand_penalty": 1.0,
    "validation_margin": 0.2,
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def write_gzip_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
        handle = io.TextIOWrapper(compressed, encoding="utf-8", newline="")
        frame.to_csv(handle, index=False)
        handle.flush()


def make_split(source: Path, truth: Path, destination: Path, keep_dates: set[str]) -> None:
    comments = read_csv(source / "comentarios.csv.gz")
    dates = pd.to_datetime(comments["fecha"], errors="coerce", utc=True, format="mixed")
    local_dates = dates.dt.tz_convert("America/Argentina/Salta").dt.date.astype("string")
    selected = comments.loc[local_dates.isin(keep_dates)].copy()
    selected_ids = set(selected["comentario_id"])
    selected.loc[~selected["respuesta_a"].isin(selected_ids), "respuesta_a"] = ""
    publication_ids = set(selected["publicacion_id"])
    account_ids = set(selected["cuenta_id"])

    write_gzip_csv(selected, destination / "comentarios.csv.gz")
    publications = read_csv(source / "publicaciones.csv.gz")
    publications = publications[publications["publicacion_id"].isin(publication_ids)]
    write_gzip_csv(publications, destination / "publicaciones.csv.gz")
    accounts = read_csv(source / "cuentas.csv.gz")
    accounts = accounts[accounts["cuenta_id"].isin(account_ids)]
    write_gzip_csv(accounts, destination / "cuentas.csv.gz")
    shutil.copy2(source / "fuentes.csv", destination / "fuentes.csv")

    truth_out = destination / "verdad"
    truth_out.mkdir(parents=True, exist_ok=True)
    truth_comments = read_csv(truth / "comentarios.csv.gz")
    truth_comments = truth_comments[truth_comments["comentario_id"].isin(selected_ids)]
    write_gzip_csv(truth_comments, truth_out / "comentarios.csv.gz")
    narrative_ids = set(truth_comments.loc[truth_comments["narrativa_id"] != "ninguna", "narrativa_id"])
    narratives = read_csv(truth / "narrativas.csv")
    narratives = narratives[narratives["narrativa_id"].isin(narrative_ids)].copy()
    origins = pd.to_datetime(narratives["fecha_origen"], errors="coerce", utc=True, format="mixed").dt.tz_convert("America/Argentina/Salta")
    outside = ~origins.dt.date.astype("string").isin(keep_dates)
    narratives.loc[(narratives["emergente"] == "si") & outside, "emergente"] = "no"
    narratives.to_csv(truth_out / "narrativas.csv", index=False)
    truth_accounts = read_csv(truth / "cuentas.csv.gz")
    truth_accounts = truth_accounts[truth_accounts["cuenta_id"].isin(account_ids)]
    write_gzip_csv(truth_accounts, truth_out / "cuentas.csv.gz")


def invoke_pipeline(data: Path, output: Path, decisor: str, timeout: float) -> dict:
    started = time.perf_counter()
    command = [sys.executable, "pipeline.py", "--datos", str(data), "--entrega", str(output), "--decisor", decisor]
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"pipeline timed out after {timeout:.0f}s for {data}") from exc
    elapsed = time.perf_counter() - started
    if result.returncode:
        raise RuntimeError(f"pipeline failed for {data}:\n{result.stdout}\n{result.stderr}")
    metrics_path = output / "metricas.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
    # Artifact durations describe a stable reference run. Penalize this run's
    # actual measured time, including cold embedding/model work when present.
    for line in result.stdout.splitlines():
        if line.startswith("telemetria: "):
            metrics.update(json.loads(line.removeprefix("telemetria: ")))
    metrics.setdefault("segundos", elapsed)
    metrics["runner_segundos"] = elapsed
    return metrics


def score(truth: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "puntaje.json"
    command = [sys.executable, "evaluacion/puntuar.py", "--verdad", str(truth), "--entrega", str(output), "--json", str(json_path)]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"scorer failed for {output}:\n{result.stdout}\n{result.stderr}")
    return json.loads(json_path.read_text(encoding="utf-8"))


def combined(score_result: dict, metrics: dict) -> float:
    points = float(score_result["narrativas"]["puntos"]) + float(score_result["coordinacion"]["puntos"])
    cost = score_result.get("costo") or {}
    seconds = float(metrics.get("segundos", cost.get("segundos", 0.0)))
    usd_k = float(cost.get("usd_por_mil_comentarios", 0.0))
    return points - METRIC_WEIGHTS["seconds_penalty"] * seconds - METRIC_WEIGHTS["usd_per_thousand_penalty"] * usd_k


def append_experiment(path: Path, row: dict) -> None:
    fields = ["id", "fecha", "commit", "estado", "resumen_params", "completo", "dia_1_7", "dia_8_14", "componentes", "costos", "tiempos", "wall_total", "margen_validacion"]
    exists = path.exists()
    if exists:
        with path.open(encoding="utf-8", newline="") as handle:
            row_id = sum(1 for _ in handle)
    else:
        row_id = 1
    row["id"] = row_id
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in fields})


def git_commit() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def mark_experiment(path: Path, status: str, experiment_id: str | None) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        rows = list(reader)
    matches = [row for row in rows if row["estado"] == "pending" and
               (experiment_id is None or row["id"] == experiment_id)]
    if not matches:
        raise ValueError("No se encontró un experimento pendiente.")
    row = matches[-1]
    row["estado"] = status
    if status == "accepted":
        row["commit"] = git_commit()
    with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    Path(handle.name).replace(path)
    return row["id"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path("datos/practica"))
    parser.add_argument("--salida", type=Path, default=Path("salida"))
    parser.add_argument("--decisor", choices=("local", "jev"), default="local")
    parser.add_argument("--resumen", default="")
    parser.add_argument("--estado", choices=("accepted", "discarded", "pending"), default="pending")
    parser.add_argument("--marcar", choices=("accepted", "discarded"), help="Marca un experimento pendiente.")
    parser.add_argument("--id", help="ID para --marcar. Por defecto marca el último pendiente.")
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--presupuesto", type=float, default=600.0)
    args = parser.parse_args()

    experiment_path = Path("experiments.tsv")
    if args.marcar:
        marcado = mark_experiment(experiment_path, args.marcar, args.id)
        print(f"Experimento {marcado}: {args.marcar}")
        return
    if min(args.timeout, args.presupuesto) <= 0:
        parser.error("Los límites de tiempo deben ser positivos.")
    started = time.perf_counter()

    source = args.datos.resolve()
    truth = source / "verdad"
    comments = read_csv(source / "comentarios.csv.gz")
    local_timestamps = pd.to_datetime(comments["fecha"], errors="coerce", utc=True, format="mixed").dt.tz_convert("America/Argentina/Salta")
    day_values = sorted(set(local_timestamps.dt.date.astype("string").dropna()))
    if len(day_values) < 2:
        parser.error("Se necesitan comentarios en al menos dos días locales.")
    midpoint = len(day_values) // 2
    splits = {"dia_1_7": set(day_values[:midpoint]), "dia_8_14": set(day_values[midpoint:])}
    args.salida.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}
    full_output = args.salida / "practica"
    full_metrics = invoke_pipeline(source, full_output, args.decisor, min(args.timeout, args.presupuesto - (time.perf_counter() - started)))
    full_score = score(truth, full_output)
    results["completo"] = {"score": full_score, "metrics": full_metrics}

    with TemporaryDirectory(prefix="qualydata-eval-", dir=args.salida) as temp_name:
        temp_root = Path(temp_name)
        for name, dates in splits.items():
            split_input = temp_root / name
            split_output = args.salida / "eval" / name
            make_split(source, truth, split_input, dates)
            remaining = args.presupuesto - (time.perf_counter() - started)
            if remaining <= 0:
                raise RuntimeError("evaluation budget exhausted before validation split")
            metrics = invoke_pipeline(split_input, split_output, args.decisor, min(args.timeout, remaining))
            results[name] = {"score": score(split_input / "verdad", split_output), "metrics": metrics}

    full_value = combined(results["completo"]["score"], results["completo"]["metrics"])
    validation_values = [combined(results[name]["score"], results[name]["metrics"]) for name in splits]
    status = args.estado

    params = results["completo"]["metrics"].get("params", {})
    row = {
        "fecha": datetime.now(ZoneInfo("America/Argentina/Salta")).isoformat(),
        "commit": git_commit(),
        "estado": status,
        "resumen_params": json.dumps({"resumen": args.resumen, "params": params}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "completo": f"{full_value:.6f}",
        "dia_1_7": f"{validation_values[0]:.6f}",
        "dia_8_14": f"{validation_values[1]:.6f}",
        "componentes": json.dumps({name: {"narrativas": {k: v for k, v in item["score"]["narrativas"].items() if k != "origen_por_narrativa"}, "coordinacion": item["score"]["coordinacion"]} for name, item in results.items()}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "costos": json.dumps({name: item["score"].get("costo") for name, item in results.items()}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "tiempos": json.dumps({name: {"pipeline": item["metrics"].get("segundos"), "runner": item["metrics"].get("runner_segundos"), "etapas": item["metrics"].get("etapas", {}), "fraccion_ia": item["metrics"].get("fraccion_ia", 0.0)} for name, item in results.items()}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        "wall_total": f"{time.perf_counter() - started:.3f}",
        "margen_validacion": f"{METRIC_WEIGHTS['validation_margin']:.6f}",
    }
    append_experiment(Path("experiments.tsv"), row)
    print("particion\tcombinado\tpuntos\tsegundos")
    for name, item in results.items():
        value = combined(item["score"], item["metrics"])
        points = float(item["score"]["narrativas"]["puntos"]) + float(item["score"]["coordinacion"]["puntos"])
        print(f"{name}\t{value:.6f}\t{points:.2f}\t{float(item['metrics'].get('segundos', 0.0)):.3f}")
    print(f"experimento\t{row['id']}\t{status}\t{row['wall_total']} s de pared")


if __name__ == "__main__":
    main()
