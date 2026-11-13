# Violaciones encontradas con los statecharts

Reglas que el código de `60c4a68` no cumple. Los modelos y sus caminos están en [../statecharts/README.md](../statecharts/README.md).

## El jurado no obtiene `entrega/` al re-ejecutar `main`

- **Regla.** Re-ejecutar el comando de FINAL_RUN.md sobre el set final da archivos idénticos a `entrega/`.
- **Dónde.** `pipeline.py:ejecutar` en `main` difiere del `c7406f3` que generó `entrega/` (`git diff --stat c7406f3 HEAD` toca `pipeline.py`, `decisores.py` y `nli_local.py`). `pipeline.py:main` además usa `--decisor jev` por defecto, que con clave cambia posturas.
- **Ejemplo.** Camino del modelo `jurado-reejecuta`: repo clonado (main, sin clave) → baja modelos → decide en local → predicciones distintas. Inferido del diff y de FINAL_RUN.md («Esas mejoras todavía no se aplicaron a los cuatro archivos de `entrega/`»). No se corrió el pipeline completo (856 s).

## `costo.json` nunca se reproduce en otra máquina

- **Regla.** `costo.json` re-ejecutado es igual al de `entrega/`.
- **Dónde.** `pipeline.py:reporte_referencia` reutiliza duraciones sólo si existe `.cache/reportes/<huella>.json`, que no está en git. En otra máquina escribe sus propios `segundos` y `hardware`.
- **Ejemplo.** En macOS arm64 `hardware` sale distinto de `"Linux x86_64, CPU, 4 hilos"` y `segundos` distinto de `856.1`. Inferido del código.

## Sin clave igual hay tráfico a Hugging Face

- **Regla.** Sin clave el pipeline no sale a la red.
- **Dónde.** `pipeline.py:embeddings` reintenta sin `local_files_only` cuando los pesos no están y `HF_HUB_OFFLINE` no está activo. `nli_local.py` baja el modelo NLI salvo que `HF_HUB_OFFLINE` esté activo.
- **Ejemplo.** Primera corrida en una máquina nueva. No usa clave ni tiene costo. El README lo documenta.

## `origin/main` publica código con una entrega de otro commit

- **Regla.** `main` siempre tiene una entrega generada por su propio código.
- **Dónde.** Proceso de cierre (FINAL_RUN.md, `program.md` «Cierre solicitado por el usuario»). Nada en el repo lo verifica.
- **Ejemplo.** `60c4a68` trae el código de la experiencia 145 y `entrega/` sigue siendo la de `8a1f5be` (código `c7406f3`). Camino: rama → verificado → merge → push sin regenerar.

## Una corrida de `eval.py` que falla no queda registrada

- **Regla.** Toda corrida queda en `experiments.tsv`.
- **Dónde.** `eval.py:main`. `invoke_pipeline` lanza `RuntimeError` (falla o timeout) antes de `append_experiment`. El presupuesto agotado también lanza antes.
- **Ejemplo.** Un pipeline que supera `--timeout 300` en la partición `dia_1_10` termina sin fila. Lo mismo un `git reset --hard` tras `--marcar discarded` antes del commit de bitácora, porque `experiments.tsv` está versionado.

## `--marcar accepted` no verifica particiones

- **Regla.** Una hipótesis aceptada no empeora ninguna partición de su tarea.
- **Dónde.** `eval.py:mark_experiment` sólo cambia `estado` y `commit`. `append_experiment` no guarda `dia_1_10` en columna propia.
- **Ejemplo.** Una fila con `dia_8_14` peor que el comparador se acepta igual con `python eval.py --marcar accepted`. La regla depende de quien corre el loop.

## Nota de narrativa con operación y cero días amplificada

- **Regla.** Si la nota de una narrativa lista una operación, muestra días amplificada.
- **Dónde.** `export_vault.py:export_vault`. Sin `estados.parquet` las métricas quedan en el valor por defecto, pero los enlaces a operaciones salen de los comentarios crudos.
- **Ejemplo.** Reproducido: `python export_vault.py --datos datos/final --entrega entrega --auxiliares <carpeta vacía>` genera `narrativa-n002.md` con «Operaciones relacionadas» y `dias_amplificada: 0`, `volumen_total: 5`, `estado_actual: "desconocido"`. Pasa en un clon limpio, porque `salida/` está en `.gitignore`.
