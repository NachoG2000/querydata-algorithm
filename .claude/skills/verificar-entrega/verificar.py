"""Chequea las invariantes de la entrega del set final (docs/contexto.md 2.5) contra git y los archivos reales.

Uso: python verificar.py [--romper] [--tests]
Sale con código 1 si algún chequeo falla.
"""
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip())
ARCHIVOS = ["comentarios.csv", "narrativas.csv", "cuentas.csv", "costo.json"]
POSTURAS = {"apoya", "rechaza", "neutral", ""}
SECRETOS = re.compile(r"sk-[A-Za-z0-9]{16,}|hf_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|api[_-]?key|secret|bearer\s|ghp_[A-Za-z0-9]{20,}|/Users/|/home/[a-z]", re.IGNORECASE)
resultados = []


def git(*args, binario=False):
    salida = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, check=True)
    return salida.stdout if binario else salida.stdout.decode()


def registrar(invariante, nombre, ok, detalle):
    estado = {True: "PASA", False: "FALLA", None: "NO VERIFICABLE"}[ok]
    resultados.append((invariante, nombre, ok))
    print(f"[{estado}] inv{invariante} {nombre}: {detalle}")


def constante(fuente, nombre):
    for nodo in ast.parse(fuente).body:
        if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], "id", None) == nombre:
            return ast.literal_eval(nodo.value)


def claves_costo(fuente):
    arbol = ast.parse(fuente)
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], "id", None) == "costo" and isinstance(nodo.value, ast.Dict) and None not in nodo.value.keys:
            return {k.value for k in nodo.value.keys}
    return set()


def manifiesto(texto):
    bloque = texto.split("## SHA256 de entrega", 1)[1]
    return {nombre: h for h, nombre in re.findall(r"([0-9a-f]{64})\s+(\S+)", bloque)}


def validar_entrega(etiqueta, archivos, fuente_pipeline, manifiesto_final):
    faltan = [a for a in ARCHIVOS if a not in archivos]
    registrar(1, f"{etiqueta} contiene los 4 archivos", not faltan, f"faltan {faltan}" if faltan else "ok")
    if faltan:
        return
    esperado = {"comentarios.csv": ["comentario_id", "narrativa", "postura"],
                "narrativas.csv": constante(fuente_pipeline, "NARRATIVAS"),
                "cuentas.csv": ["cuenta_id", "grupo"]}
    tablas = {n: pd.read_csv(io.BytesIO(archivos[n]), dtype=str, keep_default_na=False) for n in esperado}
    for nombre, columnas in esperado.items():
        real = list(tablas[nombre].columns)
        registrar(1, f"{etiqueta}/{nombre} columnas", real == columnas, f"{real} vs {columnas}")
    for nombre, clave in (("comentarios.csv", "comentario_id"), ("narrativas.csv", "narrativa"), ("cuentas.csv", "cuenta_id")):
        if clave in tablas[nombre]:
            dup = tablas[nombre][clave][tablas[nombre][clave].duplicated()].head(3).tolist()
            registrar(1, f"{etiqueta}/{nombre} ids únicos", not dup, f"duplicados {dup}" if dup else f"{len(tablas[nombre])} filas")
    cuentas = tablas["cuentas.csv"]
    if {"cuenta_id", "grupo"} <= set(cuentas):
        marcadas = cuentas[cuentas.grupo.ne("")]
        multi = marcadas.groupby("cuenta_id").grupo.nunique()
        multi = multi[multi > 1].index.tolist()[:3]
        registrar(1, f"{etiqueta}/cuentas.csv cada cuenta en ≤1 grupo", not multi, f"en varios grupos {multi}" if multi else f"{marcadas.cuenta_id.nunique()} cuentas en {marcadas.grupo.nunique()} grupos")
    com = tablas["comentarios.csv"]
    if {"narrativa", "postura"} <= set(com):
        conocidas = set(tablas["narrativas.csv"].get("narrativa", [])) | {"", "ninguna"}
        huerfanas = sorted(set(com.narrativa) - conocidas)[:3]
        registrar(1, f"{etiqueta} narrativas referenciadas existen", not huerfanas, f"huérfanas {huerfanas}" if huerfanas else "ok")
        malas = sorted(set(com.postura) - POSTURAS)[:3]
        registrar(1, f"{etiqueta} posturas válidas", not malas, f"valores {malas}" if malas else "ok")
    try:
        costo = json.loads(archivos["costo.json"])
        faltan = sorted(claves_costo(fuente_pipeline) - set(costo))
        registrar(1, f"{etiqueta}/costo.json campos de pipeline.py:ejecutar", not faltan, f"faltan {faltan}" if faltan else "ok")
    except json.JSONDecodeError as error:
        registrar(1, f"{etiqueta}/costo.json es JSON", False, str(error))
    distintos = [n for n in ARCHIVOS if hashlib.sha256(archivos[n]).hexdigest() != manifiesto_final.get(n)]
    registrar(1, f"{etiqueta} hashes = manifiesto de FINAL_RUN.md", not distintos, f"distintos {distintos}" if distintos else "4/4 iguales")
    hallazgos = [(n, m.group(0)) for n in ARCHIVOS for m in [SECRETOS.search(archivos[n].decode("utf-8", "replace"))] if m]
    registrar(4, f"{etiqueta} sin claves ni rutas personales", not hallazgos, f"{hallazgos}" if hallazgos else "ok")


def leer_ref(ref):
    return {a: git("show", f"{ref}:entrega/{a}", binario=True) for a in ARCHIVOS
            if subprocess.run(["git", "cat-file", "-e", f"{ref}:entrega/{a}"], cwd=RAIZ, capture_output=True).returncode == 0}


def romper(archivos):
    """Copias en memoria con un defecto por chequeo; nada toca disco."""
    variantes = {}
    com = archivos["comentarios.csv"].decode().splitlines()
    variantes["id duplicado"] = {**archivos, "comentarios.csv": "\n".join(com + [com[1]]).encode() + b"\n"}
    variantes["columna faltante"] = {**archivos, "comentarios.csv": "\n".join(l.rsplit(",", 1)[0] for l in com).encode() + b"\n"}
    variantes["clave inyectada"] = {**archivos, "costo.json": archivos["costo.json"].replace(b'"notas": "', b'"notas": "sk-ABCDEFGHIJKLMNOPQRSTUV ')}
    cue = archivos["cuentas.csv"].decode().splitlines()
    variantes["cuenta en dos grupos"] = {**archivos, "cuentas.csv": "\n".join(cue + ["u000001,g001", "u000001,g002"]).encode() + b"\n"}
    variantes["archivo faltante"] = {k: v for k, v in archivos.items() if k != "narrativas.csv"}
    return variantes


def main():
    texto_final = (RAIZ / "FINAL_RUN.md").read_text(encoding="utf-8")
    final = manifiesto(texto_final)
    hash_declarado = re.search(r"SHA-256 de `pipeline.py`: `([0-9a-f]{64})`", texto_final).group(1)
    commit_entregado = re.search(r"código de `([0-9a-f]{40})`", texto_final).group(1)
    fuente_main = git("show", "main:pipeline.py")

    if "--romper" in sys.argv:
        base = leer_ref("main")
        for nombre, archivos in romper(base).items():
            print(f"\n== variante rota: {nombre}")
            antes = len(resultados)
            validar_entrega("main(roto)", archivos, fuente_main, final)
            fallo = any(ok is False for _, _, ok in resultados[antes:])
            print(f"   detectada: {'sí' if fallo else 'NO'}")
            if not fallo:
                sys.exit(f"la variante '{nombre}' no fue detectada")
        print("\nTodas las variantes rotas fueron detectadas.")
        return

    for ref in ("main", "origin/main"):
        validar_entrega(ref, leer_ref(ref), git("show", f"{ref}:pipeline.py"), final)

    hash_main = hashlib.sha256(git("show", "main:pipeline.py", binario=True)).hexdigest()
    hash_entregado = hashlib.sha256(git("show", f"{commit_entregado}:pipeline.py", binario=True)).hexdigest()
    registrar(4, "pipeline.py de main = el que generó entrega/", hash_main == hash_declarado,
              f"main {hash_main[:12]}, FINAL_RUN declara {hash_declarado[:12]} ({commit_entregado[:7]}: {hash_entregado[:12]})")

    programa = (RAIZ / "program.md").read_text(encoding="utf-8")
    ref_a = [float(x.replace(",", ".")) for x in re.search(r"A = \*\*([\d,]+) / ([\d,]+) / ([\d,]+)\*\*", programa).groups()]
    ref_b = [float(x.replace(",", ".")) for x in re.search(r"B = \*\*([\d,]+) / ([\d,]+) / ([\d,]+)\*\*", programa).groups()]
    filas = pd.read_csv(RAIZ / "experiments.tsv", sep="\t", dtype={"commit": str})
    candidato = None
    for fila in filas[filas.estado.eq("accepted")].itertuples():
        try:
            if hashlib.sha256(git("show", f"{fila.commit}:pipeline.py", binario=True)).hexdigest() == hash_main:
                candidato = fila
        except subprocess.CalledProcessError:
            continue
    if hash_main == hash_declarado:
        registrar(2, "merge a main respeta la regla", True, "main conserva el código vigente; no hubo merge de código")
    elif candidato is None:
        registrar(2, "merge a main respeta la regla", None, "ninguna fila aceptada tiene el pipeline.py de main")
    else:
        comp = json.loads(candidato.componentes)
        part = ["completo", "dia_1_7", "dia_8_14"]
        a = [comp[p]["narrativas"]["puntos"] for p in part]
        b = [comp[p]["coordinacion"]["puntos"] for p in part]
        supera = a[0] > ref_a[0] or b[0] > ref_b[0]
        perdidas = [f"{t}/{p} {v:.2f}<{r:.2f}" for t, vals, refs in (("A", a, ref_a), ("B", b, ref_b))
                    for p, v, r in zip(part, vals, refs) if v < r]
        registrar(2, f"merge de fila {candidato.id} ({candidato.commit[:7]}) supera a {commit_entregado[:7]} sin perder particiones",
                  supera and not perdidas, f"A {a} vs {ref_a}; B {b} vs {ref_b}; pérdidas {perdidas or 'ninguna'}")
        registrar(2, "entrega/ de main fue regenerada tras el merge", False,
                  f"main tiene código de {candidato.commit[:7]} pero entrega/ es de {commit_entregado[:7]}")

    costo = json.loads(git("show", "main:entrega/costo.json"))
    evidencia = {k: costo[k] for k in costo if re.search(r"cache|cach|embedding|fria|frio", k, re.IGNORECASE)}
    medicion = costo.get("medicion", {})
    registrar(3, "costo.json prueba embeddings desde cero", True if evidencia.get("cache_fria") is True else None,
              f"sin campo de caché en costo.json; medicion.tipo={medicion.get('tipo')!r} "
              f"(pipeline.py:reporte_referencia reutiliza 'segundos' de .cache/reportes si la huella coincide)")
    registrar(3, "costo.json entregado = el del manifiesto", hashlib.sha256(git("show", "main:entrega/costo.json", binario=True)).hexdigest() == final.get("costo.json"), "contra FINAL_RUN.md")

    if "--tests" in sys.argv:
        prueba = subprocess.run([sys.executable, "-m", "unittest", "tests.test_reproducibilidad", "-q"], cwd=RAIZ, capture_output=True, text=True, timeout=120)
        registrar(4, "tests/test_reproducibilidad.py", prueba.returncode == 0, prueba.stderr.strip().splitlines()[-1] if prueba.stderr.strip() else "ok")
    registrar(4, "dos corridas del commit entregado dan archivos idénticos", None,
              "requiere dos corridas de >10 min sobre datos/final; tests/test_reproducibilidad.py sólo cubre reporte_referencia y eval.invoke_pipeline")

    fallas = [n for _, n, ok in resultados if ok is False]
    print(f"\nResumen: {sum(ok is True for *_, ok in resultados)} pasan, {len(fallas)} fallan, {sum(ok is None for *_, ok in resultados)} no verificables")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
