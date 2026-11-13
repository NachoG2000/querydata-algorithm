---
name: verificar-entrega
description: Verifica las invariantes de la entrega del set final (docs/contexto.md 2.5) con un modelo TLA+ del proceso rama_experimental → verificada → mergeada → corrida_final → entregada y chequeos sobre entrega/, FINAL_RUN.md, costo.json, experiments.tsv y git. Usala antes de mergear a main, antes de regenerar o publicar entrega/, o al cambiar pipeline.py:escribir_entrega, reporte_referencia, embeddings o el costo de ejecutar.
---

# Verificar la entrega del set final

## Qué promete

1. `main` siempre contiene una `entrega/` válida. Daño si no: el jurado recibe archivos ilegibles o con ids repetidos.
2. Sólo se mergea si el mejor commit supera al vigente según la regla de aceptación (program.md:47). Daño si no: se publica código peor que el entregado.
3. La corrida final calcula embeddings desde cero y su `costo.json` es el que se entrega. Daño si no: el costo y el tiempo declarados no son los de una corrida fría.
4. Dos corridas del commit entregado producen archivos idénticos, sin claves. Daño si no: la entrega no se puede reproducir desde `main` o filtra secretos.

## Cómo correrla

Desde la raíz del repo:

```sh
STATECHART=<script del skill /statechart> PYTHON=<python con pandas> .claude/skills/verificar-entrega/run.sh [--tests]
```

`STATECHART` es el script del skill pstack `/statechart`. Buscalo en ese skill, no lo copies acá. Sin `STATECHART` se omite el modelo y corren sólo los chequeos sobre archivos. `--tests` corre además `tests/test_reproducibilidad.py` (unos segundos). Agregá `--romper` para correr los chequeos sobre copias corruptas en memoria y confirmar que cada uno puede fallar. No toca disco. El script dura menos de 30 s y no corre el pipeline.

Código de salida 1 si algún chequeo de archivos falla o si el modelo con guardas (`modelo-guardado.cfg`) rompe una regla. Que `modelo.cfg` rompa reglas es esperado: describe el proceso tal como opera hoy.

Leé cada resultado TLA+ con el skill `/statechart`. Da el camino más corto a cada regla rota en palabras del proceso.

## Archivos

- `modelo.tla`. El proceso de entrega. Tres constantes son guardas que hoy no existen en código. `GUARDA_MERGE` exige que el candidato supere al vigente antes del merge. `CACHE_FRIA` borra `.cache` antes de la corrida final. `REGENERAR` exige una corrida final tras un merge antes de entregar.
- `modelo.cfg`. Las tres guardas en FALSE, como opera el repo. `modelo-guardado.cfg`. Las tres en TRUE.
- `view.ts`. Etiquetas del chart.
- `verificar.py`. Chequeos sobre `git show main:` y `origin/main:`.

## Resultado en 60c4a68

Modelo (`modelo.cfg`, 26 estados). Rompe `MergeSoloSiSupera` (verificar, mergear sin guarda), `CostoDeCorridaFria` y `EntregaReproducibleDesdeMain` (verificar, mergear, cerrar sin regenerar). Con guardas, las cuatro reglas se cumplen (14 estados).

Archivos. 28 pasan, 2 fallan, 2 no verificables.
- Falla. `main:pipeline.py` (sha256 8381e041…) no es el que generó `entrega/` (FINAL_RUN.md declara 37c85259…, el de c7406f3). Rerun de `main` no reproduce la entrega publicada.
- Falla. `main` tiene el código de la fila 145 (de7ebd0) pero `entrega/` sigue siendo de c7406f3. La fila 145 sí cumple la regla numérica (A 14,02/12,35/17,91 contra 13,37/11,58/17,25; B igual a la referencia).
- No verificable. `costo.json` no tiene campo que pruebe caché fría. `medicion.tipo = primera_corrida_local` y `reporte_referencia` puede reemplazar `segundos` por los de una corrida previa con la misma huella.
- No verificable. Dos corridas de >10 min sobre `datos/final`. El test de reproducibilidad no cubre eso.

## Real o error de modelado

Un FALLA de `verificar.py` es real. Leé el detalle que imprime. Un camino roto en `modelo-guardado.cfg` es un error de modelado o una guarda que dejó de describir el plan: revisá la acción contra el código de la cobertura. Un camino roto en `modelo.cfg` es la brecha conocida. Si alguien implementa una guarda en código, pasá esa constante a TRUE en `modelo.cfg` y anotá el archivo:función que la ejecuta.

## Cobertura

| Chequeo | Archivo:función |
|---|---|
| Columnas de narrativas.csv | pipeline.py:NARRATIVAS (línea 101) |
| Archivos de entrega y escritura atómica | pipeline.py:escribir_entrega (681) |
| Campos de costo.json | pipeline.py:ejecutar, dict `costo` (816) |
| Reuso de `segundos` | pipeline.py:reporte_referencia (701, reuso en 738) |
| Caché de embeddings | pipeline.py:embeddings (172, ruta en 184) |
| Regla de merge | program.md (líneas 24 y 47), experiments.tsv `componentes` |
| Manifiesto de hashes y commit entregado | FINAL_RUN.md |
| Reproducibilidad | tests/test_reproducibilidad.py, eval.py:invoke_pipeline (81) |

Commit de sincronía: `60c4a68`. Movelo sólo después de confirmar que el modelo y `verificar.py` describen el código del nuevo commit. Si `git diff 60c4a68 -- pipeline.py FINAL_RUN.md program.md tests/test_reproducibilidad.py entrega/` cambia algo de la cobertura, revisá la fila antes de mover el commit.

## Qué no cubre

No corre el pipeline ni compara dos corridas reales. No prueba que los embeddings se hayan calculado en frío. No valida contra la verdad del set final, que no es pública. El modelo es una abstracción de un solo candidato y un solo merge. La partición `dia_1_10` no entra en la regla porque program.md:24 no da su referencia.
