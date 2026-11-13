---
name: verificar-comentario
description: Verifica el recorrido de un comentario (docs/contexto.md sección 2.2) contra pipeline.postura y entrega/comentarios.csv. Usar cuando un cambio toca postura, la propagación por respuesta_a, AFIRMACION_CORTA, CONTRADICCION, el NLI de aristas o cómo ejecutar arma la columna narrativa.
---

# Verificar el recorrido de un comentario

Reglas (2.2): cada comentario termina con exactamente una narrativa o `ninguna`. Una respuesta que acompaña hereda narrativa y postura. Una que contradice tiene la misma narrativa y la postura opuesta. `ninguna` no propaga. Ciclos y padres inexistentes en `respuesta_a` no rompen. Si se rompen, la entrega cuenta mal el apoyo y el rechazo de cada narrativa o se cuelga con datos sucios.

## ¿El cambio toca esto?

| Regla | Código | Chequeo |
|---|---|---|
| exactamente una narrativa o ninguna | pipeline.py:postura (515-608), ejecutar (800-801) | I1, E1, E2, TLA+ UnaNarrativa |
| acompaña hereda | pipeline.py:postura (543-556, 600-606) | I2, E3, TLA+ AcompanaHereda |
| contradice: misma narrativa, postura opuesta | pipeline.py:postura (553-554, 606) | I3, E4, TLA+ ContradiceOpuesta |
| ninguna no propaga | pipeline.py:postura (604-606) | I4, TLA+ NingunaNoPropaga |
| ciclos y padres inexistentes | pipeline.py:postura (523, 584-598) | I5, E5, TLA+ NoDeadlock |
| postura de arista o de decisor (Pasos de 2.2) | pipeline.py:postura (570, 604) | I6, TLA+ PosturaConOrigen |

Commit de sincronía: `60c4a68`. Si `git diff 60c4a68 -- pipeline.py` toca `postura` o `ejecutar`, volvé a leer el código contra `modelo/Comentario.tla` y `chequeo.py`. Mové el commit solo después de confirmar que describen el código nuevo.

## Correr

Desde la raíz del repo:

```sh
python .claude/skills/verificar-comentario/chequeo.py --datos <carpeta con comentarios.csv.gz>
```

Sin `--datos` corren los chequeos sintéticos (llaman a `pipeline.postura` real con `nli_local` apagado y un decisor falso: ciclo a↔b, padre inexistente `zzz`, "Tal cual", "Mentira", hijo de un padre `ninguna`) y E1 sobre `entrega/`. Sale con 0 si solo fallan hallazgos conocidos (I6, E4).

Para el modelo TLA+, corré `/statechart` sobre `modelo/Comentario.tla` con `modelo/Comentario.cfg` y `modelo/view.ts`, en una carpeta temporal fuera del repo (3 comentarios, unos 4 s, 41.112 estados). Hoy: `PosturaConOrigen` se rompe; el resto se cumple. Leé el resultado con `/statechart`.

## Probar que puede fallar

`chequeo.py --romper <nombre>` muta `pipeline.py` en memoria:

- `contradiccion-sin-signo` hace fallar I3.
- `ninguna-propaga` hace fallar I4.
- `sin-deteccion-ciclos` hace fallar I5.

En el modelo, `ROTO` en una copia del `.cfg` con los mismos nombres rompe `ContradiceOpuesta`, `NingunaNoPropaga` y `NoDeadlock`.

## Bug o error de modelo

E3 y E4 usan las expresiones regulares del pipeline como aproximación sobre datos reales: confirmá cada id leyendo el texto antes de llamarlo bug. Si el código real no reproduce una falla del modelo, el modelo está mal. Hallazgos vigentes: `docs/violaciones/narrativa-comentario.md`.

## Qué no cubre

No ejecuta el NLI real ni el decisor Jev. No evalúa si el clasificador de relación acierta; solo si el resultado se propaga bien. El modelo TLA+ no tiene más de 3 comentarios ni más de una narrativa.
