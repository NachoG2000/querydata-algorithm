# Resultados de setup

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
