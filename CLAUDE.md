# CLAUDE.md

Pipeline del equipo para el desafío QualyData (track Big Data), Hackathon Argentina Space 2026, Salta, 11 al 13 de noviembre de 2026. Enunciado oficial: https://github.com/qualydata-org/desafio-qualydata. Si este archivo contradice el enunciado, manda el enunciado.

Contexto largo, decisiones y su porqué: [`docs/contexto.md`](docs/contexto.md). Léelo antes de proponer cambios de arquitectura.

## Qué resuelve

Sobre comentarios públicos sintéticos responde: **qué circula, desde cuándo y quién lo empuja**.
- **Tarea A (narrativas, 30 pts):** agrupar comentarios en narrativas sin lista previa, marcar ruido, postura apoya/rechaza, `fecha_origen` de cada narrativa.
- **Tarea B (coordinación, 25 pts):** detectar cuentas coordinadas y agruparlas por operación.
- 45 pts más los da el jurado: costo, escala y almacenamiento (20), robustez (15), claridad y visualización (10).

## Reglas duras (nunca romper)

1. Un comando: `python pipeline.py --datos <dir> --entrega <dir>`. Determinista: dos corridas dan archivos idénticos.
2. Funciona sin claves. APIs externas (Jev, LLM) solo si existe su variable de entorno, y siempre con reemplazo local.
3. Cero secretos en git.
4. Todo gasto de IA del pipeline va a `costo.json`. El `costo.json` de `entrega/` sale de la corrida real sobre el set final, con embeddings calculados desde cero.
5. Nada específico del set de práctica: ni palabras, ni temas, ni cantidades, ni umbrales absolutos ajustados a mano. Umbrales relativos a los datos y escalados a la exposición (largo del período, volumen).
6. La verdad de práctica solo se usa para medir (vía `evaluacion/puntuar.py`) o en diagnósticos que no alimentan al predictor.
7. Nunca editar `evaluacion/puntuar.py` ni los datos. `eval.py` solo con autorización explícita.
8. `main` contiene la entrega válida. El trabajo experimental va en ramas y solo se mergea si cumple la regla de aceptación.
9. Solo cuenta lo que está en el repo al cierre (13/11/2026, 13:00). Lo que se sube después no se evalúa.

## Mapa del repo

| Ruta | Qué es |
|---|---|
| `pipeline.py` | El pipeline completo. Parámetros en `PARAMS` al inicio. Único archivo que edita el loop de optimización. |
| `decisores.py` | `DecisionEngine.decide(lote) -> [(etiqueta, prob)]` y el atajo `decidir(...)`, en modo `local` o `jev`. Sin `TYPESAFE_API_KEY` cae a `local`. Caché SQLite en `.cache/decisores.sqlite3`, concurrencia con hilos y conteo de costo. |
| `nli_local.py` | NLI local (MiniLMv2 mnli-xnli) para postura de raíces y relación con el padre, con caché. Se activa con `PARAMS["nli_local"]`. |
| `eval.py` | Corre el pipeline sobre práctica y las ventanas completo, días 1–7, 8–14 y 1–10, puntúa y registra en `experiments.tsv`. |
| `experiments.tsv` | Registro de cada corrida del loop: commit, estado (`accepted` o `discarded`), parámetros, componentes, costos y tiempos. |
| `program.md` | Instrucciones y backlog del loop autónomo. |
| `entrega/` | Los cuatro archivos oficiales del set final: `comentarios.csv`, `narrativas.csv`, `cuentas.csv` y `costo.json`. |
| `FINAL_RUN.md` | Procedencia de `entrega/`: commit que la generó, hashes de entrada, tiempo de la corrida fría. |
| `export_vault.py` | Genera el vault de Obsidian (solo agregados) para la demo. |
| `escala.py` | Curva de costo replicando el set (factores ×1, ×5 y ×20 por defecto; `--incluir-50` agrega ×50). |
| `analizar_practica.py` | Diagnósticos sobre práctica. No alimenta al predictor. |
| `tests/` | Pruebas de reproducibilidad y de la caché NLI. |
| `ejemplos/linea_base.py`, `evaluacion/puntuar.py` | Copias del código oficial. No se editan. |
| `NOTES.md` | Exploración y diagnósticos. |
| `RESULTS.md` | Puntajes oficiales por commit. |
| `PREGUNTAS.md` | Preguntas abiertas a la organización. |
| `SETUP_PROMPT.md` | Instrucciones del setup inicial. |
| `docs/contexto.md` | Historia de decisiones y lecciones. |
| `docs/violaciones.md` | Invariantes que el código actual no cumple, con archivo, función y ejemplo. Insumo del loop. |
| [`docs/statecharts/`](docs/statecharts/README.md) | Diagramas de los flujos principales, chequeados con TLC. |
| `.claude/skills/` | Skills de verificación formal, una por subsistema. |

Las salidas auxiliares (`detalles.parquet`, `estados.parquet`, `rafagas.parquet`, `metricas.json`) se escriben junto a cada corrida en `salida/`, que no se versiona.

## Subsistemas y sus máquinas de estado

Cada uno tiene una skill de verificación formal en `.claude/skills/`. Antes de tocar un subsistema, lee su skill, respeta sus invariantes y corre su chequeo.

| Subsistema | Skill | Statechart |
|---|---|---|
| Ciclo de vida de una narrativa: suelto → candidata → nacida → activa ⇄ mutando / latente, con `amplificada` como atributo | [`verificar-narrativa`](.claude/skills/verificar-narrativa/SKILL.md) | |
| Recorrido de un comentario: asignación, ruido, herencia por aristas de `respuesta_a`, postura | [`verificar-comentario`](.claude/skills/verificar-comentario/SKILL.md) | |
| Evidencia de coordinación: par de comentarios → evento → arista entre cuentas → cuenta coordinada → operación | [`verificar-coordinacion`](.claude/skills/verificar-coordinacion/SKILL.md) | |
| Loop de experimentación: propuesta → corrida → aceptación por tarea y ventana → commit o descarte → registro | [`verificar-loop`](.claude/skills/verificar-loop/SKILL.md) | [experimento del loop](docs/statecharts/README.md#3-un-experimento-del-loop-de-mejora) |
| Entrega del set final: rama → verificación → merge → corrida desde cero → `entrega/` → commit | [`verificar-entrega`](.claude/skills/verificar-entrega/SKILL.md) | [entrega final](docs/statecharts/README.md#2-entrega-final-de-la-rama-a-main) |

Otros flujos dibujados en [`docs/statecharts/`](docs/statecharts/README.md): el jurado re-ejecuta el pipeline sobre el set final, y quien mira la demo navega el vault de Obsidian.

## Regla de aceptación de experimentos

- Se evalúa por tarea: un cambio en A se juzga por los componentes de A; uno en B, por los de B. La otra tarea no puede empeorar.
- Se mide en el set completo y en las ventanas días 1–7, 8–14 y 1–10. Ninguna puede empeorar respecto de su propio valor anterior.
- Decide el puntaje oficial de `puntuar.py`. El tiempo solo desempata, salvo que suba más de un 30%.
- En B, precisión de cuentas ≥ 0,9 como piso separado: un buen B-cubed de operaciones no compensa una detección mala.

## Estado actual (actualizar con cada commit aceptado)

- Línea base oficial: 21,96 / 55 (A 12,52 + B 9,44).
- `entrega/` del set final: generada por `c7406f3` y publicada en `8a1f5be`. En práctica, ese código da **33,16 / 55** (A 13,37 + B 19,79). La corrida fría sobre el set final tardó 856,1 s, sin tokens ni dólares de API, y marcó 13 cuentas en 3 operaciones.
- Mejor código aceptado: `de7ebd0`, **33,81 / 55** en práctica (A 14,02 + B 19,79). Ventanas: 17,98 (días 1–7), 30,05 (días 8–14) y 23,27 (días 1–10). Precisión de cuentas 0,909 en el completo y 1,0 en las ventanas. Todavía no regeneró `entrega/`.
- Componentes del completo con `de7ebd0` (0 a 1): agrupamiento B-cubed 0,415, postura macro-F1 0,510, ruido F1 0,718, origen 0,333, cuentas F1 0,788, operaciones B-cubed 0,799.
- Mayores huecos: agrupamiento de narrativas, origen de emergentes (dos de tres emergentes no se fechan bien) y recall de cuentas en ventanas cortas (0,17 en días 1–7, 0,31 en días 1–10). El set final dura 10 días.

## Lecciones aprendidas (no repetir errores)

- Una variante con B-cubed de operaciones alto marcó 892 cuentas con 10% de precisión. Por eso el piso de precisión va aparte.
- La partición días 1–7 sí tiene actividad coordinada (114 de 115 cuentas activas). Si un detector no encuentra nada ahí, sus umbrales no generalizan: no es ruido.
- La coordinación necesita repeticiones y rinde mucho menos en períodos cortos. El set final dura 10 días: medir siempre en la ventana de días 1–10.
- Ajustar `fecha_origen` de un cluster mezclado no sirve. Primero separar la narrativa emergente, después fechar.
- Los tiempos de práctica usan embeddings cacheados. Nunca reportarlos como tiempo real del set final.
- Una misma coincidencia no cuenta como dos eventos por pasar por la vía exacta y la semántica.
