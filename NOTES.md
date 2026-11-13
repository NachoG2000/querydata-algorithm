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
