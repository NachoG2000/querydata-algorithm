"""Resume el set de práctica con DuckDB, a partir de los Parquet tipados."""

import argparse
from pathlib import Path

import duckdb

from pipeline import cargar

CONSULTAS = {
    "Comentarios por día local": "SELECT CAST(fecha AS DATE) dia, count(*) comentarios FROM comentarios GROUP BY dia ORDER BY dia",
    "Comentarios por publicación": """SELECT count(*) publicaciones, min(n) minimo, quantile_cont(n, [.1,.5,.9]) p10_p50_p90,
        max(n) maximo FROM (SELECT count(*) n FROM comentarios GROUP BY publicacion_id)""",
    "Publicaciones con más comentarios": "SELECT publicacion_id, count(*) n FROM comentarios GROUP BY 1 ORDER BY n DESC, 1 LIMIT 5",
    "Longitud de comentarios y respuestas": """SELECT count(*) n, count_if(respuesta_a <> '') respuestas,
        round(100.0 * count_if(respuesta_a <> '') / count(*), 2) pct_respuestas,
        quantile_cont(length(texto), [.1,.5,.9,.99]) caracteres,
        quantile_cont(CASE WHEN trim(texto) = '' THEN 0 ELSE array_length(regexp_split_to_array(trim(texto), '\\s+')) END, [.1,.5,.9,.99]) palabras
        FROM comentarios""",
    "Antigüedad en días al inicio de la conversación y seguidores": """SELECT
        quantile_cont(date_diff('day', fecha_creacion, (SELECT min(fecha)::DATE FROM comentarios)), [.1,.5,.9,.99]) antiguedad,
        quantile_cont(seguidores, [.1,.5,.9,.99]) seguidores FROM cuentas""",
    "Me gusta": "SELECT quantile_cont(me_gusta, [.1,.5,.9,.99]) me_gusta, max(me_gusta) maximo FROM comentarios",
    "Horas locales de mayor volumen acumulado": "SELECT hour(fecha) hora, count(*) n FROM comentarios GROUP BY 1 ORDER BY n DESC, 1 LIMIT 5",
    "Picos por fecha y hora": "SELECT date_trunc('hour', fecha) hora, count(*) n FROM comentarios GROUP BY 1 ORDER BY n DESC, 1 LIMIT 5",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", type=Path, default=Path("datos/practica"))
    args = parser.parse_args()
    lote = cargar(args.datos, Path(".cache"))
    with duckdb.connect() as db:
        db.execute("SET TimeZone = 'America/Argentina/Salta'")
        db.register("comentarios", lote.comentarios)
        db.register("cuentas", lote.cuentas)
        for titulo, consulta in CONSULTAS.items():
            print(titulo)
            print(db.sql(consulta).df().to_string(index=False))
    print(lote.calidad)


if __name__ == "__main__":
    main()
