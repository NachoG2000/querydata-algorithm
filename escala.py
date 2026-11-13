"""Prepare and measure replicated data sets for the cost and scale pitch."""
from __future__ import annotations

import argparse
import gzip
import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd


def copy_replicated(source: Path, destination: Path, factor: int) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "fuentes.csv", destination / "fuentes.csv")
    for name in ("comentarios.csv.gz", "publicaciones.csv.gz", "cuentas.csv.gz"):
        with destination.joinpath(name).open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            writer = io.TextIOWrapper(compressed, encoding="utf-8", newline="")
            first = True
            for frame in pd.read_csv(source / name, dtype=str, keep_default_na=False, chunksize=100_000):
                for replica in range(factor):
                    copied = frame.copy()
                    suffix = f"__r{replica:02d}" if factor > 1 else ""
                    for column in ("comentario_id", "publicacion_id", "cuenta_id"):
                        if column in copied:
                            copied[column] = copied[column].astype(str) + suffix
                    if "respuesta_a" in copied:
                        copied["respuesta_a"] = copied["respuesta_a"].replace("", pd.NA).astype("string").fillna("")
                        copied.loc[copied["respuesta_a"] != "", "respuesta_a"] += suffix
                    writer.write(copied.to_csv(index=False, header=first))
                    first = False
            writer.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path("datos/practica"))
    parser.add_argument("--salida", type=Path, default=Path("salida/escala"))
    parser.add_argument("--factores", nargs="+", type=int, default=[1, 5, 20])
    parser.add_argument("--incluir-50", action="store_true")
    parser.add_argument("--decisor", choices=("local", "jev"), default="local")
    args = parser.parse_args()
    factors = list(dict.fromkeys(args.factores + ([50] if args.incluir_50 else [])))
    if any(factor <= 0 for factor in factors):
        parser.error("all scale factors must be positive")
    args.salida.mkdir(parents=True, exist_ok=True)
    rows = []
    for factor in factors:
        data_dir = args.salida / "datos" / f"x{factor}"
        output_dir = args.salida / "salidas" / f"x{factor}"
        preparation_started = time.perf_counter()
        copy_replicated(args.datos, data_dir, factor)
        preparation_seconds = time.perf_counter() - preparation_started
        pipeline_started = time.perf_counter()
        result = subprocess.run([sys.executable, "pipeline.py", "--datos", str(data_dir), "--entrega", str(output_dir), "--decisor", args.decisor], text=True, capture_output=True)
        pipeline_seconds = time.perf_counter() - pipeline_started
        if result.returncode:
            raise RuntimeError(f"pipeline failed at x{factor}:\n{result.stdout}\n{result.stderr}")
        cost = json.loads((output_dir / "costo.json").read_text(encoding="utf-8"))
        rows.append({"factor": factor, "comentarios": cost.get("comentarios_procesados", ""), "preparacion_segundos": round(preparation_seconds, 3), "pipeline_segundos": round(pipeline_seconds, 3), "segundos": round(preparation_seconds + pipeline_seconds, 3), "usd_ia": cost.get("usd_ia", 0.0), "usd_por_mil_comentarios": cost.get("usd_por_mil_comentarios", 0.0), "hardware": cost.get("hardware", "")})
        (args.salida / "resultados.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"x{factor}: preparación {preparation_seconds:.3f}s, pipeline {pipeline_seconds:.3f}s, {rows[-1]['comentarios']} comentarios")
        with (args.salida / "resultados.tsv").open("w", encoding="utf-8") as handle:
            handle.write("factor\tcomentarios\tpreparacion_segundos\tpipeline_segundos\tsegundos\tusd_ia\tusd_por_mil_comentarios\thardware\n")
            for row in rows:
                handle.write("\t".join(str(row[key]) for key in ("factor", "comentarios", "preparacion_segundos", "pipeline_segundos", "segundos", "usd_ia", "usd_por_mil_comentarios", "hardware")) + "\n")



if __name__ == "__main__":
    main()
