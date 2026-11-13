---
name: verificar-narrativa
description: Verifica el ciclo de vida de una narrativa (docs/contexto.md sección 2.1) contra pipeline.py y la entrega. Usar cuando un cambio toca validar_candidatas, fecha_origen, describir, estados_por_dia o agrupar, o cuando cambia entrega/narrativas.csv.
---

# Verificar el ciclo de vida de una narrativa

Reglas (2.1): una narrativa pasa por suelto, candidata, nacida, activa, mutando y latente; `amplificada` es un atributo aparte. Si se rompen, la entrega fecha mal el origen, hace nacer narrativas sostenidas solo por cuentas coordinadas o parte una narrativa en dos.

El pipeline es por lotes. Los estados `activa`, `mutando` y `latente` no existen como máquina: `estados_por_dia` clasifica cada día por separado. `suelto` y `candidata` tampoco se guardan; solo existen dentro de `agrupar` y `validar_candidatas`.

## ¿El cambio toca esto?

Cobertura (archivo:función, líneas en el commit de sincronía):

| Regla | Código | Chequeo |
|---|---|---|
| fecha_origen = más antiguo del núcleo | pipeline.py:fecha_origen (611), describir (621) | N1, E1 |
| no nace solo con cuentas coordinadas | pipeline.py:validar_candidatas (484-501) | N2, TLA+ NoNaceSoloCoordinada |
| transiciones de 2.1 | pipeline.py:estados_por_dia (642-678) | N3, E2, TLA+ TransicionPermitida |
| amplificada desde el nacimiento | pipeline.py:estados_por_dia (668) | N4 |
| revive o muta con el mismo id | pipeline.py:estados_por_dia, ejecutar (801) | N5, TLA+ ConservaId |

Commit de sincronía: `60c4a68`. Si `git diff 60c4a68 -- pipeline.py` toca alguna de esas funciones, volvé a leer el código contra `modelo/Narrativa.tla` y `chequeo.py` antes de confiar en el resultado. Mové este commit solo después de confirmar que el modelo y el chequeo describen el código nuevo.

## Correr

Desde la raíz del repo:

```sh
python .claude/skills/verificar-narrativa/chequeo.py --datos <carpeta con comentarios.csv.gz> --estados salida/final/estados.parquet
```

`--datos` y `--estados` son opcionales; sin ellos corren solo los chequeos sintéticos sobre las funciones reales. Tarda unos segundos. Sale con 0 si solo fallan hallazgos conocidos (N3, E2) y con 1 si falla otra regla.

Para el modelo TLA+, corré `/statechart` sobre `modelo/Narrativa.tla` con `modelo/Narrativa.cfg` y la vista `modelo/view.ts`, en una carpeta temporal fuera del repo. Hoy: 94 estados; `TransicionPermitida` se rompe (nacida → mutando en 3 pasos); `ConservaId`, `NoNaceSoloCoordinada` y `NoDeadlock` se cumplen. Leé el resultado con `/statechart`.

## Probar que puede fallar

`chequeo.py --romper <nombre>` aplica una mutación en memoria a `pipeline.py` (el archivo no cambia):

- `origen-maximo` hace fallar N1.
- `cuenta-coordinadas` hace fallar N2.
- `amplificada-tarde` hace fallar N4.

En el modelo, cambiá `ROTO` en una copia del `.cfg`: `cuenta-coordinadas` rompe `NoNaceSoloCoordinada`; `revive-con-id-nuevo` rompe `ConservaId`. Si una mutación ya no aplica, el script lo dice: actualizá `ROTURAS`.

## Bug o error de modelo

Ante una falla nueva, reproducila con la función real (el chequeo ya la llama). Si la función real no muestra el problema, el modelo está mal: corregí el modelo, no la regla. No debilites una regla para que pase. Los hallazgos vigentes están en `docs/violaciones/narrativa-comentario.md`.

## Qué no cubre

No verifica que el clustering separe emergentes ni que no parta una narrativa que muta (requiere etiquetas). No verifica que el núcleo use la centralidad respecto del centroide de la narrativa final. El modelo TLA+ tiene una sola narrativa y 3 días.
