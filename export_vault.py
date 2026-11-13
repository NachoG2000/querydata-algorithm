#!/usr/bin/env python3
"""Export pipeline aggregates as an Obsidian vault.

The exporter only writes generated files listed in its manifest. Existing user
notes remain untouched, so rerunning the export is safe after manual edits.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


MANIFEST = ".qualydata-export.json"


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path, compression="infer", dtype=str, keep_default_na=False)


def safe_name(value: object, fallback: str = "sin-nombre") -> str:
    text = str(value or fallback).strip()
    text = re.sub(r"[^\w\-. ]+", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text).strip("-.")
    return text[:100] or fallback


def as_number(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if column not in frame:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def yaml_value(value: object) -> str:
    text = str(value if value is not None else "").replace("\n", " ").strip()
    return json.dumps(text, ensure_ascii=False)


def frontmatter(values: dict[str, object]) -> str:
    lines = ["---"]
    for key, value in values.items():
        if isinstance(value, (int, float)) and not pd.isna(value):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def pick_examples(details: pd.DataFrame, label: str, limit: int = 5) -> pd.DataFrame:
    rows = details[details["narrativa"].astype(str) == label].copy()
    if rows.empty:
        return rows
    if "centralidad" in rows:
        rows["_centralidad"] = pd.to_numeric(rows["centralidad"], errors="coerce").fillna(0)
        rows = rows.sort_values(["_centralidad", "comentario_id"], ascending=[False, True])
    return rows.head(limit)


def daily_rows(states: pd.DataFrame, label: str) -> pd.DataFrame:
    if states.empty or "narrativa" not in states:
        return pd.DataFrame()
    return states[states["narrativa"].astype(str) == label].copy()


def narrative_note(label: str, meta: pd.Series, details: pd.DataFrame, states: pd.DataFrame,
                   source_names: dict[str, str], operation_links: list[str]) -> str:
    rows = pick_examples(details, label)
    daily = daily_rows(states, label)
    volume = int(pd.to_numeric(meta.get("volumen_total", len(rows)), errors="coerce") or 0)
    support = float(pd.to_numeric(meta.get("apoyo_pct", 0.0), errors="coerce") or 0.0)
    reject = float(pd.to_numeric(meta.get("rechazo_pct", 0.0), errors="coerce") or 0.0)
    origin = meta.get("fecha_origen", "")
    status = meta.get("estado_actual", meta.get("estado", "desconocido"))
    amplified_days = meta.get("dias_amplificada", 0)
    title = meta.get("titulo", label)
    keys = meta.get("frases_clave", "")
    links = []
    if "fuente_id" in rows:
        links = sorted({f"[[fuente-{safe_name(source_names.get(str(v), v))}]]" for v in rows["fuente_id"] if str(v)})
    body = [frontmatter({"tipo": "narrativa", "narrativa": label, "fecha_origen": origin,
                         "volumen_total": volume, "apoyo_pct": round(support, 4),
                         "rechazo_pct": round(reject, 4), "estado_actual": status,
                         "dias_amplificada": amplified_days}), "", f"# {title}", "",
           f"Etiqueta: `{label}`", f"Frases clave: {keys}", ""]
    if links:
        body.extend(["Fuentes relacionadas", "", " ".join(links), ""])
    if operation_links:
        body.extend(["Operaciones relacionadas", "", " ".join(operation_links), ""])
    body.extend(["Comentarios centrales", ""])
    if rows.empty:
        body.append("No hay detalles de comentarios en esta salida.")
    else:
        for _, row in rows.iterrows():
            text = str(row.get("texto", "")).replace("\n", " ").strip()
            body.append(f"- `{row.get('comentario_id', '')}` ({row.get('postura', '')}): {text}")
    body.extend(["", "Serie diaria", "", "| Día | Volumen | Apoya | Rechaza | Coordinada | Estado |", "| --- | ---: | ---: | ---: | ---: | --- |"])
    if daily.empty:
        body.append("| | 0 | 0 | 0 | 0 | desconocido |")
    else:
        for _, row in daily.sort_values("dia").iterrows():
            body.append("| {dia} | {volumen} | {apoyo} | {rechazo} | {coord} | {estado} |".format(
                dia=row.get("dia", ""), volumen=row.get("volumen", 0), apoyo=row.get("apoyo", 0),
                rechazo=row.get("rechazo", 0), coord=row.get("fraccion_coordinada", 0),
                estado=row.get("estado", "")))
    return "\n".join(body) + "\n"


def operation_note(group: str, accounts: pd.DataFrame, bursts: pd.DataFrame,
                   narrative_by_account: dict[str, set[str]], source_links: list[str]) -> str:
    members = accounts[accounts["grupo"].astype(str) == group].copy()
    ids = sorted(str(v) for v in members.get("cuenta_id", []))
    age = pd.to_numeric(members.get("antiguedad_dias", pd.Series(dtype=float)), errors="coerce").dropna()
    member_links = " ".join(f"`{account}`" for account in ids)
    group_bursts = bursts[bursts.get("grupo", pd.Series(dtype=str)).astype(str) == group] if not bursts.empty else pd.DataFrame()
    narrative_labels = sorted({label for account in ids for label in narrative_by_account.get(account, set())})
    narrative_links = " ".join(f"[[narrativa-{safe_name(label)}]]" for label in narrative_labels)
    body = [frontmatter({"tipo": "operacion", "grupo": group, "cuentas": len(ids),
                         "antiguedad_media_dias": round(float(age.mean()), 2) if not age.empty else 0,
                         "rafagas": len(group_bursts)}), "", f"# Operación {group}", "",
           f"Cuentas ({len(ids)}): {member_links or 'sin datos'}", "",
           f"Narrativas que empuja: {narrative_links or 'ninguna'}", "", "Ráfagas", ""]
    if source_links:
        body[body.index("Ráfagas"):] = ["Fuentes relacionadas", "", " ".join(source_links), "", "Ráfagas", ""]
    if group_bursts.empty:
        body.append("No hay detalle de ráfagas en esta salida.")
    else:
        body.extend(["| Publicación | Inicio | Fin | Cuentas |", "| --- | --- | --- | ---: |"])
        for _, row in group_bursts.iterrows():
            body.append(f"| {row.get('publicacion_id', '')} | {row.get('inicio', '')} | {row.get('fin', '')} | {row.get('cuentas', '')} |")
    return "\n".join(body) + "\n"


def export_vault(datos: Path, entrega: Path, vault: Path, auxiliares: Path | None = None) -> list[str]:
    vault.mkdir(parents=True, exist_ok=True)
    manifest_path = vault / MANIFEST
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": []}
    owned = set(previous.get("files", []))

    artifact_root = auxiliares or entrega
    if not (artifact_root / "estados.parquet").exists() and entrega.name == "entrega":
        artifact_root = Path("salida/final")
    required = [entrega / "narrativas.csv", entrega / "comentarios.csv", entrega / "cuentas.csv"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Faltan archivos de entrega: " + ", ".join(missing))

    narratives = read_table(entrega / "narrativas.csv")
    comments = read_table(entrega / "comentarios.csv")
    details = read_table(artifact_root / "detalles.parquet")
    states = read_table(artifact_root / "estados.parquet")
    accounts = read_table(entrega / "cuentas.csv")
    bursts = read_table(artifact_root / "rafagas.parquet")
    publications = read_table(datos / "publicaciones.csv.gz")
    sources = read_table(datos / "fuentes.csv")

    if details.empty and not comments.empty:
        raw = read_table(datos / "comentarios.csv.gz")
        if not raw.empty:
            details = raw.merge(comments[["comentario_id", "narrativa", "postura"]], on="comentario_id", how="left")
    if "narrativa" not in details:
        details["narrativa"] = "ninguna"
    if not publications.empty and "publicacion_id" in details and "publicacion_id" in publications:
        details = details.merge(publications[["publicacion_id", "fuente_id"]], on="publicacion_id", how="left")
    source_names = {}
    if not sources.empty and {"fuente_id", "nombre"}.issubset(sources.columns):
        source_names = dict(zip(sources["fuente_id"].astype(str), sources["nombre"].astype(str)))

    # Recompute account age at the latest observed comment. The official
    # accounts output intentionally contains only account_id and group.
    raw_accounts = read_table(datos / "cuentas.csv.gz")
    latest = pd.to_datetime(details.get("fecha", pd.Series(dtype=str)), errors="coerce", utc=True).max()
    if not accounts.empty and not raw_accounts.empty and {"cuenta_id", "fecha_creacion"}.issubset(raw_accounts.columns):
        ages = raw_accounts[["cuenta_id", "fecha_creacion"]].copy()
        ages["fecha_creacion"] = pd.to_datetime(ages["fecha_creacion"], errors="coerce", utc=True)
        days = (latest - ages["fecha_creacion"]).dt.total_seconds() / 86400 if pd.notna(latest) else 0
        age_map = dict(zip(ages["cuenta_id"].astype(str), days.fillna(0)))
        accounts["antiguedad_dias"] = accounts["cuenta_id"].astype(str).map(age_map).fillna(0)

    generated: list[str] = []
    narrative_meta = narratives.set_index("narrativa") if not narratives.empty and "narrativa" in narratives else pd.DataFrame()
    labels = sorted(set(narratives.get("narrativa", [])) | set(details.loc[details["narrativa"].astype(str) != "ninguna", "narrativa"]))
    if not accounts.empty and "grupo" in accounts:
        groups = sorted({str(v) for v in accounts["grupo"] if str(v)})
    else:
        groups = []

    account_narratives: dict[str, set[str]] = {}
    if {"cuenta_id", "narrativa"}.issubset(details.columns):
        for account, group in details.groupby("cuenta_id"):
            account_narratives[str(account)] = {str(v) for v in group["narrativa"] if str(v) != "ninguna"}

    operation_sources: dict[str, set[str]] = {group: set() for group in groups}
    if {"cuenta_id", "fuente_id"}.issubset(details.columns) and not accounts.empty:
        groups_by_account = dict(zip(accounts["cuenta_id"].astype(str), accounts["grupo"].astype(str)))
        for _, row in details.iterrows():
            group = groups_by_account.get(str(row.get("cuenta_id", "")), "")
            if group and str(row.get("fuente_id", "")):
                operation_sources.setdefault(group, set()).add(str(row["fuente_id"]))
    operation_source_links = {
        group: sorted(f"[[fuente-{safe_name(source_names.get(source, source))}]]" for source in ids)
        for group, ids in operation_sources.items()
    }
    operation_links_by_narrative: dict[str, set[str]] = {label: set() for label in labels}
    for group, narrative_labels in ((group, {label for account in accounts.loc[accounts["grupo"].astype(str) == group, "cuenta_id"].astype(str) for label in account_narratives.get(account, set())}) for group in groups):
        for label in narrative_labels:
            operation_links_by_narrative.setdefault(label, set()).add(f"[[operacion-{safe_name(group)}]]")

    if not states.empty and "narrativa" in states:
        for label in labels:
            rows = states[states["narrativa"].astype(str) == label]
            total = as_number(rows, "volumen").sum()
            if total:
                latest_row = rows.sort_values("dia").iloc[-1]
                if label not in narrative_meta.index:
                    narrative_meta.loc[label, "titulo"] = label
                narrative_meta.loc[label, "volumen_total"] = int(total)
                narrative_meta.loc[label, "apoyo_pct"] = float((as_number(rows, "apoyo") * as_number(rows, "volumen")).sum() / total)
                narrative_meta.loc[label, "rechazo_pct"] = float((as_number(rows, "rechazo") * as_number(rows, "volumen")).sum() / total)
                narrative_meta.loc[label, "estado_actual"] = latest_row.get("estado", "desconocido")
                narrative_meta.loc[label, "dias_amplificada"] = int(rows.get("amplificada", pd.Series(dtype=bool)).astype(str).str.lower().eq("true").sum())

    generated_contents: dict[str, str] = {}
    for label in labels:
        meta = narrative_meta.loc[label] if isinstance(narrative_meta, pd.DataFrame) and label in narrative_meta.index else pd.Series(dtype=object)
        relative = f"narrativa-{safe_name(label)}.md"
        generated_contents[relative] = narrative_note(label, meta, details, states, source_names, sorted(operation_links_by_narrative.get(label, set())))
        generated.append(relative)

    for group in groups:
        relative = f"operacion-{safe_name(group)}.md"
        generated_contents[relative] = operation_note(group, accounts, bursts, account_narratives, operation_source_links.get(group, []))
        generated.append(relative)

    # Source notes provide a stable graph endpoint for narratives and operations.
    narrative_sources = {label: set() for label in labels}
    if {"narrativa", "fuente_id"}.issubset(details.columns):
        for _, row in details.iterrows():
            label, source = str(row.get("narrativa", "")), str(row.get("fuente_id", ""))
            if label in narrative_sources and source:
                narrative_sources[label].add(source)
    operation_sources_by_source: dict[str, set[str]] = {}
    for group, source_ids in operation_sources.items():
        for source in source_ids:
            operation_sources_by_source.setdefault(source, set()).add(group)
    for source_id, source_name in source_names.items():
        narrative_links = sorted(f"[[narrativa-{safe_name(label)}]]" for label, ids in narrative_sources.items() if source_id in ids)
        operation_links = sorted(f"[[operacion-{safe_name(group)}]]" for group in operation_sources_by_source.get(source_id, set()))
        relative = f"fuente-{safe_name(source_name or source_id)}.md"
        generated_contents[relative] = "\n".join([
            frontmatter({"tipo": "fuente", "fuente_id": source_id, "nombre": source_name}), "",
            f"# {source_name}", "", f"ID: `{source_id}`", "",
            "Narrativas", "", " ".join(narrative_links) or "Ninguna", "",
            "Operaciones", "", " ".join(operation_links) or "Ninguna", "",
        ])
        generated.append(relative)

    index = [frontmatter({"tipo": "indice", "generado_por": "export_vault.py"}), "", "# Índice QualyData", "", "## Narrativas", "", "| Narrativa | Título | Origen | Volumen | Estado |", "| --- | --- | --- | ---: | --- |"]
    for label in labels:
        meta = narrative_meta.loc[label] if isinstance(narrative_meta, pd.DataFrame) and label in narrative_meta.index else pd.Series(dtype=object)
        index.append(f"| [[narrativa-{safe_name(label)}]] | {meta.get('titulo', label)} | {meta.get('fecha_origen', '')} | {meta.get('volumen_total', '')} | {meta.get('estado_actual', meta.get('estado', ''))} |")
    index.extend(["", "## Operaciones", "", "| Operación | Cuentas | Narrativas |", "| --- | ---: | --- |"])
    for group in groups:
        ids = accounts.loc[accounts["grupo"].astype(str) == group, "cuenta_id"].astype(str).tolist() if "grupo" in accounts else []
        labels_for_group = sorted({label for account in ids for label in account_narratives.get(account, set())})
        index.append(f"| [[operacion-{safe_name(group)}]] | {len(ids)} | {' '.join(f'[[narrativa-{safe_name(label)}]]' for label in labels_for_group)} |")
    index.extend(["", "## Consultas Dataview", "", "```dataview", "TABLE fecha_origen, volumen_total, estado_actual, dias_amplificada", "FROM \".\"", "WHERE tipo = \"narrativa\"", "SORT volumen_total DESC", "```"])
    generated_candidates = sorted(set(generated + ["index.md"]))
    collisions = [relative for relative in generated_candidates if (vault / relative).exists() and relative not in owned]
    if collisions:
        raise FileExistsError("El vault ya contiene notas no generadas por este exportador: " + ", ".join(collisions))
    for relative in owned:
        target = vault / relative
        if target.is_file():
            target.unlink()
    for relative, content in generated_contents.items():
        (vault / relative).write_text(content, encoding="utf-8")
    index_path = vault / "index.md"
    index_path.write_text("\n".join(index) + "\n", encoding="utf-8")
    generated.append("index.md")
    manifest_path.write_text(json.dumps({"files": sorted(generated)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return generated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path("datos/practica"))
    parser.add_argument("--entrega", type=Path, default=Path("salida/practica"))
    parser.add_argument("--auxiliares", type=Path, default=None)
    parser.add_argument("--vault", type=Path, default=Path("vault"))
    args = parser.parse_args()
    files = export_vault(args.datos, args.entrega, args.vault, args.auxiliares)
    print(f"Vault generado en {args.vault} con {len(files)} archivos")


if __name__ == "__main__":
    main()
