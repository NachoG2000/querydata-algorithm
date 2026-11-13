---
name: verificar-coordinacion
description: Verifica formalmente la evidencia de coordinación de pipeline.py (par de comentarios → evento → arista → cuenta coordinada → operación) contra las invariantes de docs/contexto.md 2.3. Usar antes y después de tocar pipeline.coordinacion, unir_detecciones, ampliar_semillas, PARAMS de coordinación, entrega/cuentas.csv, o al aceptar un experimento de la tarea B.
---

# Verificar coordinación

**Qué protege.** Una coincidencia aislada entre dos cuentas no debe convertirlas en "coordinadas". Si se rompe, la entrega acusa a cuentas orgánicas y la precisión oficial de la tarea B cae debajo de 0,9.

## Cómo correrla

Desde la raíz del repo (tarda ~5 s):

```sh
STATECHART=<script de la skill /statechart> PYTHON=<python con pandas, sklearn, networkx> .claude/skills/verificar-coordinacion/run.sh
```

Agregá `--romper` para ver que cada chequeo puede fallar: corre el modelo con `modelo-roto.cfg` y el chequeo Python sobre variantes rotas de `pipeline.coordinacion` que se compilan en memoria (no se edita ningún archivo). Con `--romper`, todo debe salir `breaks` / `DETECTADA`. Si alguna sale `NO DETECTADA`, el chequeo quedó ciego: arreglá el chequeo, no el código.

Leé la salida TLA+ con la skill `/statechart`: da el camino más corto a cada invariante rota en palabras del dominio. Sin `STATECHART`, el script solo corre la parte Python.

## Qué verifica

| Invariante (contexto.md 2.3) | Modelo TLA+ (`modelo.tla`) | Chequeo sobre el código (`verificar.py`) |
|---|---|---|
| I1. Un par de comentarios aporta como mucho un evento | `UnEventoPorPar` | Dos cuentas `x1`,`y1` con el mismo texto largo, 0,2 s de diferencia, una sola vez: coinciden por vía exacta y por paráfrasis. No deben quedar marcadas. |
| I2. Arista de peso 1 no marca coordinación | `PesoUnoNoMarca` | El mismo caso, y las mutaciones `peso_uno` (`veces >= 1`) y `peso_uno_sem` (`len(contextos) >= 1`). |
| I3. Ventanas y umbrales estimados de los datos y escalados | no modelado (es numérico) | Metamórfico: dilatar todos los tiempos ×10 debe escalar la ventana entre ×5 y ×20. |
| I4. Cada cuenta en a lo sumo una operación | `CuentaUnaOperacion` | `unir_detecciones` con dos detecciones solapadas; y `entrega/cuentas.csv` sin `cuenta_id` repetidos ni dos grupos por cuenta. |
| I5. Precisión de cuentas en práctica ≥ 0,9 | no modelado | Lee la última fila `accepted` de `experiments.tsv` y exige precisión ≥ 0,9 en toda partición con cuentas marcadas. No corre el pipeline (>10 min). |

Modelo: 2 cuentas, 2 pares de comentarios, 2 vías, 2 operaciones. Constantes: `DEDUP` (la segunda vía no suma un contexto nuevo), `UMBRAL` (peso mínimo, el código usa 2), `UNICA` (una operación por cuenta). `modelo.cfg` refleja el código actual; `modelo-roto.cfg` apaga las tres. 97 estados.

## Registro de cobertura

Sincronizado con el commit **60c4a68**. Mové este commit solo después de confirmar que el modelo y los chequeos siguen describiendo el código en el commit nuevo (releé las líneas citadas y corré `run.sh` y `run.sh --romper`).

| Archivo:función (línea en 60c4a68) | Qué cubre |
|---|---|
| `pipeline.py:coordinacion` (311) | todo el chequeo Python corre esta función real |
| `pipeline.py:coordinacion` l.332 | ventana por mezcla gaussiana (I3, mutación `ventana_fija`) |
| `pipeline.py:coordinacion` l.338-339, 400 | soporte y participantes escalados por población y volumen (I3, solo por lectura) |
| `pipeline.py:coordinacion` l.350 | arista exacta con `veces >= 2` (I2, `UMBRAL`) |
| `pipeline.py:coordinacion` l.372, 393-394 | `repeticiones` como set de contextos (I1, `DEDUP`) |
| `pipeline.py:coordinacion` l.408 | componentes conexas → una operación por cuenta (I4) |
| `pipeline.py:unir_detecciones` (420) | unión de las dos detecciones (I4) |
| `entrega/cuentas.csv` | I4 sobre la entrega |
| `experiments.tsv` columna `componentes` | I5 |

Si un cambio toca cualquiera de esas líneas, o `ejemplos/linea_base.py:normalize`, o `pipeline.py:texto_embedding`, corré la skill. Si una mutación de `MUTACIONES` en `verificar.py` levanta `mutación ... ya no aplica`, el código cambió: actualizá el texto viejo/nuevo de esa mutación a la línea equivalente.

## Bug real o error del modelo

- Falla el modelo con `modelo.cfg`: el modelo dejó de reflejar el código o el código cambió la regla. Releé las líneas de la tabla; si el código cambió, es un hallazgo.
- Falla `I1+I2` con el código real: el código marca una coincidencia aislada. Es un bug. Confirmalo mirando `coordinacion_escalada` (se imprime en stdout de `coordinacion`).
- Falla `I3`: primero revisá que los datos sintéticos (`datos()`) sigan dilatándose linealmente; la mezcla gaussiana es inestable si los intervalos son enteros exactos (por eso se usa jitter continuo).
- La línea `[INFO] control` no es invariante: muestra cuántas de las 6 cuentas del grupo sintético se detectan. Hoy salen 3 de 6 porque la ventana estimada (0,3 s) corta la ráfaga; es recall, no precisión.

## Qué no cubre

- `pipeline.py:ampliar_semillas` (439): la expansión exige ≥ 2 publicaciones (l.469) pero no tiene chequeo propio.
- El corte por cuantil `q_peso_semantico` (l.397) puede ocultar o revelar dobles conteos según la distribución de pesos; el caso sintético usa un grupo que repite solo 2 veces para que el corte no tape el bug.
- La precisión real solo se lee del último registro; no se recalcula.
- El modelo no tiene tiempo ni ventanas: I3 e I5 solo se chequean en Python.
