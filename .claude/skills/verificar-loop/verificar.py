"""Chequea las invariantes del loop de experimentación (docs/contexto.md 2.4) contra experiments.tsv y git."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
PERMITIDOS = {"pipeline.py", "decisores.py"}
BITACORA = {"experiments.tsv", "RESULTS.md", "NOTES.md", "program.md", "FINAL_RUN.md"}
ESTADOS = {"accepted", "discarded"}
PARTICIONES = ["completo", "dia_1_7", "dia_8_14", "dia_1_10"]
TAREAS = ["narrativas", "coordinacion"]


def git(*args):
    r = subprocess.run(["git", "-C", str(RAIZ), *args], text=True, capture_output=True)
    return r.returncode, r.stdout.strip()


def archivos(desde, hasta):
    _, salida = git("diff", "--name-only", desde, hasta) if desde else git("show", "--name-only", "--format=", hasta)
    return set(filter(None, salida.splitlines()))


def puntos(fila):
    comp = json.loads(fila.componentes)
    return {(p, t): float(comp[p][t]["puntos"]) for p in PARTICIONES if p in comp for t in TAREAS}


def era(fila):
    return "por_tarea" if "dia_1_10" in json.loads(fila.componentes) else "combinado_margen"


def chequear(d, existe=None):
    existe = existe or (lambda c: git("cat-file", "-e", f"{c}^{{commit}}")[0] == 0)
    fallas = {}

    sin_estado = d[~d.estado.isin(ESTADOS)].id.tolist()
    huecos = sorted(set(range(1, int(d.id.max()) + 1)) - set(d.id.astype(int)))
    fallas["I1 toda corrida registrada"] = [f"fila {i}: estado fuera de {sorted(ESTADOS)}" for i in sin_estado] + [f"id faltante {i}" for i in huecos]

    aceptadas = d[d.estado.eq("accepted")]
    regresiones, fuera, previa = [], [], None
    for fila in aceptadas.itertuples():
        if previa is None:
            pass
        elif not existe(fila.commit):
            fuera.append(f"fila {fila.id}: commit {fila.commit[:7]} no existe en git")
        else:
            extra = archivos(previa.commit, fila.commit) - PERMITIDOS
            codigo = sorted(extra - BITACORA)
            if codigo:
                fuera.append(f"fila {fila.id} ({fila.commit[:7]}): cambia fuera de pipeline.py/decisores.py desde la aceptada anterior: {codigo}")
        if previa is not None:
            antes, ahora = puntos(previa), puntos(fila)
            for clave in sorted(set(antes) & set(ahora)):
                if ahora[clave] < antes[clave] - 1e-9:
                    regresiones.append(f"fila {fila.id} vs {previa.id} [{era(fila)}]: {clave[0]}.{clave[1]} {antes[clave]:.2f} -> {ahora[clave]:.2f}")
        previa = fila
    fallas["I2 aceptada no empeora ninguna tarea ni partición"] = regresiones
    fallas["I4 el loop solo edita pipeline.py/decisores.py"] = fuera

    arrastre, ultima_aceptada = [], None
    filas = list(d.itertuples())
    for actual, siguiente in zip(filas, filas[1:]):
        if actual.estado == "accepted":
            ultima_aceptada = actual.commit
        if actual.estado == "discarded" and ultima_aceptada and existe(actual.commit) and existe(ultima_aceptada):
            base = archivos(ultima_aceptada, actual.commit) & PERMITIDOS
            if base:
                arrastre.append(f"fila {actual.id} descartada corrió sobre {actual.commit[:7]}, cuyo {sorted(base)} difiere de la última aceptada {ultima_aceptada[:7]}")
        if actual.estado != "discarded" or siguiente.estado != "discarded":
            continue
        if not (existe(actual.commit) and existe(siguiente.commit)):
            arrastre.append(f"fila {actual.id}->{siguiente.id}: commit ausente, no verificable")
            continue
        cambio = archivos(actual.commit, siguiente.commit) & PERMITIDOS
        if cambio:
            arrastre.append(f"fila {actual.id} descartada -> fila {siguiente.id}: {sorted(cambio)} cambió entre {actual.commit[:7]} y {siguiente.commit[:7]} sin aceptada intermedia")
    fallas["I3 descartada deja el código como antes"] = arrastre
    return fallas


def romper(d):
    d = d.copy()
    d.loc[d.index[0], "estado"] = ""
    d = d[d.id != d.id.iloc[5]]
    ultima = d[d.estado.eq("accepted")].iloc[-1].copy()
    comp = json.loads(ultima.componentes)
    comp["dia_1_7"]["coordinacion"]["puntos"] -= 1
    ultima["componentes"] = json.dumps(comp)
    ultima["id"] = int(d.id.max()) + 1
    ultima["commit"] = "0" * 40
    descartada = d.iloc[-1].copy()
    descartada["id"] = int(d.id.max()) + 2
    descartada["estado"] = "discarded"
    descartada["commit"] = d[d.estado.eq("accepted")].iloc[0].commit
    otra = descartada.copy()
    otra["id"] += 1
    otra["commit"] = d.iloc[-1].commit
    return pd.concat([d, ultima.to_frame().T, descartada.to_frame().T, otra.to_frame().T], ignore_index=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--romper", action="store_true", help="Corre los chequeos sobre una copia en memoria mutada a propósito.")
    args = parser.parse_args()
    d = pd.read_csv(RAIZ / "experiments.tsv", sep="\t")
    if args.romper:
        d = romper(d)
        print("MODO --romper: copia en memoria con estado vacío, id faltante, aceptada que empeora dia_1_7.coordinacion con commit inexistente, y dos descartadas consecutivas sobre código distinto.")
    print(f"filas={len(d)} aceptadas={int(d.estado.eq('accepted').sum())} descartadas={int(d.estado.eq('discarded').sum())}")
    fallas = chequear(d)
    for nombre, lista in fallas.items():
        print(f"\n{'FALLA' if lista else 'OK   '} {nombre} ({len(lista)})")
        for linea in lista:
            print(f"  - {linea}")
    sys.exit(1 if any(fallas.values()) else 0)


if __name__ == "__main__":
    main()
