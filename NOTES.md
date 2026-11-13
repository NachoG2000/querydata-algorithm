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

### Reevaluación de la variante 23 con el protocolo por tarea

Experimento 34, repetición exacta del código archivado de la variante 23, sin claves. `python eval.py` completó las tres particiones en **153,194 s**.

| Partición | A oficial / 30 | B oficial / 25 | Precisión B | Tiempo pipeline, s |
|---|---:|---:|---:|---:|
| completo | 13.13 | 9.35 | 1.000 | 50.739 |
| dia_1_7 | 11.46 | 0.38 | 0.000 | 44.425 |
| dia_8_14 | 17.20 | 4.33 | 1.000 | 44.319 |

**Descartada**: B completo 9,35 < 9,44 y días 1–7 0,38 < 1,60. La mejora de días 8–14 a 4,33 no compensa esas pérdidas. La primera mitad conserva su veto por la evidencia descrita arriba. El tiempo completo 50,739 s no supera el límite del 30% frente al mismo pipeline de A en la referencia 31 (54,685 s); no decide este rechazo. A no cambió. La fila 34 permanece en `experiments.tsv` y se restauró el código de trabajo previo; la siguiente fase debe establecer B de alta precisión con umbrales normalizados por exposición.

### Estado al cierre del bucle por tarea

límite de las 07:00 de Argentina del 13/11/2026; 139 filas. Última hipótesis aceptada: 137. La reevaluación de la variante 23 sigue registrada como descartada en la fila 34. La tabla final de puntajes y tiempos está en `RESULTS.md`.

Auditoría de separación sobre la configuración final, sólo con IDs, bandera de emergente y fechas de la verdad; no se leyeron descripciones ni se incorporaron etiquetas al predictor. «Propio» exige mayoría estricta de la narrativa emergente entre los comentarios con narrativa verdadera del cluster dominante; es un diagnóstico, no una métrica de aceptación sustitutiva.

| ID de evaluación | Captura | Pureza | Cluster propio | Error de origen, h |
|---|---:|---:|---|---:|
| L5 | 89.52% | 40.56% | No | -144.74 |
| B4 | 47.39% | 49.37% | No | -229.88 |
| H3 | 70.42% | 99.24% | Sí | 0.00 |

Queda separación pendiente antes de ajustar `fecha_origen`. Las mejoras del completo que perdían puntos en una mitad se descartaron; corregir una fecha de un cluster mezclado no sustituye separar la narrativa. Se mantiene el orden del backlog de `program.md`.

## Diagnóstico de narrativas para mejora A

Medición del código congelado en `c7406f3`, con las predicciones idénticas publicadas en `8a1f5be`. No se cambió `pipeline.py`. La verdad se leyó sólo como IDs y etiquetas para medir, sin descripciones ni vocabulario. El conjunto de B-cubed es exactamente el del scorer oficial: comentarios con narrativa verdadera; las predicciones vacías cuentan como singletons.

B-cubed oficial: precisión **0.594190**, recall **0.307583**, F1 **0.405340**. La pérdida de recall (0.692417) supera la de precisión (0.405810): domina la **fragmentación** global, aunque sigue habiendo fusión, especialmente en emergentes. No se infiere esto sólo del número de clusters; se pondera cada comentario como el scorer.

### Fragmentación por narrativa verdadera

| ID de evaluación | Comentarios | Clusters asignados | Predichos ruido | Captura dominante | P B-cubed | R B-cubed | Fragmentos efectivos |
|---|---:|---:|---:|---:|---:|---:|---:|
| B1 | 15608 | 17 | 1465 | 0.2248 | 0.5856 | 0.1333 | 7.50 |
| B2 | 16605 | 14 | 1604 | 0.5955 | 0.7059 | 0.3809 | 2.63 |
| B3 | 11848 | 14 | 1143 | 0.7039 | 0.7592 | 0.5119 | 1.95 |
| B4 | 8626 | 10 | 389 | 0.4739 | 0.4213 | 0.3085 | 3.24 |
| H1 | 16474 | 18 | 2094 | 0.2861 | 0.5690 | 0.1374 | 7.28 |
| H2 | 14501 | 18 | 1220 | 0.6678 | 0.7220 | 0.4654 | 2.15 |
| H3 | 3513 | 11 | 195 | 0.7042 | 0.7607 | 0.5216 | 1.92 |
| H4 | 12538 | 11 | 1508 | 0.2519 | 0.5668 | 0.1472 | 6.79 |
| L1 | 18463 | 9 | 1023 | 0.6464 | 0.7112 | 0.4591 | 2.18 |
| L2 | 16163 | 13 | 1178 | 0.3613 | 0.4153 | 0.1835 | 5.45 |
| L3 | 9462 | 14 | 1798 | 0.1944 | 0.3359 | 0.0878 | 11.39 |
| L4 | 11331 | 13 | 1648 | 0.3366 | 0.6586 | 0.1827 | 5.47 |
| L5 | 7158 | 9 | 221 | 0.8952 | 0.3959 | 0.8035 | 1.24 |

Los clusters asignados excluyen «ninguna»; los fragmentos efectivos son `1 / recall B-cubed` de esa narrativa y sí incluyen el efecto de predicciones vacías como singletons.

### Fusión por cluster predicho

| Cluster | Comentarios | Narrativas verdaderas distintas | Dominante | Pureza sin ruido | Fracción ruido verdadero |
|---|---:|---:|---|---:|---:|
| n001 | 15856 | 13 | L5 | 0.4056 | 0.0036 |
| n002 | 13252 | 3 | L1 | 0.9006 | 0.0000 |
| n003 | 12373 | 4 | H2 | 0.8358 | 0.0635 |
| n004 | 3314 | 5 | B1 | 0.5202 | 0.0000 |
| n005 | 2494 | 4 | H3 | 0.9924 | 0.0004 |
| n006 | 10462 | 12 | B4 | 0.4937 | 0.2085 |
| n007 | 4747 | 6 | H1 | 0.9930 | 0.0000 |
| n008 | 3940 | 5 | H4 | 0.8015 | 0.0000 |
| n009 | 3077 | 4 | H2 | 0.5876 | 0.0000 |
| n010 | 2374 | 7 | H1 | 0.6057 | 0.0000 |
| n011 | 11448 | 6 | B2 | 0.8638 | 0.0000 |
| n012 | 9349 | 5 | B3 | 0.8921 | 0.0000 |
| n013 | 6450 | 11 | B1 | 0.3955 | 0.0000 |
| n014 | 9086 | 7 | L2 | 0.6426 | 0.0000 |
| n015 | 3523 | 4 | B1 | 0.9960 | 0.0000 |
| n016 | 5582 | 5 | B2 | 0.2807 | 0.0000 |
| n017 | 3961 | 13 | L4 | 0.6105 | 0.0000 |
| n018 | 4549 | 9 | H4 | 0.5489 | 0.0000 |
| n019 | 3694 | 6 | H4 | 0.5998 | 0.3032 |
| n020 | 5623 | 7 | L4 | 0.9631 | 0.2957 |
| n021 | 7283 | 10 | B2 | 0.3639 | 0.4876 |
| n022 | 3202 | 7 | H1 | 0.4804 | 0.0781 |
| n023 | 5467 | 13 | B4 | 0.3867 | 0.0000 |
| n024 | 5307 | 5 | B1 | 0.5101 | 0.0000 |

La composición completa por IDs y las contribuciones ponderadas a la pérdida de precisión y recall están en `.cache/mejora-a/diagnostico-narrativas.json`. Estos IDs no se usan en producción.

### Postura verdadera y predicha

La comparación usa sólo comentarios con narrativa verdadera, como el macro-F1 oficial. Una postura vacía sigue contando como error de recall.

| Clase | Verdad | Predicción |
|---|---:|---:|
| apoya | 85197 | 138157 |
| rechaza | 77093 | 8647 |
| vacía | 0 | 15486 |

Entre las posturas no vacías, **94.11%** son «apoya». Macro-F1 oficial de postura: **0.446124**. El sesgo de clase se mide condicionado a posturas emitidas, sin ocultar las vacías de la tabla.

### Raíces y respuestas

Una respuesta tiene un padre existente, distinto de sí misma; lo restante se trata como raíz para este diagnóstico, igual que el camino de respaldo. Se informa la fracción sobre todos los comentarios y el macro-F1 sólo sobre narrativas verdaderas.

| Grupo | Comentarios totales | Fracción del set | Comentarios con narrativa verdadera | Macro-F1 postura | F1 apoya | F1 rechaza |
|---|---:|---:|---:|---:|---:|---:|
| raices | 171946 | 0.8597 | 134236 | 0.452016 | 0.703063 | 0.200969 |
| respuestas | 28054 | 0.1403 | 28054 | 0.414917 | 0.632183 | 0.197651 |

### Referencia nueva de diez días

El código exacto de `c7406f3`, con la única extensión del arnés, produjo A = 13.37 / 11.58 / 17.25 / 12.91 y B = 19.79 / 5.63 / 12.14 / 9.64 (completo / días 1–7 / días 8–14 / días 1–10). La precisión B fue 0.9091 / 1.0000 / 1.0000 / 1.0000. La nueva partición bloquea la aceptación igual que las mitades. La referencia fue medida en un worktree detached del commit original, sin claves.

### Hipótesis A: NLI local multilingüe para postura

Se probó una muestra aleatoria estructural (1.000 raíces y 1.000 respuestas, semilla 42, selección sin etiquetas). La primera formulación genérica de apoyo/rechazo no superó el método actual: no se incorpora por el mero hecho de usar un modelo. Cinco pares de hipótesis lingüísticas genéricas se compararon en la misma muestra; el mejor exploratorio obtuvo macro-F1 0,508945 con «Este texto afirma que algo es verdad» / «Este texto niega que algo sea verdad» y corte 0,35. Es selección exploratoria y no una estimación independiente de generalización. Sólo se aceptará con los puntajes oficiales en las cuatro ventanas.

El candidato conserva las señales locales de rechazo y usa NLI adicional en raíces; en respuestas, NLI compara texto padre e hijo y sólo añade una relación cuando su probabilidad supera 0,65 y el enlace pasa el filtro temático vigente. Se fijan modelo y revisión públicos; los logits se guardan por modelo, tokenización y textos, sin verdad. La preparación de caché se informa por separado; el arnés compara corridas preparadas. El cierre final debe medir también la corrida realmente fría.

La preparación NLI completa deduplicó las entradas y tardó 1.127,880 s para 428.054 pares lógicos (200.000 comentarios). Se informa aparte del arnés caliente; no se confunde ese costo de preparación con el tiempo de ejecución preparada. Experimento 140 aceptado: A = 13,88 / 12,21 / 17,76 / 13,49; B conserva 19,79 / 5,63 / 12,14 / 9,64. Completo 72,670 s, frente a 71,377 s de la referencia. La entrega final se regenerará con caché vacía durante el cierre, si el candidato sigue admisible.

Hipótesis A 141: Calibrate root NLI while preserving existing reply relations. Se mide con puntaje oficial en cuatro ventanas y se restaura el código anterior si no pasa.
Resultado 141: {"id": "141", "task": "A", "A": {"completo": 13.64, "dia_1_7": 11.94, "dia_8_14": 17.53, "dia_1_10": 13.28}, "B": {"completo": 19.79, "dia_1_7": 5.63, "dia_8_14": 12.14, "dia_1_10": 9.64}, "precision_B": {"completo": 0.9090909090909091, "dia_1_7": 1.0, "dia_8_14": 1.0, "dia_1_10": 1.0}, "seconds": 72.778, "accepted": false, "reasons": ["A pierde en alguna ventana", "no mejora estricta del completo en la tarea"], "summary": "Calibrate root NLI while preserving existing reply relations"}

Hipótesis A 142: Increase multilingual NLI root rejection recall. Se mide con puntaje oficial en cuatro ventanas y se restaura el código anterior si no pasa.
Resultado 142: {"id": "142", "task": "A", "A": {"completo": 13.65, "dia_1_7": 11.95, "dia_8_14": 17.5, "dia_1_10": 13.2}, "B": {"completo": 19.79, "dia_1_7": 5.63, "dia_8_14": 12.14, "dia_1_10": 9.64}, "precision_B": {"completo": 0.9090909090909091, "dia_1_7": 1.0, "dia_8_14": 1.0, "dia_1_10": 1.0}, "seconds": 77.993, "accepted": false, "reasons": ["A pierde en alguna ventana", "no mejora estricta del completo en la tarea"], "summary": "Increase multilingual NLI root rejection recall"}

Hipótesis A 143: Require stronger NLI evidence for root rejection. Se mide con puntaje oficial en cuatro ventanas y se restaura el código anterior si no pasa.
Resultado 143: {"id": "143", "task": "A", "A": {"completo": 13.96, "dia_1_7": 12.28, "dia_8_14": 17.85, "dia_1_10": 13.57}, "B": {"completo": 19.79, "dia_1_7": 5.63, "dia_8_14": 12.14, "dia_1_10": 9.64}, "precision_B": {"completo": 0.9090909090909091, "dia_1_7": 1.0, "dia_8_14": 1.0, "dia_1_10": 1.0}, "seconds": 72.26, "accepted": true, "reasons": [], "summary": "Require stronger NLI evidence for root rejection"}

Hipótesis A 144: Use only confident NLI parent relations. Se mide con puntaje oficial en cuatro ventanas y se restaura el código anterior si no pasa.
Resultado 144: {"id": "144", "task": "A", "A": {"completo": 13.85, "dia_1_7": 12.16, "dia_8_14": 17.75, "dia_1_10": 13.48}, "B": {"completo": 19.79, "dia_1_7": 5.63, "dia_8_14": 12.14, "dia_1_10": 9.64}, "precision_B": {"completo": 0.9090909090909091, "dia_1_7": 1.0, "dia_8_14": 1.0, "dia_1_10": 1.0}, "seconds": 76.856, "accepted": false, "reasons": ["A pierde en alguna ventana", "no mejora estricta del completo en la tarea"], "summary": "Use only confident NLI parent relations"}

Hipótesis A 145: Recover parent relations at lower calibrated NLI confidence. Se mide con puntaje oficial en cuatro ventanas y se restaura el código anterior si no pasa.
