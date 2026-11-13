"""Procesa un lote de QualyData y escribe una entrega reproducible."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
import fcntl
import json
import os
import platform
import importlib.metadata
import re
import unicodedata

PARAMS = {
    "q_longitud_guion": 0.25,
    "q_coseno_guion": 0.975,
    "mezcla_ventana": 0.5,
    "factor_soporte": 0.85,
    "factor_rafaga": 2.0,
    "q_ritmo_publicacion": 0.25,
    "q_demora_guion": 0.5,
    "factor_vecindad_sem": 1.0,
    "q_peso_semantico": 0.5,
    "q_longitud_parafrasis": 0.2,
    "factor_soporte_parafrasis": 1.0,
    "fondo_guiones_largos": False,
    "modelo_coordinacion_base": 'intfloat/multilingual-e5-small',
    "revision_coordinacion_base": '614241f622f53c4eeff9890bdc4f31cfecc418b3',
    "modelo_coordinacion_aux": 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    "revision_coordinacion_aux": 'a3ded7f4d0d725c6fc251504622d65b2516a3aa1',
    "modo_coordinacion": 'union',
    "q_coseno_aux": 0.97,
    "q_coseno_expansion": 0.95,
    "factor_ventana_expansion": 0.25,
    "factor_vecinos_expansion": 2,
    "peso_origen_fusion": 0.25,
    "q_origen_fusion": 0.1,
    "seed": 42,
    "modelo": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "revision": "a3ded7f4d0d725c6fc251504622d65b2516a3aa1",
    "batch_size": 128,
    "hilos": 4,
    "muestra": 10000,
    "n_neighbors": 50,
    "n_components": 5,
    "min_cluster_size": 100,
    "min_samples": 10,
    "min_palabras": 6,
    "percentil_candidata": 0.25,
    "percentil_fusion": 0.5,
    "percentil_nucleo": 0.50,
    "percentil_asignacion": 0.0,
    "percentil_intervalo_guion": 0.5,
    "percentil_ventana": 0.25,
    "percentil_aristas": 0.5,
    "min_palabras_guion": 6,
    "min_cuentas_grupo": 4,
    "min_coincidencias": 2,
    "max_cuentas_rafaga": 64,
    "vecinos_temporales": 12,
    "coseno_guion": 0.9,
    "percentil_estado": 0.25,
    "percentil_amplificada": 0.75,
    "fraccion_jev": 0.01,
    "margen_jev": 0.05,
}

os.environ.setdefault("HF_HOME", str(Path(".cache/huggingface").resolve()))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("NUMBA_NUM_THREADS", str(PARAMS["hilos"]))
os.environ.setdefault("OMP_NUM_THREADS", str(PARAMS["hilos"]))

import duckdb
import networkx as nx
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from threadpoolctl import threadpool_limits

ZONA = "America/Argentina/Salta"
ARCHIVOS = {
    "comentarios": ("comentario_id", "publicacion_id", "cuenta_id", "fecha", "texto", "respuesta_a", "me_gusta"),
    "cuentas": ("cuenta_id", "usuario", "fecha_creacion", "seguidores", "siguiendo"),
    "publicaciones": ("publicacion_id", "fuente_id", "fecha", "titular"),
    "fuentes": ("fuente_id", "nombre", "tipo"),
}
NARRATIVAS = ["narrativa", "titulo", "frases_clave", "fecha_origen"]
ESTADOS = ["narrativa", "dia", "volumen", "apoyo", "rechazo", "fraccion_coordinada", "deriva", "estado", "amplificada"]
RAFAGAS = ["grupo", "publicacion_id", "inicio", "fin", "cuentas"]
ENLACES = re.compile(r"https?://\S+|@\w+", flags=re.IGNORECASE)
ESPACIOS = re.compile(r"\s+")
PALABRAS = re.compile(r"[^\W_]+", flags=re.UNICODE)


@dataclass
class Lote:
    comentarios: pd.DataFrame
    cuentas: pd.DataFrame
    calidad: dict


def ruta_csv(datos, tabla):
    ruta = datos / f"{tabla}.csv"
    return ruta if ruta.is_file() else ruta.with_suffix(".csv.gz")


def cargar(datos, cache):
    rutas = {tabla: ruta_csv(datos, tabla) for tabla in ARCHIVOS}
    firma = sha256(b"parquet-v1")
    for tabla, ruta in rutas.items():
        with ruta.open("rb") as archivo:
            for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
                firma.update(bloque)
        firma.update(tabla.encode())
    almacen = cache / "datos" / firma.hexdigest()
    almacen.parent.mkdir(parents=True, exist_ok=True)
    if not almacen.is_dir():
        with TemporaryDirectory(dir=almacen.parent) as temporal, duckdb.connect() as db:
            db.execute("SET threads = 1")
            for tabla, columnas in ARCHIVOS.items():
                expresiones = {
                    "fecha": "TRY_CAST(fecha AS TIMESTAMPTZ) AS fecha",
                    "fecha_creacion": "TRY_CAST(fecha_creacion AS DATE) AS fecha_creacion",
                    **{campo: f"TRY_CAST({campo} AS BIGINT) AS {campo}" for campo in ("me_gusta", "seguidores", "siguiendo")},
                }
                seleccion = ", ".join(expresiones.get(campo, f"coalesce({campo}, '') AS {campo}") for campo in columnas)
                consulta = f"SELECT {seleccion} FROM read_csv(?, all_varchar = true, sample_size = -1)"
                tabla_arrow = db.execute(consulta, [str(rutas[tabla])]).fetch_arrow_table()
                pq.write_table(tabla_arrow, Path(temporal) / f"{tabla}.parquet", compression="zstd")
            try:
                Path(temporal).rename(almacen)
            except OSError:
                if not almacen.is_dir():
                    raise
    comentarios = pd.read_parquet(almacen / "comentarios.parquet")
    cuentas = pd.read_parquet(almacen / "cuentas.parquet")
    calidad = {
        "fechas_invalidas": int(comentarios.fecha.isna().sum()),
        "textos_vacios": int(comentarios.texto.str.strip().eq("").sum()),
        "comentarios_duplicados": int(comentarios.comentario_id.duplicated().sum()),
        "cuentas_duplicadas": int(cuentas.cuenta_id.duplicated().sum()),
        "comentarios_sin_id": int(comentarios.comentario_id.eq("").sum()),
        "cuentas_sin_id": int(cuentas.cuenta_id.eq("").sum()),
    }
    comentarios = comentarios[comentarios.comentario_id.ne("")].drop_duplicates("comentario_id")
    comentarios = comentarios.sort_values("comentario_id").reset_index(drop=True)
    cuentas = cuentas[cuentas.cuenta_id.ne("")].drop_duplicates("cuenta_id").sort_values("cuenta_id")
    padres = comentarios.respuesta_a.ne("")
    calidad["respuestas_huerfanas"] = int((padres & ~comentarios.respuesta_a.isin(comentarios.comentario_id)).sum())
    return Lote(comentarios, cuentas, calidad)


def texto_embedding(texto):
    limpio = ENLACES.sub(" ", unicodedata.normalize("NFKC", texto).casefold())
    return ESPACIOS.sub(" ", limpio).strip()


def embeddings(comentarios, cache, modelo=None, revision=None):
    textos = comentarios.texto.map(texto_embedding)
    indices, unicos = pd.factorize(textos, sort=True)
    if len(unicos) == 0:
        return np.empty((0, 0), dtype=np.float32), indices
    claves = [sha256(texto.encode()).digest() for texto in unicos]
    modelo = modelo or PARAMS["modelo"]
    revision = revision or PARAMS["revision"]
    huella = sha256(f"{modelo}/{revision}/texto-v1".encode()).hexdigest()[:12]
    nombre = f"{Path(modelo).name}-{huella}"
    carpeta = cache / "embeddings"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{nombre}.parquet"
    with (carpeta / f"{nombre}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        tabla = pq.read_table(ruta) if ruta.exists() else None
        previas = {} if tabla is None else dict(zip(tabla["texto_sha256"].to_pylist(), range(len(tabla))))
        faltantes = [i for i, clave in enumerate(claves) if clave not in previas]
        if faltantes:
            import torch
            from sentence_transformers import SentenceTransformer

            torch.manual_seed(PARAMS["seed"])
            torch.set_num_threads(PARAMS["hilos"])
            try:
                encoder = SentenceTransformer(modelo, revision=revision, device="cpu", local_files_only=True)
            except OSError:
                if os.environ.get("HF_HUB_OFFLINE", "").upper() in {"1", "ON", "YES", "TRUE"}:
                    raise
                encoder = SentenceTransformer(modelo, revision=revision, device="cpu")
            entrada = [unicos[i] for i in faltantes]
            if "e5-" in modelo:
                entrada = [f"passage: {texto}" for texto in entrada]
            nuevos = encoder.encode(entrada, batch_size=PARAMS["batch_size"], normalize_embeddings=True,
                                    show_progress_bar=False)
            dimension = nuevos.shape[1]
            bloque = pa.table({
                "texto_sha256": pa.array([claves[i] for i in faltantes], type=pa.binary(32)),
                "embedding": pa.FixedSizeListArray.from_arrays(pa.array(nuevos.ravel()), dimension),
            })
            inicio = len(previas)
            previas.update((claves[i], inicio + j) for j, i in enumerate(faltantes))
            tabla = bloque if tabla is None else pa.concat_tables([tabla, bloque])
            with TemporaryDirectory(dir=carpeta) as temporal:
                nueva_ruta = Path(temporal) / ruta.name
                pq.write_table(tabla, nueva_ruta, compression="zstd")
                nueva_ruta.replace(ruta)
        posiciones = np.fromiter((previas[clave] for clave in claves), dtype=np.int64)
        vectores = tabla["embedding"].combine_chunks()
        matriz = vectores.values.to_numpy().reshape(-1, vectores.type.list_size)
    return matriz[posiciones], indices


@dataclass
class Candidatas:
    etiquetas: np.ndarray
    centroides: np.ndarray
    pisos: np.ndarray
    similitud: np.ndarray


def asignar_centroide(vectores, centroides):
    etiquetas = np.full(len(vectores), -1, dtype=np.int32)
    similitud = np.zeros(len(vectores), dtype=np.float32)
    margen = np.zeros(len(vectores), dtype=np.float32)
    if len(centroides):
        for inicio in range(0, len(vectores), 4096):
            rango = slice(inicio, inicio + 4096)
            coseno = np.einsum("ij,kj->ik", vectores[rango], centroides)
            mejor = coseno.argmax(axis=1)
            maximos = coseno[np.arange(len(mejor)), mejor]
            etiquetas[rango] = mejor
            similitud[rango] = maximos
            margen[rango] = maximos - np.partition(coseno, -2, axis=1)[:, -2] if len(centroides) > 1 else 1
    return etiquetas, similitud, margen


def agrupar(vectores, aptos, fechas=None):
    import hdbscan
    from umap import UMAP

    rng = np.random.default_rng(PARAMS["seed"])
    indices = np.flatnonzero(aptos)
    if len(indices) < max(PARAMS["min_cluster_size"], PARAMS["n_components"] + 2):
        return Candidatas(np.full(len(vectores), -1), vectores[:0], np.empty(0), np.zeros(len(vectores)))
    if len(indices) > PARAMS["muestra"]:
        indices = np.sort(rng.choice(indices, PARAMS["muestra"], replace=False))
    muestra = vectores[indices]
    reducido = UMAP(n_neighbors=PARAMS["n_neighbors"], n_components=PARAMS["n_components"],
                    metric="cosine", random_state=PARAMS["seed"], n_jobs=1, init="random").fit_transform(muestra)
    modelo = hdbscan.HDBSCAN(min_cluster_size=PARAMS["min_cluster_size"], min_samples=PARAMS["min_samples"],
                            core_dist_n_jobs=1)
    etiquetas = modelo.fit_predict(reducido)
    etiquetas_validas = sorted(set(etiquetas) - {-1})
    if len(etiquetas_validas) > 1:
        from sklearn.cluster import AgglomerativeClustering

        centros_previos = np.asarray([muestra[etiquetas == i].mean(axis=0) for i in etiquetas_validas])
        centros_previos /= np.maximum(np.linalg.norm(centros_previos, axis=1, keepdims=True), 1e-8)
        distancias = np.clip(1 - centros_previos @ centros_previos.T, 0, 2)
        np.fill_diagonal(distancias, np.inf)
        umbral = float(np.quantile(distancias.min(axis=1), PARAMS["percentil_fusion"]))
        if umbral > 0:
            tiempos = fechas.iloc[indices].astype("int64").to_numpy(dtype=np.float64) / 1e9
            validos = fechas.iloc[indices].notna().to_numpy()
            amplitud = np.ptp(tiempos[validos]) if validos.any() else 1.0
            origenes = np.asarray([np.quantile(tiempos[(etiquetas==i) & validos],PARAMS["q_origen_fusion"]) if ((etiquetas==i) & validos).any() else np.median(tiempos[validos]) if validos.any() else 0.0 for i in etiquetas_validas])
            distancias = np.clip(1-centros_previos @ centros_previos.T,0,2)
            distancias += PARAMS["peso_origen_fusion"] * np.abs(origenes[:,None]-origenes[None,:]) / max(amplitud,1.0)
            np.fill_diagonal(distancias,0)
            fusion = AgglomerativeClustering(n_clusters=None, distance_threshold=umbral,
                                            metric="precomputed", linkage="average").fit_predict(distancias)
            nuevas = np.full(len(etiquetas), -1, dtype=np.int32)
            for etiqueta, grupo in zip(etiquetas_validas, fusion):
                nuevas[etiquetas == etiqueta] = grupo
            etiquetas = nuevas
    centros, pisos = [], []
    for etiqueta in sorted(set(etiquetas) - {-1}):
        grupo = muestra[etiquetas == etiqueta]
        centro = grupo.mean(axis=0)
        centro /= max(np.linalg.norm(centro), 1e-8)
        centros.append(centro)
        pisos.append(np.quantile(np.einsum("ij,j->i", grupo, centro), PARAMS["percentil_asignacion"]))
    centroides = np.asarray(centros, dtype=np.float32) if centros else vectores[:0]
    etiquetas, similitud, _ = asignar_centroide(vectores, centroides)
    pisos = np.asarray(pisos)
    if len(centroides):
        etiquetas[~aptos | (similitud < pisos[etiquetas])] = -1
    return Candidatas(etiquetas, centroides, pisos, similitud)


def texto_guion(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"#\w+", " ", texto)
    texto = re.sub(r"(\w)\1{2,}", r"\1", texto)
    return " ".join(PALABRAS.findall(texto))


def coordinacion(comentarios, normalizados, vectores, indices, config=None):
    config = {**PARAMS, **(config or {})}
    from sklearn.mixture import GaussianMixture
    from ejemplos.linea_base import normalize

    eventos = comentarios[["comentario_id", "publicacion_id", "cuenta_id", "fecha"]].assign(norm=comentarios.texto.map(normalize))
    eventos = eventos[eventos.fecha.notna() & eventos.cuenta_id.ne("") & eventos.publicacion_id.ne("")]
    if len(eventos) < 2:
        return {}, pd.DataFrame(columns=RAFAGAS), 0.0
    largo = eventos.norm.str.split().str.len()
    minimo = max(1, int(np.ceil(largo.quantile(config["q_longitud_guion"]))));largos = eventos[largo.ge(minimo)]
    if len(largos) < 2:
        return {}, pd.DataFrame(columns=RAFAGAS), 0.0
    repetidos = largos.sort_values(["publicacion_id", "norm", "fecha"], kind="stable")
    intervalos = repetidos.groupby(["publicacion_id", "norm"]).fecha.diff().dt.total_seconds()
    positivos = intervalos[intervalos.gt(0)].to_numpy()
    rng = np.random.default_rng(config["seed"])
    if len(positivos) >= 2:
        muestra = np.sort(rng.choice(len(positivos), min(len(positivos), config["muestra"]), replace=False))
        mezcla = GaussianMixture(n_components=2, n_init=3, random_state=config["seed"], reg_covar=1e-6).fit(np.log1p(positivos[muestra]).reshape(-1, 1))
        medias = np.sort(mezcla.means_.ravel())
        ventana = float(np.expm1((1 - config["mezcla_ventana"]) * medias[0] + config["mezcla_ventana"] * medias[1]))
    else:
        ventana = float(np.median(positivos)) if len(positivos) else 0.0
    if ventana <= 0:
        return {}, pd.DataFrame(columns=RAFAGAS), 0.0
    poblacion = eventos.cuenta_id.nunique();volumen = largos.groupby("publicacion_id").size()
    soporte = max(2, int(np.ceil(config["factor_soporte"] * np.sqrt(np.log1p(poblacion)))))
    participantes = max(2, int(np.ceil(np.log1p(volumen.mean()) / config["factor_rafaga"])))
    base = eventos.assign(ts=eventos.fecha.dt.as_unit("ns").astype("int64") // 10**9)
    conteo = largos.groupby(["publicacion_id", "norm"]).cuenta_id.transform("nunique")
    candidatas = base.loc[largos.index[conteo.ge(participantes)]]
    enlaces_exactos = Counter()
    for _, datos in candidatas.groupby(["publicacion_id", "norm"], sort=True):
        datos = datos.sort_values("ts", kind="stable")
        miembros = sorted(set(datos.loc[datos.ts.le(datos.ts.iloc[0] + ventana), "cuenta_id"]))
        if len(miembros) >= participantes:
            enlaces_exactos.update(combinations(miembros, 2))
    red_exacta = nx.Graph()
    red_exacta.add_edges_from(par for par, veces in sorted(enlaces_exactos.items()) if veces >= 2)
    exactos = {cuenta:f"e{i:03d}" for i,c in enumerate(sorted(map(sorted,nx.connected_components(red_exacta))),1) if len(c)>=soporte for cuenta in c}
    minimo_parafrasis = max(1, int(np.ceil(largo.quantile(config["q_longitud_parafrasis"]))))
    largos = eventos[largo.ge(minimo_parafrasis)]
    volumen = largos.groupby("publicacion_id").size()
    actividad = eventos.sort_values(["publicacion_id", "fecha", "comentario_id"], kind="stable")
    intervalos = actividad.groupby("publicacion_id").fecha.diff().dt.total_seconds()
    ritmo = intervalos[intervalos.gt(0)].groupby(actividad.publicacion_id).median()
    rapido = float(ritmo.quantile(config["q_ritmo_publicacion"])) if len(ritmo) else 0.0
    repetidos_raw = largos.assign(guion=normalizados.loc[largos.index]).sort_values(["publicacion_id", "guion", "fecha"], kind="stable")
    diferencias = repetidos_raw.groupby(["publicacion_id", "guion"]).fecha.diff().dt.total_seconds()
    positivos_raw = diferencias[diferencias.gt(0)]
    ventana_sem = min(ventana, float(np.sqrt(rapido * positivos_raw.quantile(config["q_demora_guion"])))) if len(positivos_raw) and rapido > 0 else 0.0
    ordenados = largos.sort_values(["publicacion_id", "fecha", "comentario_id"], kind="stable")
    posiciones = ordenados.index.to_numpy();pubs = ordenados.publicacion_id.to_numpy();cuentas = ordenados.cuenta_id.to_numpy()
    tiempos = ordenados.fecha.dt.as_unit("ns").astype("int64").to_numpy() / 1e9
    poblacion_vectores = np.unique(indices[posiciones]) if config["fondo_guiones_largos"] else np.arange(len(vectores))
    cantidad = min(len(poblacion_vectores), config["muestra"])
    a = rng.integers(0, len(poblacion_vectores), cantidad)
    b = (a + rng.integers(1, len(poblacion_vectores), cantidad)) % len(poblacion_vectores) if len(poblacion_vectores)>1 else a
    fondo = np.einsum("ij,ij->i", vectores[poblacion_vectores[a]], vectores[poblacion_vectores[b]])
    q = 1 - (1 - config["q_coseno_guion"]) / max(1.0, float(np.sqrt(volumen.median())))
    piso = float(np.quantile(fondo, q));repeticiones = defaultdict(set)
    vecinos = max(1, int(np.ceil(config["factor_vecindad_sem"] * np.log1p(len(largos)))))
    candidatos_raw = repetidos_raw[repetidos_raw.duplicated(["publicacion_id", "guion"], keep=False)]
    limite_raw = largos.groupby("publicacion_id").cuenta_id.nunique().map(lambda n:max(2,int(np.ceil(np.sqrt(n)))))
    for (publicacion,guion),datos in candidatos_raw.groupby(["publicacion_id","guion"],sort=True):
        inicio = None;miembros=set();episodios=[]
        for cuenta,fecha in datos[["cuenta_id","fecha"]].itertuples(index=False,name=None):
            if inicio is None or (fecha-inicio).total_seconds()>ventana_sem:
                if 2<=len(miembros)<=limite_raw[publicacion]:episodios.append(sorted(miembros))
                inicio=fecha;miembros=set()
            miembros.add(cuenta)
        if 2<=len(miembros)<=limite_raw[publicacion]:episodios.append(sorted(miembros))
        for miembros in episodios:
            for par in combinations(miembros,2):repeticiones[par].add((publicacion,guion))
    if ventana_sem > 0:
        for salto in range(1, min(len(ordenados), vecinos + 1)):
            cercanos = np.flatnonzero((pubs[:-salto] == pubs[salto:]) & (tiempos[salto:] - tiempos[:-salto] <= ventana_sem) & (cuentas[:-salto] != cuentas[salto:]))
            for inicio in range(0, len(cercanos), 4096):
                izq=cercanos[inicio:inicio+4096];der=izq+salto
                similitud=np.einsum("ij,ij->i",vectores[indices[posiciones[izq]]],vectores[indices[posiciones[der]]])
                for i,j in zip(izq[similitud>=piso],der[similitud>=piso]):
                    repeticiones[tuple(sorted((cuentas[i],cuentas[j])))].add((pubs[i],normalizados.iloc[posiciones[i]]))
    pesos = {par:len(contextos) for par,contextos in repeticiones.items() if len(contextos)>=2}
    sem = nx.Graph()
    if pesos:
        corte=float(np.quantile(list(pesos.values()),config["q_peso_semantico"]))
        sem.add_weighted_edges_from((a,b,peso) for (a,b),peso in sorted(pesos.items()) if peso>=corte)
    comunidades = nx.community.louvain_communities(sem, seed=config["seed"]) if sem.number_of_edges() else []
    soporte_parafrasis = max(2, int(np.ceil(config["factor_soporte_parafrasis"] * np.sqrt(np.log1p(poblacion)))))
    semanticos = {cuenta:f"s{i:03d}" for i,c in enumerate(sorted(map(sorted,comunidades)),1) if len(c)>=soporte_parafrasis for cuenta in c}
    union = nx.Graph()
    for mapping in (exactos,semanticos):
        grupos = defaultdict(list)
        for cuenta,grupo in mapping.items():grupos[grupo].append(cuenta)
        for miembros in grupos.values():
            miembros=sorted(miembros);union.add_nodes_from(miembros);union.add_edges_from((miembros[0],x) for x in miembros[1:])
    grupos = {cuenta:f"g{i:03d}" for i,c in enumerate(sorted(map(sorted,nx.connected_components(union))),1) for cuenta in c}
    seleccionados = eventos[eventos.cuenta_id.isin(grupos)].assign(grupo=lambda t:t.cuenta_id.map(grupos))
    filas=[]
    if len(seleccionados):
        seleccionados=seleccionados.assign(bloque=(seleccionados.fecha.dt.as_unit("ns").astype("int64")/1e9//max(ventana,1)).astype("int64"))
        for (grupo,pub,_),datos in seleccionados.groupby(["grupo","publicacion_id","bloque"],sort=True):
            n=datos.cuenta_id.nunique()
            if n>=2:filas.append((grupo,pub,datos.fecha.min(),datos.fecha.max(),n))
    print(json.dumps({"coordinacion_escalada":{"ventana_exacta_s":ventana,"ventana_semantica_s":ventana_sem,"piso_coseno":piso,"soporte_comunidad":soporte,"soporte_parafrasis":soporte_parafrasis,"participantes_rafaga":participantes,"min_palabras_relativo":minimo,"min_palabras_parafrasis":minimo_parafrasis,"cuentas_exactas":len(exactos),"cuentas_semanticas":len(semanticos),"cuentas_union":len(grupos)}},sort_keys=True),flush=True)
    return grupos,pd.DataFrame(filas,columns=RAFAGAS),ventana


def unir_detecciones(resultados):
    grafo = nx.Graph()
    for grupos, _, _ in resultados:
        comunidades = defaultdict(list)
        for cuenta, grupo in grupos.items(): comunidades[grupo].append(cuenta)
        for miembros in comunidades.values():
            miembros = sorted(miembros);grafo.add_nodes_from(miembros)
            grafo.add_edges_from((miembros[0], cuenta) for cuenta in miembros[1:])
    grupos = {cuenta:f"g{i:03d}" for i,c in enumerate(sorted(map(sorted,nx.connected_components(grafo))),1) for cuenta in c}
    tablas=[]
    for anteriores,tabla,_ in resultados:
        if not tabla.empty:
            equivalencia={grupo:grupos[cuenta] for cuenta,grupo in anteriores.items()}
            tablas.append(tabla.assign(grupo=tabla.grupo.map(equivalencia)))
    rafagas=pd.concat(tablas,ignore_index=True).drop_duplicates() if tablas else pd.DataFrame(columns=RAFAGAS)
    if not rafagas.empty:rafagas=rafagas.sort_values(["grupo","publicacion_id","inicio","fin","cuentas"],kind="stable").reset_index(drop=True)
    return grupos,rafagas,max(r[2] for r in resultados)


def ampliar_semillas(comentarios, normalizados, vectores, indices, grupos, rafagas, ventana):
    if not grupos or len(vectores)<2:return grupos,rafagas
    eventos=comentarios[comentarios.fecha.notna() & comentarios.cuenta_id.ne("") & comentarios.publicacion_id.ne("")]
    longitudes=normalizados.loc[eventos.index].str.split().str.len()
    eventos=eventos[longitudes.ge(longitudes.quantile(PARAMS["q_longitud_parafrasis"]))]
    if len(eventos)<2:return grupos,rafagas
    datos=eventos.sort_values(["publicacion_id","fecha","comentario_id"],kind="stable")
    posiciones=datos.index.to_numpy();pubs=datos.publicacion_id.to_numpy();cuentas=datos.cuenta_id.to_numpy()
    tiempos=datos.fecha.dt.as_unit("ns").astype("int64").to_numpy()/1e9
    conocidas=datos.cuenta_id.isin(grupos).to_numpy()
    volumen=eventos.groupby("publicacion_id").size()
    rng=np.random.default_rng(PARAMS["seed"]);n=min(len(vectores),PARAMS.get("muestra_coordinacion",PARAMS["muestra"]))
    a=rng.integers(0,len(vectores),n);b=(a+rng.integers(1,len(vectores),n))%len(vectores)
    fondo=np.einsum("ij,ij->i",vectores[a],vectores[b])
    q=1-(1-PARAMS["q_coseno_expansion"])/max(1.0,float(np.sqrt(volumen.median())))
    piso=float(np.quantile(fondo,q))
    evidencia=defaultdict(set);vecinos=defaultdict(set)
    cantidad=max(1,int(np.ceil(PARAMS["factor_vecindad_sem"]*np.log1p(len(datos)))))
    for salto in range(1,min(len(datos),cantidad+1)):
        candidatos=np.flatnonzero((pubs[:-salto]==pubs[salto:]) & (tiempos[salto:]-tiempos[:-salto]<=ventana*PARAMS["factor_ventana_expansion"]) & (conocidas[:-salto]!=conocidas[salto:]))
        for inicio in range(0,len(candidatos),4096):
            izq=candidatos[inicio:inicio+4096];der=izq+salto
            cosenos=np.einsum("ij,ij->i",vectores[indices[posiciones[izq]]],vectores[indices[posiciones[der]]])
            for i,j in zip(izq[cosenos>=piso],der[cosenos>=piso]):
                semilla,candidata=(i,j) if conocidas[i] else (j,i)
                clave=(cuentas[candidata],grupos[cuentas[semilla]])
                evidencia[clave].add(pubs[i]);vecinos[clave].add(cuentas[semilla])
    tamanos=Counter(grupos.values());propuestas=defaultdict(list)
    for (cuenta,grupo),publicaciones in sorted(evidencia.items()):
        soporte=max(1,int(np.ceil(np.log1p(tamanos[grupo])/PARAMS["factor_vecinos_expansion"])))
        if len(publicaciones)>=2 and len(vecinos[(cuenta,grupo)])>=soporte:
            propuestas[cuenta].append((len(publicaciones),len(vecinos[(cuenta,grupo)]),grupo))
    nuevos=dict(grupos)
    for cuenta,candidatos in sorted(propuestas.items()):
        candidatos=sorted(candidatos,reverse=True)
        if len(candidatos)==1 or candidatos[0][:2]>candidatos[1][:2]:nuevos[cuenta]=candidatos[0][2]
    seleccion=eventos[eventos.cuenta_id.isin(nuevos)].assign(grupo=lambda x:x.cuenta_id.map(nuevos))
    seleccion=seleccion.assign(bloque=(seleccion.fecha.dt.as_unit("ns").astype("int64")/1e9//max(ventana,1)).astype("int64"))
    filas=[]
    for (grupo,pub,_),bloque in seleccion.groupby(["grupo","publicacion_id","bloque"],sort=True):
        n=bloque.cuenta_id.nunique()
        if n>=2:filas.append((grupo,pub,bloque.fecha.min(),bloque.fecha.max(),n))
    return nuevos,pd.DataFrame(filas,columns=RAFAGAS)


def validar_candidatas(comentarios, candidatas, grupos, motor):
    from decisores import DecisionInput

    candidatos = comentarios.assign(grupo=candidatas)
    candidatos = candidatos[candidatos.grupo.ge(0)]
    resumen = candidatos.groupby("grupo").agg(volumen=("grupo", "size"), publicaciones=("publicacion_id", "nunique"),
                                             dias=("fecha", lambda fechas: fechas.dt.tz_convert(ZONA).dt.date.nunique()))
    if resumen.empty:
        return []
    genuinos = candidatos[~candidatos.cuenta_id.isin(grupos) & candidatos.cuenta_id.ne("")]
    cuentas = genuinos.groupby("grupo").cuenta_id.nunique().reindex(resumen.index, fill_value=0)
    tamano = resumen.volumen.quantile(PARAMS["percentil_candidata"])
    validas = resumen[(resumen.volumen >= tamano) & cuentas.ge(2) & (resumen.publicaciones.gt(1) | resumen.dias.gt(1))]
    representantes = (genuinos.sort_values("centralidad", ascending=False, kind="stable")
                       .drop_duplicates("grupo").set_index("grupo").texto)
    solicitudes = [DecisionInput(text=representantes[i], labels=("afirmacion", "reaccion"), kind="claim")
                   for i in validas.index]
    return [i for i, (tipo, _) in zip(validas.index, motor.decide_local(solicitudes)) if tipo == "afirmacion"]


def asignar_y_ruido(vectores, indices, aptos, candidatas, validas):
    etiquetas, similitud, margen = asignar_centroide(vectores, candidatas.centroides[validas])
    if validas:
        etiquetas[~aptos | (similitud < candidatas.pisos[validas][etiquetas])] = -1
    return etiquetas[indices], similitud[indices], margen[indices]


AFIRMACION_CORTA = re.compile(r"^(sí|si|tal cual|exacto|exactamente|así es|asi es|de acuerdo|totalmente|es verdad|es cierto)(\b|$)")
CONTRADICCION = re.compile(r"^(no($|[ ,.!?])|eso es falso\b|mentira\b|nada que ver\b|no es cierto\b|para nada\b)")


def postura(comentarios, etiquetas, centralidad, margen, motor):
    from decisores import DecisionInput

    textos = comentarios.texto.tolist()
    ids = comentarios.comentario_id.tolist()
    posiciones = {identidad: i for i, identidad in enumerate(ids)}
    padres = np.full(len(ids), -1, dtype=np.int64)
    signos = np.ones(len(ids), dtype=np.int8)
    for i, padre in enumerate(comentarios.respuesta_a):
        if not padre or padre not in posiciones or posiciones[padre] == i:
            continue
        limpio = texto_embedding(textos[i])
        corto = len(PALABRAS.findall(limpio)) <= PARAMS["min_palabras"] + 1
        if corto and AFIRMACION_CORTA.match(limpio):
            padres[i] = posiciones[padre]
        elif CONTRADICCION.match(limpio):
            padres[i] = posiciones[padre]
            signos[i] = -1

    raices = np.flatnonzero((padres < 0) & (etiquetas >= 0))
    ejemplos = {}
    for i in raices:
        etiqueta = etiquetas[i]
        if etiqueta not in ejemplos or centralidad[i] > centralidad[ejemplos[etiqueta]]:
            ejemplos[etiqueta] = i

    def solicitud(i):
        referencia = textos[ejemplos[etiquetas[i]]]
        return DecisionInput(text=textos[i], labels=("apoya", "rechaza"), kind="stance", context={"afirmacion": referencia})

    locales = motor.decide_local(map(solicitud, raices))
    orientacion = np.ones(len(ids), dtype=np.int8)
    for i, (etiqueta, _) in zip(raices, locales):
        orientacion[i] = -1 if etiqueta == "rechaza" else 1

    ia = 0
    if motor.mode == "jev":
        dudosos = [(prob, margen[i], i) for i, (_, prob) in zip(raices, locales) if margen[i] <= PARAMS["margen_jev"]]
        limite = int(len(ids) * PARAMS["fraccion_jev"])
        elegidos = [i for _, _, i in sorted(dudosos)[:limite]]
        for i, (etiqueta, _) in zip(elegidos, motor.decide(map(solicitud, elegidos))):
            orientacion[i] = -1 if etiqueta == "rechaza" else 1
        ia = motor.stats.logical_ia

    resuelto = padres < 0
    en_camino = np.zeros(len(ids), dtype=bool)
    ciclos = 0
    for i in np.flatnonzero(~resuelto):
        camino = []
        actual = i
        while not resuelto[actual] and not en_camino[actual]:
            en_camino[actual] = True
            camino.append(actual)
            actual = padres[actual]
        if en_camino[actual]:
            ciclos += 1
            while not resuelto[actual]:
                resuelto[actual] = True
                etiquetas[actual] = -1
                actual = padres[actual]
        for hijo in reversed(camino):
            en_camino[hijo] = False
            if not resuelto[hijo]:
                padre = padres[hijo]
                if etiquetas[padre] >= 0:
                    etiquetas[hijo] = etiquetas[padre]
                    orientacion[hijo] = signos[hijo] * orientacion[padre]
                resuelto[hijo] = True
    return np.where(etiquetas < 0, "", np.where(orientacion > 0, "apoya", "rechaza")), ia, ciclos


def fecha_origen(grupo, minimo):
    nucleo = grupo[grupo.centralidad.ge(grupo.centralidad.quantile(PARAMS["percentil_nucleo"]))]
    origen = nucleo.fecha.min()
    if pd.isna(origen):
        origen = grupo.fecha.min()
    if pd.isna(origen):
        origen = minimo
    return origen.tz_convert(ZONA).isoformat()


def describir(detalles, minimo):
    from sklearn.feature_extraction.text import CountVectorizer

    grupos = list(detalles[detalles.narrativa.ne("ninguna")].groupby("narrativa", sort=True))
    if not grupos:
        return pd.DataFrame(columns=NARRATIVAS)
    textos = [" ".join(grupo.texto) for _, grupo in grupos]
    vectorizador = CountVectorizer(ngram_range=(1, 2), max_features=40000, token_pattern=r"(?u)\b\w+\b")
    cuentas = vectorizador.fit_transform(textos).tocsr()
    terminos = vectorizador.get_feature_names_out()
    frecuencia = np.asarray(cuentas.sum(axis=0)).ravel()
    idf = np.log1p(float(np.mean(np.asarray(cuentas.sum(axis=1)))) / frecuencia)
    filas = []
    for i, (etiqueta, grupo) in enumerate(grupos):
        fila = cuentas.getrow(i)
        mejores = np.lexsort((terminos[fila.indices], -fila.data * idf[fila.indices]))[:6]
        titulo = grupo.sort_values(["centralidad", "comentario_id"], ascending=[False, True]).texto.iloc[0]
        filas.append((etiqueta, " ".join(titulo.split())[:180], "|".join(terminos[fila.indices[mejores]]), fecha_origen(grupo, minimo)))
    return pd.DataFrame(filas, columns=NARRATIVAS)


def estados_por_dia(detalles, vectores, indices, grupos):
    fechados = detalles[detalles.fecha.notna()]
    if fechados.empty:
        return pd.DataFrame(columns=ESTADOS)
    ultimo = fechados.fecha.dt.tz_convert(ZONA).max().normalize()
    asignados = fechados[fechados.narrativa.ne("ninguna")].copy()
    asignados["dia"] = asignados.fecha.dt.tz_convert(ZONA).dt.normalize()
    filas = []
    for narrativa, grupo in asignados.groupby("narrativa", sort=True):
        dias = {dia: datos for dia, datos in grupo.groupby("dia")}
        centro = vectores[indices[grupo.index]].mean(axis=0)
        centro /= max(np.linalg.norm(centro), 1e-8)
        deriva, cuotas = {}, {}
        for dia, datos in dias.items():
            centro_dia = vectores[indices[datos.index]].mean(axis=0)
            deriva[dia] = float(np.clip(1 - np.dot(centro_dia, centro) / max(np.linalg.norm(centro_dia), 1e-8), 0, 2))
            cuotas[dia] = float(datos.cuenta_id.isin(grupos).mean())
        volumen_min = np.quantile([len(datos) for datos in dias.values()], PARAMS["percentil_estado"])
        deriva_max = np.quantile(list(deriva.values()), 1 - PARAMS["percentil_estado"])
        cuota_max = np.quantile(list(cuotas.values()), PARAMS["percentil_amplificada"])
        for dia in pd.date_range(min(dias), ultimo, freq="D"):
            datos = dias.get(dia)
            volumen = len(datos) if datos is not None else 0
            apoyo = float(datos.postura.eq("apoya").mean()) if volumen else 0.0
            rechazo = float(datos.postura.eq("rechaza").mean()) if volumen else 0.0
            distancia, cuota = deriva.get(dia, 0.0), cuotas.get(dia, 0.0)
            amplificada = cuota > 0 and cuota >= cuota_max
            if dia == min(dias):
                estado = "nacida"
            elif volumen == 0 or volumen < volumen_min:
                estado = "latente"
            elif distancia > deriva_max:
                estado = "mutando"
            else:
                estado = "activa"
            filas.append((narrativa, dia.date().isoformat(), volumen, apoyo, rechazo, cuota, distancia, estado, amplificada))
    return pd.DataFrame(filas, columns=ESTADOS)


def escribir_entrega(destino, detalles, narrativas, cuentas, estados, rafagas):
    destino.mkdir(parents=True, exist_ok=True)
    auxiliares = destino if destino.resolve() != Path("entrega").resolve() else Path("salida/final")
    auxiliares.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destino) as temporal:
        borrador = Path(temporal)
        detalles[["comentario_id", "narrativa", "postura"]].to_csv(borrador / "comentarios.csv", index=False)
        narrativas.to_csv(borrador / "narrativas.csv", index=False)
        cuentas.to_csv(borrador / "cuentas.csv", index=False)
        for archivo in sorted(borrador.iterdir()):
            archivo.replace(destino / archivo.name)
    with TemporaryDirectory(dir=auxiliares) as temporal:
        borrador = Path(temporal)
        for nombre, tabla in {"estados": estados, "detalles": detalles, "rafagas": rafagas}.items():
            tabla.to_parquet(borrador / f"{nombre}.parquet", index=False, compression="zstd")
        for archivo in sorted(borrador.iterdir()):
            archivo.replace(auxiliares / archivo.name)
    return auxiliares


def reporte_referencia(datos, cache, costo, metricas):
    """Keep the first measured local report for identical inputs and software.

    Predictions are always recomputed. Only measured durations are reused;
    current-run telemetry is printed separately for the evaluation harness.
    API accounting must always describe fresh calls, so Jev is never reused.
    """
    if metricas["decisor"] != "local":
        return costo, metricas
    firma = sha256(b"reporte-local-v1")
    for tabla in ARCHIVOS:
        firma.update(tabla.encode())
        with ruta_csv(datos, tabla).open("rb") as archivo:
            for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
                firma.update(bloque)
    for nombre in ("pipeline.py", "decisores.py"):
        firma.update(Path(__file__).with_name(nombre).read_bytes())
    software = {nombre: importlib.metadata.version(nombre) for nombre in (
        "numpy", "pandas", "pyarrow", "duckdb", "torch", "sentence-transformers",
        "transformers", "umap-learn", "hdbscan", "networkx", "numba", "scikit-learn",
    )}
    firma.update(json.dumps({"params": metricas["params"], "software": software,
                             "hardware": costo["hardware"], "python": platform.python_version()},
                            sort_keys=True).encode())
    clave = firma.hexdigest()
    carpeta = cache / "reportes"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{clave}.json"
    referencia = {"tipo": "primera_corrida_local", "huella": clave,
                  "tiempos_actuales": "stdout: telemetria"}
    costo = {**costo, "medicion": referencia}
    metricas = {**metricas, "medicion": referencia}
    with (carpeta / f"{clave}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if ruta.exists():
            reporte = json.loads(ruta.read_text(encoding="utf-8"))
            # Reuse durations only, never quality, predictions or accounting.
            costo["segundos"] = reporte["segundos"]
            metricas["segundos"] = reporte["segundos"]
            metricas["etapas"] = reporte["etapas"]
        else:
            with TemporaryDirectory(dir=carpeta) as temporal:
                nueva = Path(temporal) / ruta.name
                nueva.write_text(json.dumps({"segundos": metricas["segundos"],
                                             "etapas": metricas["etapas"]}), encoding="utf-8")
                nueva.replace(ruta)
    return costo, metricas


def ejecutar(datos, destino, cache, decisor):
    from decisores import DecisionEngine, PARAMS as PARAMS_DECISORES

    inicio = anterior = perf_counter()
    etapas = {}

    def medir(etapa):
        nonlocal anterior
        ahora = perf_counter()
        etapas[etapa] = round(ahora - anterior, 3)
        anterior = ahora
        print(f"{etapa}: {etapas[etapa]:.3f} s", flush=True)

    lote = cargar(datos, cache)
    comentarios = lote.comentarios
    medir("cargar")
    vectores, indices = embeddings(comentarios, cache)
    medir("embeddings")
    normalizados = comentarios.texto.map(texto_embedding)
    unicos = normalizados.groupby(indices).first().reindex(np.arange(len(vectores)))
    aptos = np.asarray([len(PALABRAS.findall(t)) >= PARAMS["min_palabras"] for t in unicos], dtype=bool)
    fechas_texto = comentarios.groupby(indices).fecha.min().reindex(np.arange(len(vectores)))
    candidatas = agrupar(vectores, aptos, fechas=fechas_texto)
    medir("agrupar")
    if (PARAMS["modelo_coordinacion_aux"], PARAMS["revision_coordinacion_aux"]) == (PARAMS["modelo"], PARAMS["revision"]):
        vectores_aux, indices_aux = vectores, indices
    else:
        vectores_aux, indices_aux = embeddings(comentarios, cache, PARAMS["modelo_coordinacion_aux"], PARAMS["revision_coordinacion_aux"])
    nueva = coordinacion(comentarios, normalizados, vectores_aux, indices_aux, {"q_coseno_guion": PARAMS["q_coseno_aux"]})
    if PARAMS["modo_coordinacion"] == "union":
        if (PARAMS["modelo_coordinacion_base"], PARAMS["revision_coordinacion_base"]) == (PARAMS["modelo"], PARAMS["revision"]):
            vectores_base, indices_base = vectores, indices
        else:
            vectores_base, indices_base = embeddings(comentarios, cache, PARAMS["modelo_coordinacion_base"], PARAMS["revision_coordinacion_base"])
        deteccion_base = coordinacion(comentarios, normalizados, vectores_base, indices_base)
        grupos, rafagas, ventana = unir_detecciones([deteccion_base, nueva])
    else:
        grupos, rafagas, ventana = nueva
    grupos, rafagas = ampliar_semillas(comentarios, normalizados, vectores_aux, indices_aux, grupos, rafagas, ventana)
    medir("coordinacion")
    with DecisionEngine(mode=decisor, cache_path=cache / "decisores.sqlite3") as motor:
        validas = validar_candidatas(comentarios.assign(centralidad=candidatas.similitud[indices]),
                                     candidatas.etiquetas[indices], grupos, motor)
        etiquetas, similitud, margen = asignar_y_ruido(vectores, indices, aptos, candidatas, validas)
        medir("validar_y_asignar")
        if not comentarios.fecha.notna().any():
            etiquetas[:] = -1
        posturas, ia, ciclos = postura(comentarios, etiquetas, similitud, margen, motor)
        estadisticas = motor.stats.as_dict()
        modo = motor.mode
    detalles = comentarios.assign(
        narrativa=[f"n{label + 1:03d}" if label >= 0 else "ninguna" for label in etiquetas],
        postura=posturas, centralidad=similitud,
    )
    lote.calidad["ciclos_respuesta"] = ciclos
    lote.calidad["candidatas"] = len(candidatas.centroides)
    lote.calidad["narrativas"] = len(validas)
    narrativas = describir(detalles, detalles.fecha.min())
    medir("postura_y_origen")
    cuentas = lote.cuentas[["cuenta_id"]].assign(grupo=lambda tabla: tabla.cuenta_id.map(grupos).fillna(""))
    estados = estados_por_dia(detalles, vectores, indices, grupos)
    medir("estados_por_dia")
    auxiliares = escribir_entrega(destino, detalles, narrativas, cuentas, estados, rafagas)
    medir("escribir_entrega")
    fraccion = ia / max(len(comentarios), 1)
    segundos = round(perf_counter() - inicio, 3)
    costo = {
        "comentarios_procesados": len(comentarios),
        "segundos": segundos,
        "tokens_ia": estadisticas["input_tokens"] + estadisticas["output_tokens"],
        "usd_ia": estadisticas["usd_ia"],
        "usd_por_mil_comentarios": estadisticas["usd_ia"] * 1000 / max(len(comentarios), 1),
        "hardware": f"{platform.system()} {platform.machine()}, CPU, {PARAMS['hilos']} hilos",
        "almacenamiento": "DuckDB local sobre Parquet Zstandard",
        "notas": f"Embeddings locales y decisor {modo}.",
        "fraccion_ia": fraccion,
    }
    metricas = {
        "segundos": segundos, "etapas": etapas, "fraccion_ia": fraccion, "calidad": lote.calidad,
        "ventana_coordinacion_s": ventana, "decisor": modo, "decisiones": estadisticas, "params": {"pipeline": PARAMS, "decisores": PARAMS_DECISORES},
    }
    print("telemetria: " + json.dumps({"segundos": segundos, "etapas": etapas,
                                       "decisiones": estadisticas}, sort_keys=True), flush=True)
    costo, metricas = reporte_referencia(datos, cache, costo, metricas)
    for ruta, valor in ((destino / "costo.json", costo), (auxiliares / "metricas.json", metricas)):
        ruta.write_text(json.dumps(valor, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(lote.calidad, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path("datos/practica"))
    parser.add_argument("--entrega", type=Path, default=Path("salida/practica"))
    parser.add_argument("--cache", type=Path, default=Path(".cache"))
    parser.add_argument("--decisor", choices=("local", "jev"), default="local")
    args = parser.parse_args()
    with threadpool_limits(limits=PARAMS["hilos"]):
        ejecutar(args.datos, args.entrega, args.cache, args.decisor)


if __name__ == "__main__":
    main()
