# Invariantes 2.1 y 2.2 contra el código

Contraste de cada invariante de `docs/contexto.md` (secciones 2.1 y 2.2) con `pipeline.py` en el commit `60c4a68`. Los ids reales salen de `entrega/` y del lote final (`datos/final/comentarios.csv.gz`, 150.000 comentarios, los mismos ids que `entrega/comentarios.csv`). `estados.parquet` sale de la corrida `de7ebd0`; `pipeline.py` no cambió entre ese commit y `60c4a68`.

Chequeos que lo reproducen: `.claude/skills/verificar-narrativa/` y `.claude/skills/verificar-comentario/`.

El pipeline es por lotes. No hay una narrativa que viva y cambie de estado: `agrupar` y `validar_candidatas` deciden de una vez qué grupos nacen, y `estados_por_dia` pone una etiqueta a cada día. `suelto` y `candidata` no se guardan en ninguna salida.

## 2.1 Ciclo de vida de una narrativa

| Invariante | Veredicto | Dónde | Ejemplo |
|---|---|---|---|
| Transiciones `nacida → activa`, `activa ⇄ mutando`, `activa ⇄ latente` | No se cumple | `pipeline.py:estados_por_dia`, 669-676 | Cada día se clasifica sin mirar el anterior. En `estados.parquet` hay 34 transiciones fuera de 2.1, p. ej. n004 `nacida → mutando` (2026-10-06), n002 `mutando → latente` (2026-10-08) y `latente → mutando` (2026-10-12). Mínimo sintético: un día con 1 comentario entre días de 6 da `nacida → latente`. TLC lo encuentra en 3 pasos. |
| `fecha_origen` = más antiguo del núcleo, nunca posterior a un comentario del núcleo | Se cumple dentro de la función, con una salvedad | `pipeline.py:fecha_origen`, 611-618; `describir`, 621 | Toma el mínimo del núcleo (centralidad ≥ mediana), así que nunca es posterior. Las 28 fechas de `narrativas.csv` coinciden con un comentario de su narrativa. Salvedad 1: si todo el núcleo no tiene fecha, cae al mínimo del grupo entero, borde incluido (615-616). Salvedad 2: `centralidad` es la similitud con el centroide más cercano (`asignar_y_ruido`), no con el de la narrativa final. Una respuesta que heredó narrativa por `respuesta_a` puede entrar al núcleo con una centralidad medida contra otro centroide. Hay 5 narrativas cuyo origen es una respuesta (n004 `c0000690`, n008 `c0000587`, n012 `c0000440`, n015 `c0000877`, n021 `c0000008`); en 4 la narrativa difiere de la del padre, así que no heredaron. No se observó el caso de forma concluyente. |
| Revive desde `latente` con el mismo id | Se cumple por construcción (lote) | `estados_por_dia`, 652-677 | El id es la etiqueta del cluster. `latente` es solo una etiqueta del día, así que volver a `activa` no puede crear un id nuevo. TLC: `ConservaId` se cumple. |
| Muta con el mismo id, sin partirse | No verificable en lote | `agrupar`, 249-300 | `mutando` también es una etiqueta del día y conserva el id. Que HDBSCAN no parta una narrativa que derivó requiere etiquetas de verdad. |
| Sub-grupo días después con centroide distinto = emergente propia | No se cumple según la evaluación; no verificable sin etiquetas | `agrupar`, 266-283; `asignar_y_ruido`, 504-508 | La fusión suma una penalización por distancia de origen (`peso_origen_fusion`), pero después cada comentario va al centroide más cercano sin mirar la fecha. `contexto.md` §4 registra que dos de tres emergentes quedan fusionadas. |
| Ninguna candidata nace solo con apoyo de cuentas coordinadas | Se cumple | `validar_candidatas`, 493-496 | Exige 2 o más cuentas fuera de `grupos`. Sintético: una candidata con 5 cuentas coordinadas no nace y otra con 3 genuinas sí. Matiz: tamaño (filtro 2) y persistencia (filtro 4) cuentan también los comentarios coordinados, así que 2 cuentas genuinas más cientos de comentarios coordinados alcanzan. |
| Los cuatro filtros de nacimiento | Se cumple | `validar_candidatas`, 484-501 | Afirmación (decisor), tamaño relativo (cuantil 0,25), cuentas genuinas, más de una publicación o más de un día. |
| `amplificada` puede valer desde el nacimiento | Se cumple | `estados_por_dia`, 668 | Se calcula también el día `nacida`. Sintético: día 1 con 100 % de cuentas coordinadas da `nacida` + `amplificada`. |

## 2.2 Recorrido de un comentario

| Invariante | Veredicto | Dónde | Ejemplo |
|---|---|---|---|
| Exactamente una narrativa o `ninguna` | Se cumple | `postura`, 515-608; `ejecutar`, 800-801 | Una fila por comentario. Los 150.000 ids de entrada están una vez en la entrega, cada narrativa existe en `narrativas.csv` y la postura está vacía exactamente cuando la narrativa es `ninguna`. Los comentarios sin id o duplicados se descartan en `cargar` (159), así que no reciben fila. |
| Respuesta que acompaña hereda narrativa y postura | Se cumple cuando la arista se acepta | `postura`, 543-556, 600-606 | 1.161 respuestas reales de hasta 4 palabras tipo "así es" con padre asignado: las 1.161 heredan. Sintético: "Tal cual" y un nieto "Así es" bajo una contradicción heredan bien. |
| Respuesta que contradice: misma narrativa y postura opuesta | No se cumple en respuestas largas | `postura`, 543-544 | La regex `CONTRADICCION` y el NLI se consultan solo si la arista es "afín" (misma etiqueta, coseno ≥ cuantil 0,5 o respuesta corta). Una refutación larga a otra narrativa queda como raíz propia. De 249 respuestas reales que empiezan negando a un padre con narrativa, 42 no cumplen. Ejemplos: `c0006584` "No es zona liberada, detuvieron a dos…" responde a `c0006509` "zona liberada total…" (n012 apoya) y queda n025 apoya. `c0000440` "zona liberada total…" (n012 apoya) responde a `c0000423` "…no es zona liberada…" (n003 apoya). La regex es una aproximación: hay que leer cada id. |
| `ninguna` no propaga postura a los hijos | Se cumple | `postura`, 604 | El hijo conserva su etiqueta propia. Sintético: `h_n` (etiqueta propia n002) bajo `n0` (`ninguna`) queda n002. |
| Ciclos y padres inexistentes se detectan y no rompen | Se cumple | `postura`, 523, 584-598 | Los padres inexistentes y las autorrespuestas no generan arista (523). Un ciclo se detecta y todos sus miembros quedan en `ninguna`, aunque tuvieran narrativa propia. Sintético: a↔b con "Tal cual"/"Exacto": `ciclos=1`, ambos `ninguna`, sin error; `hu` con padre `zzz` se trata como raíz. TLC: sin deadlock. Los datos reales no tienen huérfanas ni ciclos. |
| (Pasos de 2.2) postura por arista en respuestas, por decisor en raíces | No se cumple | `postura`, 558, 570, 604-606 | Una respuesta con narrativa propia cuyo padre es `ninguna` (o fue miembro de un ciclo) no es raíz para el decisor ni hereda: queda con `orientacion = 1`, o sea `apoya`, sin que nadie lo decida. Sintético: `h_n` "Tal cual, es falso que haya obra" sale `apoya` aunque el decisor diría `rechaza`. TLC: `PosturaConOrigen` se rompe en 2 pasos (se corta un ciclo, el hijo de un miembro toma `apoya` por defecto). |

## Resumen de violaciones

1. `estados_por_dia` produce transiciones fuera de la máquina de 2.1 (34 en la corrida final).
2. Las respuestas largas que contradicen a otra narrativa no se ligan al padre: quedan en otra narrativa con `apoya` (42 de 249 candidatas reales).
3. Las respuestas con narrativa propia bajo un padre `ninguna` o un ciclo reciben `apoya` por defecto, sin decisor ni arista.
4. Emergentes fusionadas con narrativas anteriores (según la evaluación; sin verificación formal).
