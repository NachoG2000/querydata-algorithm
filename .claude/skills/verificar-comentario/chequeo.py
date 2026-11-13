"""Chequea las invariantes 2.2 (recorrido de un comentario) contra pipeline.postura y la entrega."""

import argparse
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
ROTURAS = {
    "contradiccion-sin-signo": ("padres[i]=p;signos[i]=-1", "padres[i]=p;signos[i]=1"),
    "ninguna-propaga": ("                if etiquetas[padre] >= 0:", "                if True:"),
    "sin-deteccion-ciclos": ("        if en_camino[actual]:", "        if False:"),
}
CONOCIDOS = {"I6", "E4"}


def cargar_pipeline(rotura):
    fuente = (RAIZ / "pipeline.py").read_text(encoding="utf-8")
    if rotura:
        viejo, nuevo = ROTURAS[rotura]
        assert fuente.count(viejo) == 1, f"la rotura {rotura} ya no aplica: actualizar ROTURAS"
        fuente = fuente.replace(viejo, nuevo)
    sys.path.insert(0, str(RAIZ))
    modulo = types.ModuleType("pipeline_verificado")
    modulo.__file__ = str(RAIZ / "pipeline.py")
    exec(compile(fuente, modulo.__file__, "exec"), modulo.__dict__)
    modulo.PARAMS["nli_local"] = False
    return modulo


class Motor:
    mode = "local"

    def decide_local(self, solicitudes):
        salida = []
        for s in solicitudes:
            if s.kind == "relation":
                salida.append(("independiente", 0.5))
            else:
                salida.append(("rechaza" if "falso" in s.text.lower() else "apoya", 0.9))
        return salida


def sintetico(pipeline):
    filas = [
        ("r1", "", "El intendente se robó la plata de la obra", 0),
        ("h_ac", "r1", "Tal cual", 1),
        ("h_co", "r1", "Mentira", 1),
        ("nieto", "h_co", "Así es", 0),
        ("n0", "", "jajaja", -1),
        ("h_n", "n0", "Tal cual, es falso que haya obra", 1),
        ("a", "b", "Tal cual", 0),
        ("b", "a", "Exacto", 0),
        ("c", "a", "Tal cual", 0),
        ("hu", "zzz", "La plata de la obra desapareció", 0),
    ]
    comentarios = pd.DataFrame(filas, columns=["comentario_id", "respuesta_a", "texto", "etiqueta"])
    etiquetas = comentarios.etiqueta.to_numpy().astype(np.int64)
    n = len(filas)
    vectores = np.ones((n, 4), dtype=np.float32) / 2
    error = None
    try:
        posturas, _, ciclos = pipeline.postura(comentarios, etiquetas, np.linspace(0.5, 0.9, n), np.ones(n),
                                               Motor(), vectores, np.arange(n), None)
    except Exception as e:
        error, posturas, ciclos = repr(e), [""] * n, -1
    salida = comentarios.assign(narrativa=[f"n{e + 1:03d}" if e >= 0 else "ninguna" for e in etiquetas],
                                postura=posturas).set_index("comentario_id")
    return salida, ciclos, error


def resultados_sinteticos(pipeline):
    s, ciclos, error = sintetico(pipeline)
    nar, pos = s.narrativa, s.postura
    yield "I1", "cada comentario termina con exactamente una narrativa o ninguna", (
        error is None and len(s) == 10 and all((p == "") == (x == "ninguna") for x, p in zip(nar, pos))), f"error={error}"
    yield "I2", "la respuesta que acompaña hereda narrativa y postura", (
        nar["h_ac"] == nar["r1"] and pos["h_ac"] == pos["r1"] and nar["nieto"] == nar["h_co"] and pos["nieto"] == pos["h_co"]), (
        f"r1={nar['r1']}/{pos['r1']} h_ac={nar['h_ac']}/{pos['h_ac']} h_co={nar['h_co']}/{pos['h_co']} nieto={nar['nieto']}/{pos['nieto']}")
    yield "I3", "la respuesta que contradice tiene la misma narrativa y postura opuesta", (
        nar["h_co"] == nar["r1"] and {pos["h_co"], pos["r1"]} == {"apoya", "rechaza"}), f"r1={nar['r1']}/{pos['r1']} h_co={nar['h_co']}/{pos['h_co']}"
    yield "I4", "un padre con narrativa ninguna no propaga a sus hijos", (
        nar["h_n"] == "n002"), f"n0={nar['n0']} h_n={nar['h_n']}/{pos['h_n']} (etiqueta propia n002)"
    yield "I5", "ciclos y padres inexistentes se detectan y no rompen", (
        error is None and ciclos == 1 and nar["a"] == nar["b"] == "ninguna" and nar["hu"] == "n001" and pos["hu"] == "apoya"), (
        f"ciclos={ciclos} a={nar['a']} b={nar['b']} c={nar['c']} hu={nar['hu']}/{pos['hu']} error={error}")
    yield "I6", "toda postura de un comentario con narrativa sale de una arista o del decisor (Pasos de 2.2)", (
        pos["h_n"] == "rechaza"), f"h_n={nar['h_n']}/{pos['h_n']}; el decisor diría rechaza, padre n0 es ninguna"


def resultados_entrega(pipeline, datos):
    entrega = pd.read_csv(RAIZ / "entrega/comentarios.csv", dtype=str, keep_default_na=False)
    narrativas = set(pd.read_csv(RAIZ / "entrega/narrativas.csv", dtype=str).narrativa) | {"ninguna"}
    malos = entrega[~entrega.narrativa.isin(narrativas) | (entrega.postura.eq("") != entrega.narrativa.eq("ninguna"))
                    | entrega.comentario_id.duplicated(keep=False)]
    yield "E1", "entrega: id único, narrativa existente o ninguna, postura vacía solo si ninguna", malos.empty, (
        f"{len(entrega)} filas, {len(malos)} malas {malos.comentario_id.head(3).tolist()}")
    if not datos:
        return
    entrada = pd.read_csv(Path(datos) / "comentarios.csv.gz", dtype=str, keep_default_na=False)
    yield "E2", "entrega cubre exactamente los comentarios de entrada", set(entrada.comentario_id) == set(entrega.comentario_id), (
        f"entrada={entrada.comentario_id.nunique()} entrega={len(entrega)}")
    d = entrada.merge(entrega, on="comentario_id").set_index("comentario_id")
    r = d[d.respuesta_a.isin(d.index)].copy()
    r["pn"], r["pp"] = d.loc[r.respuesta_a, "narrativa"].values, d.loc[r.respuesta_a, "postura"].values
    limpio = r.texto.map(pipeline.texto_embedding)
    contra = r[limpio.map(lambda t: bool(pipeline.CONTRADICCION.match(t))) & r.pn.ne("ninguna")]
    corta = limpio.map(lambda t: len(pipeline.PALABRAS.findall(t)) <= 4)
    acomp = r[corta & limpio.map(lambda t: bool(pipeline.AFIRMACION_CORTA.match(t)) and not pipeline.CONTRADICCION.match(t)) & r.pn.ne("ninguna")]
    malos = acomp[(acomp.narrativa != acomp.pn) | (acomp.postura != acomp.pp)]
    yield "E3", "entrega: respuestas de hasta 4 palabras que acompañan (tal cual, así es) heredan narrativa y postura del padre", malos.empty, (
        f"{len(acomp)} respuestas, {len(malos)} no heredan, ej. {list(zip(malos.index[:3], malos.respuesta_a[:3]))}")
    malos = contra[(contra.narrativa != contra.pn) | (contra.postura == contra.pp)]
    yield "E4", "entrega: respuestas que niegan tienen misma narrativa y postura opuesta", malos.empty, (
        f"{len(contra)} respuestas, {len(malos)} no cumplen, ej. {list(zip(malos.index[:3], malos.respuesta_a[:3]))}")
    huerfanas = (d.respuesta_a.ne("") & ~d.respuesta_a.isin(d.index)).sum()
    yield "E5", "entrega: datos reales sin padres inexistentes ni autorrespuestas (si hay, ver I5)", True, (
        f"huérfanas={huerfanas} autorrespuestas={(d.respuesta_a == d.index).sum()}")


def main():
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--romper", choices=sorted(ROTURAS))
    argumentos.add_argument("--datos", help="carpeta con comentarios.csv.gz del lote que produjo entrega/")
    opciones = argumentos.parse_args()
    pipeline = cargar_pipeline(opciones.romper)
    fallas_nuevas = 0
    for codigo, regla, ok, detalle in [*resultados_sinteticos(pipeline), *resultados_entrega(pipeline, opciones.datos)]:
        marca = "PASA " if ok else ("HALLAZGO" if codigo in CONOCIDOS else "FALLA")
        fallas_nuevas += (not ok) and codigo not in CONOCIDOS
        print(f"{marca:8} {codigo} {regla}\n         {detalle}")
    print(f"rotura={opciones.romper or 'ninguna'} fallas_nuevas={fallas_nuevas}")
    sys.exit(1 if fallas_nuevas else 0)


if __name__ == "__main__":
    main()
