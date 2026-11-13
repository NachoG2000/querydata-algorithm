# Violaciones: coordinación, loop y entrega

Veredicto de cada invariante de `docs/contexto.md` 2.3, 2.4 y 2.5 contra el código y los archivos en el commit 60c4a68. No se cambió código de producto. Cada veredicto sale de una skill que se puede volver a correr:

- `.claude/skills/verificar-coordinacion/run.sh` (2.3)
- `.claude/skills/verificar-loop/run.sh` (2.4)
- `.claude/skills/verificar-entrega/run.sh` (2.5)

Las tres aceptan `--romper` para mostrar que cada chequeo puede fallar.

## 2.3 Evidencia de coordinación

| Invariante | Veredicto | Dónde | Ejemplo concreto |
|---|---|---|---|
| Un par de comentarios aporta como mucho un evento | Se cumple | `pipeline.py:coordinacion` l.372 (`repeticiones = defaultdict(set)`) y l.393 (contexto = `(publicacion, guion)`) | Cuentas sintéticas `x1`,`y1` con el mismo texto en `p15` a 0,2 s coinciden por vía exacta y por paráfrasis. El contexto es el mismo y da peso 1, así que no se marcan. Si se agrega `"sem"` a la clave semántica (mutación `doble_evento`), las dos quedan marcadas. |
| Arista de peso 1 no marca coordinación | Se cumple | `pipeline.py:coordinacion` l.350 (`veces >= 2`), l.394 (`len(contextos)>=2`); `ampliar_semillas` l.469 (`len(publicaciones)>=2`) | Con el mismo par, `veces >= 1` o `len(contextos) >= 1` marca a `x1`,`y1`. El código actual no lo hace. |
| Ventanas y umbrales estimados de los datos y escalados a la exposición | Se cumple (verificado para el largo del período; volumen y población por lectura) | `pipeline.py:coordinacion` l.332 (ventana por mezcla gaussiana), l.338-339 y l.400 (soporte por población, participantes por volumen) | Dilatar todos los tiempos ×10 lleva la ventana de 0,3 s a 3,2 s. Una ventana fija de 600 s no escala y el chequeo la detecta. |
| Cada cuenta pertenece como mucho a una operación | Se cumple | `pipeline.py:coordinacion` l.408 y `unir_detecciones` l.420-428 (componentes conexas sobre un dict) | `entrega/cuentas.csv` tiene 12002 filas, ningún `cuenta_id` repetido y 13 cuentas en 3 grupos. Si una detección une `c0` con `x9` y otra une `c0` con `c1`, quedan las tres en `g001`. |
| Precisión de cuentas en práctica ≥ 0,9 | Se cumple, al límite | `experiments.tsv` fila 145 (`de7ebd0`), columna `componentes` | La precisión es 0,909 en el completo (88 cuentas marcadas) y 1,0 en `dia_1_7`, `dia_8_14` y `dia_1_10`. Una cuenta mal marcada más en el completo la deja debajo de 0,9. No se recalculó: el pipeline tarda más de 10 min. |

Observación que no viola ninguna invariante: en el caso sintético, un grupo de 6 cuentas que repite el guion 2 veces solo se detecta a medias (3 de 6). La ventana estimada de 0,3 s corta la ráfaga, que dura ~1,8 s. Es pérdida de recall, no de precisión.

## 2.4 Loop de experimentación

| Invariante | Veredicto | Dónde | Ejemplo concreto |
|---|---|---|---|
| Toda corrida queda registrada en `experiments.tsv`, aceptada o no | Se cumple en lo observable | `eval.py:append_experiment` l.121, `eval.py:mark_experiment` l.142 | Las 148 filas tienen estado: 21 `accepted` y 127 `discarded`. Los ids van de 1 a 148 sin huecos. Una corrida que muere antes de `append_experiment` no deja fila (por ejemplo el `RuntimeError` de presupuesto en `eval.py:main` l.205-211), y eso no es verificable desde los archivos. |
| Un cambio aceptado no empeora la otra tarea ni ninguna partición | No se cumple | `eval.py:main` l.216 toma el estado de `--estado` y no aplica la regla. La regla vive solo en `program.md` l.15-24. | Fila 2 (`9b7bd59`) contra fila 1: `completo.narrativas` baja de 7,93 a 6,86 y `dia_1_7.narrativas` de 8,83 a 7,28. Fila 46 (`125b383`) contra fila 31: `dia_1_7.coordinacion` baja de 7,95 a 3,26 y `dia_8_14.coordinacion` de 9,13 a 2,18. Las dos son de la regla vieja (combinado + margen 0,20). Con la regla por tarea (filas 140, 143 y 145) no hay regresiones. |
| Una descartada deja el código exactamente como antes | Se cumple para el código commiteado | `program.md` l.40 (paso 4), `eval.py:git_commit` l.137 | Ninguna fila descartada corrió sobre un `pipeline.py`/`decisores.py` distinto del último aceptado. Los cambios sin commitear del árbol de trabajo en cada corrida no son verificables. |
| El loop solo edita `pipeline.py` (y `PARAMS` de `decisores.py`) | No se cumple | `program.md` l.19 y l.40; diff entre commits aceptados consecutivos | La fila 2 (`9b7bd59`) también cambia `eval.py`, `tests/test_reproducibilidad.py`, `README.md`, `PREGUNTAS.md` y `SETUP_PROMPT.md`. La fila 140 (`a6643a5`) también cambia `eval.py`, `nli_local.py`, `requirements.txt`, `tests/test_nli_cache.py`, `.env.example`, `README.md` y `entrega/*`. Parte de eso está autorizado fuera del loop (`program.md` l.17 permite agregar `dia_1_10` a `eval.py`, y la integración de Jev entra en `c1a4bd5`), pero la invariante literal se rompe. |

## 2.5 Entrega del set final

| Invariante | Veredicto | Dónde | Ejemplo concreto |
|---|---|---|---|
| `main` siempre contiene una `entrega/` válida | Se cumple | `pipeline.py:escribir_entrega` l.681, constantes `NARRATIVAS` l.101 / `ESTADOS` l.102 / `RAFAGAS` l.103 | En `main` y `origin/main` están los 4 archivos con sus columnas. Los ids son únicos (150000 comentarios, 28 narrativas, 12002 cuentas), cada cuenta tiene a lo sumo un grupo y los 4 SHA-256 coinciden con el manifiesto de `FINAL_RUN.md`. |
| Solo se mergea si el mejor commit supera al vigente según la regla de aceptación | Se cumple en los números; ningún código lo hace cumplir | `program.md` l.47 (solo prosa) | El código de `main` es el de la fila 145 (`de7ebd0`). A: 14,02/12,35/17,91 contra 13,37/11,58/17,25 de referencia. B: igual a la referencia (19,79/5,63/12,14). `dia_1_10` no se compara porque `program.md` l.24 no da valor de referencia. |
| La corrida final calcula embeddings desde cero, y su `costo.json` es el que se entrega | No verificable | `pipeline.py:embeddings` l.172/184 reutiliza `.cache/embeddings`; `pipeline.py:reporte_referencia` l.701 (reuso en l.738) reemplaza `segundos` por el tiempo de una corrida previa si la huella coincide | `entrega/costo.json` coincide con el manifiesto, pero no registra si la caché estaba fría. Solo dice `medicion.tipo="primera_corrida_local"`. |
| Dos corridas del commit entregado producen archivos idénticos, sin claves | No se cumple para `main` (la parte "sin claves" se cumple) | `FINAL_RUN.md`; `main:pipeline.py`; `tests/test_reproducibilidad.py` | `main:pipeline.py` (sha256 `8381e041…`) no es el `pipeline.py` de `c7406f3` (`37c85259…`), que según `FINAL_RUN.md` generó la `entrega/` publicada. Correr `main` no reproduce la entrega de `main`. El test de reproducibilidad solo cubre `reporte_referencia` y `eval.invoke_pipeline`, no dos corridas completas. El escaneo de claves y rutas personales en los 4 archivos no encontró nada. |

## Resumen de violaciones

- 2.4: dos aceptadas con la regla vieja empeoraron particiones (filas 2 y 46). Ningún código aplica la regla de aceptación.
- 2.4: commits aceptados tocan archivos fuera de `pipeline.py`/`decisores.py` (filas 2 y 140).
- 2.5: `main` corre el código de `de7ebd0` pero entrega archivos generados por `c7406f3`, así que la entrega no es reproducible desde `main`.
- 2.5 (no verificable): nada prueba que la corrida final calculó los embeddings desde cero.
