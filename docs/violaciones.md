# Violaciones de invariantes

Invariantes de [`docs/contexto.md`](contexto.md) §2 que el código de `main` en `60c4a68` no cumple. No se arreglaron. Quedan como insumo para el loop de optimización. El detalle de cada una, con archivo, función, línea y ejemplo, está en tres informes:

- [`violaciones/narrativa-comentario.md`](violaciones/narrativa-comentario.md) cubre §2.1 y §2.2. Lo chequean las skills `verificar-narrativa` y `verificar-comentario`.
- [`violaciones/coordinacion-loop-entrega.md`](violaciones/coordinacion-loop-entrega.md) cubre §2.3, §2.4 y §2.5. Lo chequean las skills `verificar-coordinacion`, `verificar-loop` y `verificar-entrega`.
- [`violaciones/statecharts.md`](violaciones/statecharts.md) lista las reglas que se rompen en los [statecharts](statecharts/README.md).

## Resumen

| # | Subsistema | Invariante | Dónde | Ejemplo |
|---|---|---|---|---|
| 1 | Narrativa §2.1 | Solo las transiciones permitidas entre estados | `pipeline.py` `estados_por_dia` (l. 669-676) | Clasifica cada día sin mirar el anterior. En la corrida final hay 34 transiciones prohibidas, como n004 nacida → mutando. |
| 2 | Narrativa §2.1 | Una emergente no se fusiona con una narrativa anterior | Agrupamiento | Dos de tres emergentes de práctica quedan fusionadas (evaluación registrada, no chequeo formal). |
| 3 | Comentario §2.2 | Una respuesta que contradice tiene la misma narrativa y la postura opuesta | `pipeline.py` l. 543 | La arista solo se evalúa si el padre es "afín". `c0006584`, que responde a `c0006509`, queda en otra narrativa con `apoya`. Pasa en 42 de 249 candidatas. |
| 4 | Comentario §2.2 | La postura sale del padre o del decisor, nunca de un valor por defecto | `pipeline.py` l. 558, 570, 604-606 | Si el padre es `ninguna` o estaba en un ciclo cortado, el hijo recibe `apoya` por defecto. |
| 5 | Loop §2.4 | Una aceptada no empeora ninguna partición | `eval.py` `main` (l. 216) | La regla solo está escrita en `program.md`. La fila 2 bajó A en días 1–7 de 8,83 a 7,28. La fila 46 bajó B en días 8–14 de 9,13 a 2,18. |
| 6 | Loop §2.4 | El loop solo edita `pipeline.py` y `PARAMS` de `decisores.py` | Commits de las filas 2 y 140 | También tocan `eval.py`, tests, `requirements.txt` y `entrega/`. Una parte estaba autorizada en `program.md`. |
| 7 | Loop §2.4 | Toda corrida queda registrada | `eval.py` `invoke_pipeline` | Una corrida que falla lanza el error antes de `append_experiment`. Un `git reset --hard` borra una fila que todavía no se commiteó. |
| 8 | Entrega §2.5 | `main` contiene una `entrega/` reproducible con su código | `pipeline.py` de `main` vs `c7406f3` | Los hashes son `8381e041…` y `37c85259…`. Correr `main` no reproduce la `entrega/` publicada (`FINAL_RUN.md`). |
| 9 | Entrega §2.5 | La corrida final calcula embeddings desde cero | `pipeline.py` `embeddings`, `reporte_referencia` | No es verificable. Nada lo registra, y la caché `.cache/embeddings` y los tiempos de `.cache/reportes/` se reutilizan. |
| 10 | Jurado (statechart) | Re-ejecutar da un `costo.json` idéntico | `pipeline.py` `reporte_referencia` | Los tiempos se leen de `.cache/reportes/`, que no está en git, así que la máquina del jurado escribe los suyos. |
| 11 | Demo (statechart) | La nota de una narrativa muestra la amplificación | `export_vault.py` | Sin `salida/final/`, que no se versiona, la narrativa lista una operación pero muestra `dias_amplificada: 0` y `estado_actual: "desconocido"`. |

## Lo que se cumple

- `fecha_origen` nunca es posterior al núcleo, y las 28 fechas del set final coinciden con un comentario de su narrativa.
- Ninguna narrativa nace solo con cuentas coordinadas. El identificador se conserva al revivir.
- Cada comentario termina con exactamente una narrativa o `ninguna`. Las respuestas cortas que acompañan heredan. `ninguna` no propaga. Ciclos y padres inexistentes no rompen la propagación.
- Un par que coincide una sola vez, aunque sea por vía exacta y semántica a la vez, no marca coordinación. La ventana escala con el período. En `entrega/cuentas.csv` cada cuenta está en una operación como mucho.
- La precisión de cuentas de la última aceptada es 0,909 en el completo y 1,0 en las ventanas. Está arriba del piso, con poco margen.
- Sin clave nunca se llama a Jev.
