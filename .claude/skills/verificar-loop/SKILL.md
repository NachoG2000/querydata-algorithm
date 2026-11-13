---
name: verificar-loop
description: Verifica formalmente el loop de experimentación (propuesta, corrida, evaluación, aceptada o descartada, registro) y sus invariantes de docs/contexto.md 2.4 contra eval.py, program.md, experiments.tsv y git log. Usar al tocar eval.py, el protocolo de aceptación de program.md, al registrar o marcar experimentos, o antes de afirmar que el loop fue limpio.
---

# Verificar el loop de experimentación

Promesa que se verifica: cada corrida queda registrada, una aceptada no empeora ninguna tarea ni partición, una descartada deja el código como estaba y el loop sólo edita `pipeline.py` y `PARAMS` de `decisores.py`. Si se rompe, la entrega elegida puede ser peor que una anterior sin que nadie lo vea, o el puntaje deja de medir sólo el pipeline.

## Cuándo usarla

- Cambia `eval.py` (`append_experiment`, `mark_experiment`, `git_commit`, `main`).
- Cambia el protocolo de aceptación en `program.md`.
- Se agregan filas a `experiments.tsv` o commits aceptados.
- Antes de reportar que el historial de experimentos cumple las reglas.

## Comando

Desde la raíz del repo:

```sh
STATECHART=<script de /statechart> PYTHON=<python con pandas> OUT=<carpeta fuera del repo> .claude/skills/verificar-loop/run.sh
```

Ubicá el script `statechart` con la skill `/statechart` (sus rutas cambian entre versiones; no las copies acá). Sin `STATECHART` se corre sólo el chequeo de archivos. Tarda unos segundos.

Para ver que cada chequeo puede fallar:

```sh
... .claude/skills/verificar-loop/run.sh --romper
```

`--romper` usa `modelo-roto.cfg` (acepta con la regla histórica de margen, descarta sin `git reset`, edita `eval.py`, evalúa sin agregar fila) y una copia en memoria de `experiments.tsv` con un estado vacío, un id faltante, una aceptada que empeora `dia_1_7.coordinacion` con commit inexistente y dos descartadas sobre código distinto. Las cuatro invariantes deben fallar en ambas partes. No escribe ningún archivo del repo.

## Qué hay en la carpeta

- `modelo.tla` y `modelo.cfg`. Modelo TLA+ de una corrida a la vez, 2 corridas, particiones `completo` y `dia_1_7`, puntos 0..2. Invariantes `TodaCorridaRegistrada`, `AceptadaNoEmpeora`, `DescartadaRestaura`, `SoloPipelineYDecisores`. `Fin` es el estado final que no cambia nada.
- `modelo-roto.cfg`. Las cuatro perillas rotas.
- `view.ts`. Nombres de estados y pasos para `/statechart`.
- `verificar.py`. Chequeo sobre `experiments.tsv` y `git` real. Sale con 1 si alguna invariante falla.

Leé todo resultado TLA+ con la skill `/statechart`: muestra cada violación como su camino más corto en palabras y, si todo pasa, el diagrama de estados.

## Cómo leer `verificar.py`

- **I1 toda corrida registrada.** Toda fila tiene `estado` en `accepted` o `discarded` y los `id` son contiguos. Una corrida que muere antes de `append_experiment` no deja rastro; eso no es verificable desde archivos.
- **I2 aceptada no empeora.** Compara `componentes.<particion>.<narrativas|coordinacion>.puntos` de cada aceptada contra la aceptada anterior, en las particiones presentes en ambas. Cada regresión se etiqueta con la era del protocolo: `combinado_margen` (filas sin `dia_1_10`, regla histórica de métrica combinada y margen 0,20) o `por_tarea` (protocolo vigente de `program.md`).
- **I3 descartada restaura.** Una descartada debe correr sobre el mismo `pipeline.py`/`decisores.py` que la última aceptada, y dos descartadas seguidas no pueden diferir en esos archivos. Sólo ve código commiteado; un diff sin commitear que sobrevivió no es visible.
- **I4 sólo `pipeline.py`/`decisores.py`.** Archivos cambiados entre la aceptada anterior y la actual, ignorando bitácora (`experiments.tsv`, `RESULTS.md`, `NOTES.md`, `program.md`, `FINAL_RUN.md`). La fila 1 es la línea base y no se compara.

Una falla en `verificar.py` es un hallazgo sobre la historia real, no un error del chequeo. No la arregles debilitando la invariante. Una falla del modelo con `modelo.cfg` sí indica que el modelo dejó de describir el código o que el código cambió: compará el paso del camino con la función de la cobertura.

## Cobertura

| Chequeo | Archivo:función |
| --- | --- |
| I1, paso `Evaluar` | `eval.py:append_experiment` (l. 121), `eval.py:main` (l. 216-233) |
| I1, paso `Marcar` | `eval.py:mark_experiment` (l. 142) |
| I2, paso `Aceptar` | `program.md` protocolo por tarea (l. 15-24), regla histórica reemplazada (l. 17); `eval.py:main` no decide, recibe `--estado` |
| I3, paso `Descartar` | `program.md` paso 4 (l. 40), `eval.py:git_commit` (l. 137) |
| I4, paso `Proponer` | `program.md` l. 19 y l. 40, historia `git log` de los commits de filas `accepted` |
| Datos | `experiments.tsv` columnas `id`, `commit`, `estado`, `componentes` |

## Commit de sincronía

`60c4a68`. Movelo sólo después de confirmar que el modelo y la cobertura siguen describiendo `eval.py` y `program.md` en el commit nuevo, y de correr `run.sh` y `run.sh --romper`. Para ver si hace falta: `git diff 60c4a68 -- eval.py program.md`.

## Qué no cubre

- No corre `eval.py` ni el pipeline. Verifica la historia registrada, no corridas nuevas.
- El modelo es secuencial (un experimento a la vez). No modela dos agentes escribiendo `experiments.tsv` a la vez.
- No ve el árbol de trabajo en el momento de cada corrida, sólo commits.
- No verifica que la regla de aceptación vigente se aplicó contra el "comparador propio" de cada tarea: compara contra la aceptada anterior, que es lo que dice la invariante literal.
