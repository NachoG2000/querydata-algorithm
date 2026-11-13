import argparse, inspect, json, sys, textwrap
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path.cwd()
sys.path.insert(0, str(RAIZ))
import contextlib, io
import pipeline

MUTACIONES = {
    "doble_evento": ('.add((pubs[i],normalizados.iloc[posiciones[i]]))', '.add((pubs[i],normalizados.iloc[posiciones[i]],"sem"))'),
    "peso_uno": ("if veces >= 2", "if veces >= 1"),
    "peso_uno_sem": ("if len(contextos)>=2", "if len(contextos)>=1"),
    "ventana_fija": ("ventana = float(np.expm1(", "ventana = 600.0 or float(np.expm1("),
}


def variante(nombres):
    fuente = textwrap.dedent(inspect.getsource(pipeline.coordinacion))
    for n in nombres:
        viejo, nuevo = MUTACIONES[n]
        assert viejo in fuente, f"mutación {n} ya no aplica: el código cambió"
        fuente = fuente.replace(viejo, nuevo)
    espacio = dict(vars(pipeline))
    exec(compile(fuente, "coordinacion_rota", "exec"), espacio)
    return espacio["coordinacion"]


def datos(escala=1.0, par_doble=True, seed=7):
    rng = np.random.default_rng(seed)
    t0 = pd.Timestamp("2026-11-01T12:00:00Z")
    filas, vec = [], {}
    dim = 64

    def vector(texto):
        if texto not in vec:
            v = rng.normal(size=dim); vec[texto] = v / np.linalg.norm(v)
        return texto

    pubs = [f"p{i:02d}" for i in range(20)]
    grupo = [f"c{i}" for i in range(6)]
    for j, pub in enumerate(pubs[:2]):
        guion = f"el gobierno miente otra vez sobre la represa numero {j} y nadie dice nada"
        for n, c in enumerate(grupo):
            filas.append((pub, c, t0 + pd.Timedelta(hours=j * 5, seconds=0.3 * n + float(rng.uniform(0, 0.3))) * escala, vector(guion)))
    organicos = [f"u{i:02d}" for i in range(40)]
    for i in range(400):
        pub = pubs[rng.integers(0, 20)]
        filas.append((pub, organicos[rng.integers(0, 40)], t0 + pd.Timedelta(seconds=float(rng.uniform(0, 4e5)) * escala), vector(f"opinion libre {i} sobre el tema de hoy en la provincia y el agua")))
    for i in range(60):
        texto = f"muy buena nota gracias por compartir la informacion del dia {i}"
        pub = pubs[i % 20]
        for h in (0, 3 + i % 5):
            filas.append((pub, organicos[(i * 3 + h) % 40], t0 + pd.Timedelta(hours=h + 30, minutes=i, seconds=float(rng.uniform(0, 3000))) * escala, vector(texto)))
    if par_doble:
        texto = "exijo que se investigue ya mismo a los responsables de la obra del dique"
        filas.append(("p15", "x1", t0 + pd.Timedelta(hours=60) * escala, vector(texto)))
        filas.append(("p15", "y1", t0 + pd.Timedelta(hours=60, seconds=0.2) * escala, vector(texto)))
    df = pd.DataFrame(filas, columns=["publicacion_id", "cuenta_id", "fecha", "texto"])
    df.insert(0, "comentario_id", [f"k{i:05d}" for i in range(len(df))])
    textos = list(vec)
    vectores = np.stack([vec[t] for t in textos])
    indices = df.texto.map({t: i for i, t in enumerate(textos)}).to_numpy()
    normalizados = df.texto.map(pipeline.texto_embedding)
    return df, normalizados, vectores, indices


def correr(f, escala=1.0):
    df, normalizados, vectores, indices = datos(escala)
    with contextlib.redirect_stdout(io.StringIO()):
        grupos, rafagas, ventana = f(df, normalizados, vectores, indices)
    return grupos, ventana


def chequeos(f, union):
    res = []
    grupos, ventana = correr(f)
    detectadas = set(grupos)
    res.append(("I1+I2 par que coincide una vez (exacta y paráfrasis a la vez) no se marca", not ({"x1", "y1"} & detectadas), f"x1/y1 marcadas: {sorted({'x1','y1'} & detectadas)}"))
    print(f"[INFO] control (no es invariante): grupo c0..c5 que repite 2 veces; detectadas {sorted(detectadas)}")
    g10, v10 = correr(f, escala=10.0)
    escala_ok = ventana > 0 and 5 <= v10 / ventana <= 20
    res.append(("I3 la ventana escala con la dilatación temporal (x10)", escala_ok, f"ventana {ventana:.1f}s -> {v10:.1f}s"))
    entradas = [grupos, {"c0": "s001", "x9": "s001", "u01": "s002", "u02": "s002"}]
    gu, _, _ = union([(g, pd.DataFrame(columns=pipeline.RAFAGAS), ventana) for g in entradas])
    juntas = all(isinstance(gu, dict) and len({gu.get(c) for c, h in g.items() if h == grupo}) == 1 for g in entradas for grupo in set(g.values()))
    res.append(("I4 unir_detecciones: una operación por cuenta, y cuentas juntas en alguna detección quedan juntas", juntas, f"{gu}"))
    return res


def entrega(cuentas):
    marcadas = cuentas[cuentas.grupo.notna() & cuentas.grupo.astype(str).ne("")]
    por = marcadas.groupby("cuenta_id").grupo.nunique()
    dup = cuentas.cuenta_id.duplicated().sum()
    return ("I4 entrega/cuentas.csv: cada cuenta a lo sumo un grupo", dup == 0 and (por <= 1).all(), f"{len(cuentas)} filas, {dup} cuenta_id repetidos, {len(marcadas)} marcadas en {marcadas.grupo.nunique()} grupos")


def precision(tsv):
    d = pd.read_csv(tsv, sep="\t")
    acept = d[d.estado.eq("accepted")].iloc[-1]
    comp = json.loads(acept.componentes)
    malas = {p: v["coordinacion"]["precision"] for p, v in comp.items() if v["coordinacion"]["cuentas_marcadas"] > 0 and v["coordinacion"]["precision"] < 0.9}
    vistos = {p: round(v["coordinacion"]["precision"], 3) for p, v in comp.items()}
    return ("I5 precisión de cuentas >= 0,9 (última aceptada, fila %d)" % acept.id, not malas, f"{vistos}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--romper", action="store_true")
    a = ap.parse_args()
    cuentas = pd.read_csv(RAIZ / "entrega/cuentas.csv", dtype=str)
    if a.romper:
        casos = {
            "doble_evento (exacta y paráfrasis cuentan como dos contextos)": chequeos(variante(["doble_evento"]), pipeline.unir_detecciones),
            "peso_uno exacto (veces >= 1)": chequeos(variante(["peso_uno"]), pipeline.unir_detecciones),
            "peso_uno semántico (len(contextos) >= 1)": chequeos(variante(["peso_uno_sem"]), pipeline.unir_detecciones),
            "ventana_fija (ventana constante de 600 s)": chequeos(variante(["ventana_fija"]), pipeline.unir_detecciones),
            "cuenta en dos grupos en cuentas.csv": [entrega(pd.concat([cuentas, pd.DataFrame({"cuenta_id": [cuentas.cuenta_id.iloc[0]], "grupo": ["g999"]}), cuentas.assign(grupo="g001").iloc[:1]]))],
            "union que no une (cada detección conserva sus grupos)": chequeos(pipeline.coordinacion, lambda r: ([g for g, _, _ in r], None, None)),
        }
        fallos = 0
        for nombre, res in casos.items():
            caidos = [n for n, ok, _ in res if not ok]
            fallos += bool(caidos)
            print(f"[{'DETECTADA' if caidos else 'NO DETECTADA'}] {nombre}: falla {caidos}")
        sys.exit(0 if fallos == len(casos) else 1)
    res = chequeos(pipeline.coordinacion, pipeline.unir_detecciones) + [entrega(cuentas), precision(RAIZ / "experiments.tsv")]
    for nombre, ok, detalle in res:
        print(f"[{'OK' if ok else 'FALLA'}] {nombre} :: {detalle}")
    sys.exit(0 if all(ok for _, ok, _ in res) else 1)


if __name__ == "__main__":
    main()
