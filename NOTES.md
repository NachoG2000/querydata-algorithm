# Notas de práctica

Medición de 200.000 comentarios sobre 506 publicaciones, con fechas en Salta. Reproduce las consultas con `python analizar_practica.py`.

| Día de septiembre | Comentarios | Día de septiembre | Comentarios |
|---:|---:|---:|---:|
| 1 | 14.246 | 8 | 5.527 |
| 2 | 20.202 | 9 | 21.077 |
| 3 | 10.984 | 10 | 10.076 |
| 4 | 16.967 | 11 | 17.324 |
| 5 | 15.525 | 12 | 15.090 |
| 6 | 8.588 | 13 | 13.798 |
| 7 | 14.372 | 14 | 16.224 |

Por publicación, mínimo 3, mediana 222, p90 798,5 y máximo 6.793. Las cinco publicaciones de mayor volumen tienen 6.793, 6.542, 3.872, 3.365 y 3.356 comentarios. Hay 28.054 respuestas, el **14,03 %**. La importación no encontró fechas inválidas, textos vacíos, duplicados ni padres faltantes en práctica.

| Medida | p10 | p50 | p90 | p99 |
|---|---:|---:|---:|---:|
| Caracteres | 14 | 65 | 89 | 106 |
| Palabras | 3 | 12 | 17 | 21 |
| Antigüedad de cuenta al inicio, días | 1.027 | 3.213 | 4.797 | 5.122 |
| Seguidores | 12 | 67 | 347 | 1.414 |
| Me gusta | 0 | 2 | 15 | 68 |

Las horas más concurridas en el total fueron 18 h con 15.543 comentarios, 21 h con 15.446 y 19 h con 15.013. El pico en una sola hora fue el 9 de septiembre a las 09 h, con 3.224. El máximo de me gusta fue 1.098.

## Trampas que el pipeline debe distinguir

Una afirmación puede reaparecer con otra redacción o nacer en la mitad del período. Las reacciones breves pueden apoyar o contradecir una afirmación mediante el padre. Las operaciones pueden usar texto idéntico o variantes de un guion. La viralidad y las copias aisladas pueden parecer una ráfaga coordinada. El pipeline no lee `verdad/`. Las ventanas del evaluador usan la verdad exclusivamente para invocar el puntaje oficial.

## Diferencias con el brief

- El [cronograma oficial del commit 8cbe921](https://github.com/qualydata-org/desafio-qualydata/blob/8cbe921b67c1ef5943183de67ecb181e370322f5/README.md) ubica la publicación del set final el jueves 12 a las 17 h y el cierre el viernes 13 a las 13 h, hora de Salta. Los equipos del podio quedan sujetos a reejecución y se admiten diferencias menores con IA.
- La referencia oficial dice alrededor de 17/55. La línea base oficial intacta dio 22,15/55 en dos resultados locales de práctica. Los dos scripts coinciden con el primer commit oficial del desafío y los cambios posteriores afectaron el README. La cifra reproducida es la referencia de este repo.
- La consigna permite entrenar con la verdad de práctica. Este proyecto usa la restricción más estricta del brief y la reserva para evaluación.
- La entrega oficial tiene cuatro archivos. Los Parquet y la telemetría quedan en `salida/final/` al generar `entrega/`.
- Para conciliar los tiempos medidos y los archivos idénticos, el modo local conserva en ambos JSON una medición de referencia real por entrada, código, parámetros y entorno, identificada por `medicion.huella`. Las duraciones se guardan en `.cache/reportes/`; cada ejecución vuelve a calcular todas las predicciones y emite los tiempos actuales en `stdout` (`telemetria`). El evaluador usa estos últimos para la penalización temporal. La comparación byte a byte incluye ambos JSON completos y requiere conservar la caché de referencia. Jev mantiene la contabilidad real de cada corrida, sin reutilizar tiempos.

## Puntos de partida del código

UMAP y HDBSCAN se ajustan sobre una muestra estable de hasta 10.000 textos únicos. La asignación de todos los comentarios usa centroides. La fragmentación resultante se ve en el recall B-cubed de práctica. El grafo exige que un par coincida en publicaciones distintas. Esa condición puede perder operaciones que se concentran en una publicación.

La comparación de guiones convierte fechas a segundos antes de aplicar la ventana. Una corrida preliminar interpretó los enteros de Parquet en la unidad equivocada y produjo un puntaje artificialmente mayor. El TSV de referencia usa la conversión corregida.


## Diagnóstico previo al cambio de protocolo — 13 de noviembre

La optimización se pausó. Se reprodujeron las variantes 23 y 31 en copias aisladas; `pipeline.py` no cambió durante el diagnóstico. La verdad se consultó exclusivamente para esta auditoría solicitada, sin incorporar etiquetas, temas, nombres de campañas ni fechas concretas al predictor. Los archivos originales y el scorer permanecen congelados.

### Cuentas de la línea base y la variante 23

Ambas detectan 35 cuentas, con precisión oficial 1,0 en el completo, pero **no son las mismas**: intersección 18, 17 exclusivas de cada detector, unión 52 (todas verdaderamente coordinadas: recall de la unión 52/115 = 45,22%). La base cubre 31 cuentas de C1 y 4 de C3; la variante 23, 22 de C1 y 13 de C3. Estos IDs se usan sólo para describir la evaluación, nunca como reglas del pipeline.

| Señal entre las cuentas detectadas | Base | Variante 23 |
|---|---:|---:|
| Comentarios de esas cuentas | 251 | 237 |
| Pares de comentarios con texto bruto idéntico, ≤30 min | 33 | 29 |
| Pares con texto normalizado idéntico, ≤30 min | 191 | 152 |
| Pares con coseno ≥0,9, ≤30 min | 253 | 259 |
| De los anteriores, con redacción normalizada diferente | 89 | 120 |
| Pares de cuentas con repetición exacta en ≥2 eventos | 36 | 22 |

La coincidencia literal bruta explica sólo una parte de las ráfagas: normalizar puntuación, tildes y escritura recupera muchas coincidencias; las similitudes altas también encuentran paráfrasis. No se copiaron vocabularios del set. En la base, las demoras de las coincidencias exactas normalizadas tienen mediana 272 s y p90 540 s; en las cuentas de la variante 23, 211,5 s y 519,5 s. La variante 23 usa una ventana estimada de 232,92 s en el completo, mucho más corta que los 1.800 s de la referencia oficial. La base fragmenta sus 35 cuentas en grupos de tamaños 20/6/5/4; la variante 23, en 13/9/8/5. Ambas cubren sólo dos campañas verdaderas y requieren revisar la fragmentación de operaciones.

### Evidencia por partición: días 1–7 no se exime

Definición diagnóstica: cuentas de la misma campaña verdadera, comentarios largos (≥6 palabras como en la base), misma publicación y demora ≤1.800 s. Un evento de un par se identifica por publicación y par de textos normalizados; texto exacto y coseno no crean dos votos para el mismo evento. «Repetido» exige ≥2 eventos distintos. Los 1.800 s y cosenos 0,9/0,7 son controles descriptivos de comparación, no nuevos umbrales de producción. Las coincidencias entre miembros conocidos miden disponibilidad de evidencia, no la precisión de un detector que conoce la verdad.

| Evidencia | Completo | Días 1–7 | Días 8–14 |
|---|---:|---:|---:|
| Comentarios totales | 200000 | 100884 | 99116 |
| Cuentas coordinadas activas | 115 | 114 | 113 |
| Comentarios de cuentas coordinadas | 1065 | 597 | 468 |
| Pares con repetición exacta | 50 | 16 | 11 |
| Cuentas con repetición exacta | 51 | 23 | 19 |
| Pares repetidos con coseno ≥0,9 | 121 | 34 | 39 |
| Cuentas con repetición y coseno ≥0,9 | 76 | 45 | 34 |
| Pares repetidos con coseno ≥0,7 | 640 | 225 | 200 |
| Cuentas con repetición y coseno ≥0,7 | 92 | 74 | 50 |

La primera mitad tiene más comentarios de cuentas coordinadas y más pares con repetición exacta que la segunda; además, con coseno ≥0,9 hay 33 pares repetidos entre publicaciones distintas en la primera y 39 en la segunda. **No hay evidencia para considerarla una partición sin actividad coordinada. Sigue bloqueando B.**

La ventana propia de la variante 23 cae a 210,91 s en la primera mitad y sube a 269,78 s en la segunda. Bajo esas ventanas sólo quedan 3 pares exactos repetidos en cada mitad y 7/17 pares semánticos repetidos (coseno ≥0,9). Aun así hay 13 cuentas con evidencia semántica repetida en la primera. Que la variante 23 detecte cero allí señala una combinación de ventana, selección de vecinos y soporte de comunidad que no generaliza; no justifica desactivar la validación.

La base oficial se volvió a puntuar por mitad: B = **9,44 / 1,60 / 0,39** puntos (completo / primera / segunda). Marca 35 / 4 / 0 cuentas; precisión 1 / 1 / sin predicciones. La variante 23 tenía B = **9,35 / 0,38 / 4,33**, con 35 / 0 / 13 cuentas y precisión 1 / sin predicciones / 1. Debe revaluarse y registrarse con el protocolo nuevo, pero sus resultados previos ya muestran que la primera mitad no satisface el comparador de alta precisión.

### Emergentes: separación antes que fecha de origen

Las predicciones de comentarios de las variantes 23 y 31 son idénticas byte a byte; el cambio de coordinación no resolvió la estructura de sus narrativas. La tabla usa el cluster que captura más comentarios de cada emergente. La pureza se calcula sobre comentarios con narrativa verdadera, excluyendo ruido verdadero.

| ID de evaluación | Captura en cluster dominante | Pureza | Comentarios de narrativas anteriores en el cluster | Error de origen, horas | Diagnóstico |
|---|---:|---:|---:|---:|---|
| L5 | 77.34% | 24.87% | 16662 | -144.74 | Fusionada con narrativas anteriores |
| B4 | 46.27% | 48.00% | 4324 | -229.88 | Fusionada con narrativas anteriores |
| H3 | 70.88% | 91.11% | 7 | 0.00 | Cluster propio; queda fragmentación residual |

L5 cae principalmente en un cluster dominado por L2; B4 es la etiqueta individual más frecuente de su cluster, pero la suma de narrativas anteriores la supera. Adelantar o retrasar `fecha_origen` de esos grupos mezclados no crea una narrativa emergente separada. H3 sí tiene un grupo propio dominante y origen correcto, aunque reparte parte de sus comentarios entre otros grupos. No se usaron los títulos ni el contenido de estas etiquetas para crear reglas.

### Precisión y decisión de protocolo

La variante 31 no es una referencia admisible para B con precisión ≥0,9: marca 892 cuentas, 89 verdaderas y 803 falsas (precisión 9,98%, recall 77,39%). En las mitades su precisión es 21,36% / 18,43%. Su B-cubed de operaciones alto compensaba la mala detección dentro del puntaje combinado oficial. Hay que conservar ambos componentes visibles y aplicar el piso de precisión por separado. También se debe evitar contar una misma coincidencia como dos eventos por haber pasado por la vía exacta y la semántica con normalizaciones distintas.

Referencias del protocolo nuevo: A conserva 13,13 / 11,46 / 17,20 puntos de narrativas; B se contrasta con la base oficial de alta precisión 9,44 / 1,60 / 0,39. Esto reinicia el comparador por tarea bajo una exigencia nueva; no reescribe los resultados históricos. Los tiempos se comparan con el mismo pipeline de A y caché, no contra el TF-IDF más rápido de la base.

Archivos de auditoría local: `.cache/diagnostico/coordinacion.json`, `evidencia.json`, `narrativas.json` y `salida/diagnostico/`. Las copias aisladas reproducen la variante 23 archivada y el commit `c7cc601` (variante 31). SHA-256 de `pipeline.py` durante todo el diagnóstico: `620a824d40fa2aa03a6018d03c48afa61577eb720bbf00ad47b8fcb3189c63d6`.
