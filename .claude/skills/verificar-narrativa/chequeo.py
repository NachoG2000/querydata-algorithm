"""Chequea las invariantes 2.1 (ciclo de vida de una narrativa) contra pipeline.py y la entrega."""

import argparse
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
ROTURAS = {
    "origen-maximo": ("    origen = nucleo.fecha.min()", "    origen = nucleo.fecha.max()"),
    "cuenta-coordinadas": ("genuinos = candidatos[~candidatos.cuenta_id.isin(grupos) & ", "genuinos = candidatos["),
    "amplificada-tarde": ("            amplificada = cuota > 0 and cuota >= cuota_max",
                          "            amplificada = cuota > 0 and cuota >= cuota_max and dia != min(dias)"),
}
CONOCIDOS = {"N3"}
PERMITIDAS = {("nacida", "activa"), ("activa", "mutando"), ("mutando", "activa"), ("activa", "latente"),
              ("latente", "activa"), ("activa", "activa"), ("mutando", "mutando"), ("latente", "latente")}


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
    return modulo


class Motor:
    mode = "local"

    def decide_local(self, solicitudes):
        return [("afirmacion", 0.9) for _ in solicitudes]


def fecha(dia, hora=12):
    return pd.Timestamp(f"2026-10-{dia:02d} {hora:02d}:00", tz="America/Argentina/Salta")


def transiciones(estados):
    for narrativa, filas in estados.sort_values(["narrativa", "dia"]).groupby("narrativa"):
        lista = filas.estado.tolist()
        yield narrativa, "nacida" if lista[0] == "nacida" else f"empieza en {lista[0]}", filas.dia.iloc[0]
        for (a, b), dia in zip(zip(lista, lista[1:]), filas.dia.iloc[1:]):
            yield narrativa, (a, b), dia


def resultados_sinteticos(pipeline):
    grupo = pd.DataFrame({"centralidad": [0.95, 0.90, 0.85, 0.40, 0.30],
                          "fecha": [fecha(5), fecha(3), fecha(4), fecha(1), fecha(2)]})
    nucleo = grupo[grupo.centralidad.ge(grupo.centralidad.quantile(pipeline.PARAMS["percentil_nucleo"]))]
    origen = pd.Timestamp(pipeline.fecha_origen(grupo, fecha(1)))
    yield "N1", "fecha_origen es el comentario más antiguo del núcleo y nunca posterior a él", (
        origen == nucleo.fecha.min() and (origen <= nucleo.fecha).all()), (
        f"origen={origen.isoformat()} núcleo={sorted(f.isoformat() for f in nucleo.fecha)} (el borde arranca el día 1)")

    filas = [(f"c{g}{k}", f"p{k % 2}", cuenta, fecha(1 + k), "El intendente se robó la plata de la obra", g, 0.9)
             for g, cuentas in ((0, ["u1", "u2", "u3", "u4", "u5"]), (1, ["u6", "u7", "u8", "u6", "u7"]))
             for k, cuenta in enumerate(cuentas)]
    comentarios = pd.DataFrame(filas, columns=["comentario_id", "publicacion_id", "cuenta_id", "fecha", "texto", "grupo", "centralidad"])
    coordinadas = {f"u{i}": "g001" for i in range(1, 6)}
    validas = pipeline.validar_candidatas(comentarios, comentarios.grupo.to_numpy(), coordinadas, Motor())
    yield "N2", "ninguna candidata nace solo con apoyo de cuentas coordinadas", (0 not in validas and 1 in validas), (
        f"nacen={validas}; candidata 0 = 5 cuentas coordinadas, candidata 1 = 3 cuentas genuinas")

    dias = [1] * 6 + [2] + [3] * 6 + [4] * 6
    detalles = pd.DataFrame({"narrativa": "n001", "fecha": [fecha(d) for d in dias], "postura": "apoya",
                             "cuenta_id": ["u1", "u2"] * 3 + ["u9"] + [f"u{i}" for i in range(10, 22)]})
    vectores = np.tile(np.array([[1.0, 0.0]], dtype=np.float32), (len(dias), 1))
    estados = pipeline.estados_por_dia(detalles, vectores, np.arange(len(dias)), {"u1": "g001", "u2": "g001"})
    pasos = [paso for _, paso, _ in transiciones(estados)][1:]
    yield "N3", "cada cambio diario de estado es una transición de 2.1 (nacida→activa, activa⇄mutando, activa⇄latente)", (
        all(p in PERMITIDAS for p in pasos)), f"secuencia={estados.estado.tolist()}"
    yield "N4", "amplificada puede valer desde el nacimiento", bool(estados.amplificada.iloc[0]), (
        f"día de nacimiento: estado={estados.estado.iloc[0]} amplificada={estados.amplificada.iloc[0]} (100% cuentas coordinadas)")
    yield "N5", "la narrativa conserva su identificador en todos sus días (revive o muta sin id nuevo)", (
        estados.narrativa.nunique() == 1), f"ids={sorted(estados.narrativa.unique())}"


def resultados_entrega(estados_ruta, datos):
    narrativas = pd.read_csv(RAIZ / "entrega/narrativas.csv", dtype=str, keep_default_na=False)
    if datos:
        entrada = pd.read_csv(Path(datos) / "comentarios.csv.gz", dtype=str, keep_default_na=False, usecols=["comentario_id", "fecha"])
        entrega = pd.read_csv(RAIZ / "entrega/comentarios.csv", dtype=str, keep_default_na=False).merge(entrada, on="comentario_id")
        entrega["fecha"] = pd.to_datetime(entrega.fecha, utc=True, errors="coerce")
        origenes = pd.to_datetime(narrativas.set_index("narrativa").fecha_origen, utc=True)
        malas = [n for n, g in entrega[entrega.narrativa.ne("ninguna")].groupby("narrativa") if origenes[n] not in set(g.fecha)]
        yield "E1", "entrega: fecha_origen es la fecha de un comentario de esa narrativa", not malas, (
            f"{len(origenes)} narrativas, sin comentario en esa fecha: {malas}")
    if estados_ruta:
        estados = pd.read_parquet(estados_ruta)
        malos = [(n, p, d) for n, p, d in transiciones(estados) if p != "nacida" and p not in PERMITIDAS]
        yield "E2", "estados.parquet: solo transiciones de 2.1", not malos, (
            f"{len(malos)} transiciones fuera de 2.1, ej. {malos[:3]}")


def main():
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--romper", choices=sorted(ROTURAS))
    argumentos.add_argument("--datos", help="carpeta con comentarios.csv.gz del lote que produjo entrega/")
    argumentos.add_argument("--estados", help="estados.parquet de una corrida (salida/final/estados.parquet)")
    opciones = argumentos.parse_args()
    pipeline = cargar_pipeline(opciones.romper)
    fallas_nuevas = 0
    for codigo, regla, ok, detalle in [*resultados_sinteticos(pipeline), *resultados_entrega(opciones.estados, opciones.datos)]:
        marca = "PASA " if ok else ("HALLAZGO" if codigo in CONOCIDOS | {"E2"} else "FALLA")
        fallas_nuevas += (not ok) and codigo not in CONOCIDOS | {"E2"}
        print(f"{marca:8} {codigo} {regla}\n         {detalle}")
    print(f"rotura={opciones.romper or 'ninguna'} fallas_nuevas={fallas_nuevas}")
    sys.exit(1 if fallas_nuevas else 0)


if __name__ == "__main__":
    main()
