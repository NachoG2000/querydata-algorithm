# Resultados de setup

## Verificación de la sección 7 en Linux

Criterios de `SETUP_PROMPT.md` verificados sobre los 200.000 comentarios de práctica, con Python 3.12.14, dependencias fijadas y PyTorch 2.8.0 CPU, Linux x86_64 y cuatro hilos. El código verificado es `9b7bd59`. Esta sesión completa el setup; no cambia parámetros ni optimiza el puntaje.

La línea base oficial intacta dio **21,96/55** en dos corridas: 12,52 puntos de narrativas y 9,44 de coordinación, con todos los componentes iguales. Ambos scripts coinciden byte a byte con el upstream fijado en `8cbe921`. El primer pipeline dio **9,40/55** (6,86 + 2,54), **12,56 puntos menos** que la línea base en esta máquina. Las mediciones anteriores de macOS se conservan abajo como referencia histórica; los puntajes cambian entre plataformas y no deben compararse como una mejora de código.

`python eval.py` imprimió las tres particiones y agregó el experimento 2 a `experiments.tsv`. El arnés completo tardó **130.074 s**, con caché de embeddings caliente. La fila se aceptó como referencia inicial de Linux para el loop nocturno, sin ajuste del algoritmo.

| Partición | Puntaje / 55 | Métrica combinada | Pipeline actual, s |
|---|---:|---:|---:|
| Completo | 9.40 | 9.356490 | 43.510 |
| Días 1–7 | 8.84 | 8.803111 | 36.889 |
| Días 8–14 | 11.87 | 11.833448 | 36.552 |

La primera corrida completa tardó **611,298 s**, de los cuales **567,763 s** fueron embeddings. La segunda tardó **42,225 s**. Los ocho archivos resultaron idénticos por SHA-256, incluso usando otra semilla de hash de Python en la segunda ejecución. No se excluyeron campos de los JSON. Los JSON conservan las duraciones reales de referencia en `.cache/reportes/`; cada corrida emite sus tiempos actuales en `telemetria` y el evaluador penaliza estos últimos. Borrar la caché de reportes crea otra referencia. Esta garantía byte a byte corresponde al modo local con el mismo software y caché; Jev conserva la contabilidad real de cada ejecución.

| Archivo | SHA-256 de ambas corridas |
|---|---|
| `comentarios.csv` | `f3ca8b76a77c7b157d3acd45ea636d79b7edc01096ae36638733fda95ea81987` |
| `costo.json` | `71f9d9d3295321c845638ab084f9cb60eab6368649abefc87743dcb5572324d2` |
| `cuentas.csv` | `fdbb523f946af8c17ea0592524ebaa729dffda37141d93f29de2dd36dd10f252` |
| `detalles.parquet` | `26f7d9b24abeb7b849dc8c44a3e290d14b0575e4b23e99b2f1533503a506421d` |
| `estados.parquet` | `030fcda91c040f48aa5e9fb432427ee373c266d040c5375f14758720b9aa286b` |
| `metricas.json` | `58c5cf5b07605d1e63b35e88b7fd4652914079efbf9d52479913585a5716dfa3` |
| `narrativas.csv` | `7851986d7c4d1bd346becc25ac81dba34fa1c224477dd91377c74e9af540e9cc` |
| `rafagas.parquet` | `7da0baf6809a7b448cdacb9eb52773dbb30868fd5f35484d5de68c2be2f1d1e8` |

Se verificaron columnas, IDs únicos, cobertura de los 200.000 comentarios y 15.991 cuentas, posturas de los comentarios asignados, fechas de origen con zona horaria y lectura de los tres Parquet. Como la línea base oficial, el ruido deja la postura vacía. El modo local completó el procesamiento sin claves, con cero tokens y USD 0 de IA. Las tres pruebas de `python -m unittest discover -s tests -v` pasaron: referencia e invalidación, contabilidad de API y penalización con tiempos actuales.

`python export_vault.py` generó **109 notas** y se comprobaron **3.866 enlaces internos** con destino. Se abrió `vault/` como carpeta existente en **Obsidian 1.15.1**, con sandbox habilitado, y se verificó visualmente `index.md` con su tabla de narrativas renderizada. `program.md`, `NOTES.md`, `PREGUNTAS.md`, README y el prompt completo están versionados.

Con caché caliente, UMAP/HDBSCAN sigue siendo el cuello de botella: 33.813 s del pipeline completo. Para la noche, precalcular los embeddings de cada modelo antes de medir y comparar sobre este mismo entorno. Los riesgos para el set final son la fragmentación de narrativas (recall B-cubed 0.072), el origen emergente sin aciertos en esta corrida, la baja detección de coordinación y la demora de la primera inferencia. NLI opcional y Jev con clave siguen sin validación real; el camino local está verificado.

## Referencia histórica de macOS

Práctica contiene 200.000 comentarios y 15.991 cuentas. Los archivos y la verdad coinciden byte a byte con el clon oficial. La línea base oficial intacta completó su procesamiento en 6,2 s y dio 22,15/55. La corrida local del setup dio **10,47/55**, una diferencia de −11,68 puntos. Los parámetros quedaron como punto de partida del agente nocturno.

| Métrica automática | Línea base | Setup completo | Días 1–7 | Días 8–14 |
|---|---:|---:|---:|---:|
| B-cubed F1 de narrativas | 0,351 | 0,117 | 0,119 | 0,132 |
| F1 de ruido | 0,665 | 0,572 | 0,562 | 0,583 |
| Macro-F1 de postura | 0,491 | 0,351 | 0,376 | 0,370 |
| Origen emergente | 0,333 | 0,333 | 0,500 | 1,000 |
| Narrativas, puntos de 30 | 12,71 | 7,93 | 8,83 | 11,33 |
| F1 de cuentas coordinadas | 0,467 | 0,122 | 0,067 | 0,000 |
| B-cubed F1 de operaciones | 0,169 | 0,055 | 0,052 | 0,052 |
| Coordinación, puntos de 25 | 9,44 | 2,54 | 1,56 | 0,39 |
| **Total de 55** | **22,15** | **10,47** | **10,39** | **11,72** |

El recall B-cubed del setup fue 0,063, con precisión de 0,914. El recall de cuentas coordinadas fue 0,078 en el set completo. Estos son los puntos débiles medidos para la siguiente sesión.

## Evaluación nocturna

Una corrida del arnés con caché caliente tardó **63,19 s** de pared e incluyó la preparación de las dos ventanas y los tres puntajes oficiales.

| Lote | Métrica combinada | Pipeline, s | Agrupamiento, s |
|---|---:|---:|---:|
| Completo | 10.449 | 20.71 | 15.85 |
| Días 1–7 | 10.371 | 18.64 | 16.02 |
| Días 8–14 | 11.703 | 17.25 | 14.68 |

UMAP y HDBSCAN dominaron el tiempo con caché caliente. En el set completo, la etapa de agrupamiento tomó 15,85 s de 20,72 s. La lectura de los embeddings tomó 0,87 s. La primera corrida con textos nuevos vuelve a pagar la inferencia local.

## Repetibilidad

Dos corridas en la misma máquina produjeron tres CSV y tres Parquet idénticos byte a byte. Los JSON coincidieron al excluir los campos de duración. Una corrida pidió Jev sin clave y verificó la caída a modo local. Una muestra de datos sucios verificó texto vacío, fecha inválida, ID duplicado, padre ausente y ciclo de respuestas. Jev pasó una prueba HTTP simulada de autenticación fallida, deduplicación, caché y contabilización. NLI local y Jev con clave quedan pendientes de una prueba real. El exportador generó 106 notas y se comprobó que los 3.757 enlaces internos tienen destino. La apertura en la app de Obsidian quedó pendiente porque su selector mantuvo deshabilitado el botón Abrir.

## Costo y tiempos

El equipo usado para las mediciones fue macOS arm64, CPU con cuatro hilos para el pipeline. El primer cálculo, con los pesos ya disponibles, generó 95.270 embeddings en 174,83 s. La caché de embeddings quedó en 133 MiB. Los CSV se convirtieron a Parquet tipado en 2,81 s en esa primera corrida.

| Factor | Comentarios | Preparación de réplica | Pipeline de pared | USD de IA |
|---:|---:|---:|---:|---:|
| 1 | 200.000 | 1,24 s | 20,65 s | 0 |
| 5 | 1.000.000 | Pendiente | Pendiente | Pendiente |
| 20 | 4.000.000 | Pendiente | Pendiente | Pendiente |

La corrida local registró 0 tokens, USD 0 por mil comentarios y 0 % de comentarios procesados por API. La curva en `salida/escala/resultados.tsv` usa caché de embeddings caliente y separa el tiempo de crear la réplica. Cada factor de escala publicado aquí corresponde a una sola medición.
