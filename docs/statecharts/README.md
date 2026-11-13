# Statecharts de los flujos principales

Cuatro flujos del proyecto modelados en TLA+, verificados con TLC y dibujados como statecharts. Cada carpeta tiene el modelo (`.tla`, `.cfg`), las etiquetas en español (`view.ts`), el chart (`chart.mmd`) y el reporte de TLC (`report.md`). Un estado con borde rojo rompe una regla. Uno con borde naranja la rompe en algunos casos. Las violaciones que vienen del código real están en [../violaciones/statecharts.md](../violaciones/statecharts.md).

Los modelos describen el código de `60c4a68` (`main`). El comando de cada sección vuelve a generar los archivos. `<skill statechart>` es la carpeta de la skill `statechart` de pstack. TLC tarda unos 2 s por modelo.

## 1. El jurado re-ejecuta el pipeline

El jurado clona el repo, baja el set final y corre `python pipeline.py --datos datos/final --entrega entrega`. El modelo cruza dos decisiones del jurado: qué commit usa (`main` o el `c7406f3` que generó `entrega/`) y si tiene `TYPESAFE_API_KEY`. Termina cuando compara su `entrega/` con la del repo.

```mermaid
---
title: "El jurado re-ejecuta el pipeline"
---
stateDiagram-v2
  state "Legend" as legend {
    lg0: corrida
    lg1: resultado
    lg2: Breaks CostoIgualAEntrega or PrediccionesIgualesAEntrega or SinClaveSinRed
    lg3: Breaks SinClaveSinRed in some cases
    lg4: Path to the CostoIgualAEntrega or PrediccionesIgualesAEntrega or SinClaveSinRed bug
  }
  class lg0 blue
  class lg1 orange
  class lg2 breaks
  class lg3 mayBreak
  class lg4 bugPath
  s0: Repo clonado (commit de la entrega, sin clave)
  s1: Repo clonado (commit de la entrega, con clave)
  s2: Repo clonado (main, sin clave)
  s3: Repo clonado (main, con clave)
  s4: Modelos bajados (commit de la entrega, sin clave)
  s5: Modelos bajados (commit de la entrega, con clave)
  s6: Modelos bajados (main, sin clave)
  s7: Modelos bajados (main, con clave)
  s8: Posturas decididas en local (commit de la entrega)
  s9: Posturas decididas en local (main)
  s10: Posturas decididas por Jev
  s11: Predicciones distintas a entrega/
  s12: Predicciones iguales, costo distinto
  [*] --> s0
  [*] --> s1
  [*] --> s2
  [*] --> s3
  s0 --> s4: baja los modelos de Hugging Face
  s1 --> s5: baja los modelos de Hugging Face
  s2 --> s6: baja los modelos de Hugging Face
  s3 --> s7: baja los modelos de Hugging Face
  s4 --> s8: decide postura con NLI local
  s5 --> s8: decide postura con NLI local
  s6 --> s9: decide postura con NLI local
  s7 --> s10: manda raíces dudosas a Jev
  s8 --> s12: escribe entrega/ y compara con la del repo
  s9 --> s11: escribe entrega/ y compara con la del repo
  s10 --> s11: escribe entrega/ y compara con la del repo
  classDef breaks fill:#ffecee,stroke:#e72e3b,stroke-width:2.5px,color:#cd2834
  classDef mayBreak fill:#fff3e6,stroke:#e8730c,stroke-width:2.5px,color:#b85a06
  class s0 blue
  class s1 blue
  class s2 blue
  class s2 bugPath
  class s3 blue
  class s4 blue
  class s4 breaks
  class s5 blue
  class s6 blue
  class s6 breaks
  class s6 bugPath
  class s7 blue
  class s8 blue
  class s8 mayBreak
  class s9 blue
  class s9 breaks
  class s9 bugPath
  class s10 blue
  class s11 orange
  class s11 breaks
  class s11 bugPath
  class s12 orange
  class s12 breaks
```

Reglas que se cumplen:

- **SinClaveNoLlamaJev.** Sin clave nunca se llama a la API de Jev. `DecisionEngine` baja a modo local si falta la clave (`decisores.py`, `DecisionEngine.__init__`).

Reglas que se rompen:

- **PrediccionesIgualesAEntrega.** Con `main` las predicciones no salen iguales a `entrega/`. Camino: repo clonado (main, sin clave) → baja modelos → decide en local → predicciones distintas. `entrega/` la generó `c7406f3`, y `main` trae NLI local y cambios de postura que FINAL_RUN.md declara sin aplicar. Con clave en `main`, el default `--decisor jev` también cambia las posturas.
- **CostoIgualAEntrega.** `costo.json` nunca sale igual, ni con `c7406f3`. La máquina del jurado no tiene `.cache/reportes/` (no está en git), así que guarda sus propios segundos y su `hardware`. Camino: el mismo de arriba.
- **SinClaveSinRed.** Sin clave igual hay red. En una máquina nueva `pipeline.embeddings` y `LocalNLI` bajan los pesos fijados desde Hugging Face. No es una API con clave ni tiene costo, pero sí es tráfico externo. Camino: repo clonado (main, sin clave) → baja los modelos de Hugging Face.

Qué deja afuera: fallos o timeouts de Jev (caen al decisor local), el contenido de las predicciones, el determinismo entre sistemas operativos (se asume), `HF_HUB_OFFLINE=1` con pesos ya bajados, y la descarga del set final y la verificación de SHA-256.

```sh
<skill statechart>/scripts/statechart docs/statecharts/jurado-reejecuta/JuradoReejecuta.tla --config docs/statecharts/jurado-reejecuta/JuradoReejecuta.cfg --view docs/statecharts/jurado-reejecuta/view.ts --out /tmp/jurado-reejecuta-nuevo
```

## 2. Entrega final: de la rama a main

El protocolo de `program.md` exige que un candidato pase la aceptación en la rama de mejoras, entre a `main`, se corra en frío sobre el set final y se suba junto con su `entrega/`. El modelo agrega el cierre real de FINAL_RUN.md: el push a `main` sin regeneración fría. La regla mira `origin/main`, lo que ve el jurado.

```mermaid
---
title: "Entrega final: de la rama a main"
---
stateDiagram-v2
  state "Legend" as legend {
    lg0: trabajo
    lg1: main
    lg2: Breaks MainTieneEntregaDeSuCodigo
    lg3: Path to the MainTieneEntregaDeSuCodigo bug
  }
  class lg0 blue
  class lg1 teal
  class lg2 breaks
  class lg3 bugPath
  s0: Candidato en la rama de mejoras
  s1: Main y entrega intactos
  s2: Candidato supera la referencia
  s3: Merge local, entrega vieja
  s4: Main publicado con entrega de otro código
  s5: Entrega regenerada en frío
  s6: Main publicado con su entrega
  [*] --> s0
  s0 --> s1: no supera a c7406f3
  s0 --> s2: pasa completo y las tres particiones
  s2 --> s3: merge a main
  s3 --> s4: push sin regenerar [cierre apurado]
  s3 --> s5: corre el set final sin caché de embeddings
  s5 --> s6: commit y push de código y entrega/
  classDef breaks fill:#ffecee,stroke:#e72e3b,stroke-width:2.5px,color:#cd2834
  class s0 blue
  class s0 bugPath
  class s1 teal
  class s2 blue
  class s2 bugPath
  class s3 blue
  class s3 bugPath
  class s4 teal
  class s4 breaks
  class s4 bugPath
  class s5 blue
  class s6 teal
```

Reglas que se rompen:

- **MainTieneEntregaDeSuCodigo.** `origin/main` publica código cuyo `entrega/` salió de otro commit. Camino: candidato en la rama → pasa completo y las tres particiones → merge a main → push sin regenerar. Es el estado actual: `60c4a68` tiene el código de la experiencia 145 y `entrega/` de `8a1f5be` (código `c7406f3`). El camino planeado (merge → corrida en frío → commit y push) sí cumple la regla.

Qué deja afuera: la validación de formato de `entrega/` (siempre pasa en el modelo), una corrida en frío que falla o no entra en el plazo, el chequeo de que la caché de embeddings esté vacía (nada en el código lo exige), y el estado intermedio del `main` local.

```sh
<skill statechart>/scripts/statechart docs/statecharts/entrega-final/EntregaFinal.tla --config docs/statecharts/entrega-final/EntregaFinal.cfg --view docs/statecharts/entrega-final/view.ts --out /tmp/entrega-final-nuevo
```

## 3. Un experimento del loop de mejora

Cada hipótesis edita `pipeline.py`, corre `eval.py` sobre el completo y las tres particiones, y se marca aceptada o descartada en `experiments.tsv`. El modelo sigue un solo experimento hasta que se cierra. `empeora` dice si alguna partición perdió puntos de la tarea.

```mermaid
---
title: "Un experimento del loop de mejora"
---
stateDiagram-v2
  state "Legend" as legend {
    lg0: corrida
    lg1: registro
    lg2: cierre
    lg3: Breaks AceptadaNoEmpeoraParticion or TodaCorridaRegistrada
    lg4: Path to the AceptadaNoEmpeoraParticion or TodaCorridaRegistrada bug
  }
  class lg0 blue
  class lg1 purple
  class lg2 teal
  class lg3 breaks
  class lg4 bugPath
  s0: Hipótesis declarada (A, B o mixta)
  s1: Cambio sin commitear
  s2: Corrida cortada, sin fila
  s3: Fila pendiente, ninguna partición empeora
  s4: Fila pendiente, alguna partición empeora
  s5: Ciclo cerrado sin fila
  s6: Código commiteado, ninguna partición empeora
  s7: Fila descartada, diff por revertir
  s8: Código commiteado, alguna partición empeora
  s9: Fila aceptada, ninguna partición empeora
  s10: Cerrado descartado, fila guardada
  s11: Fila aceptada, alguna partición empeora
  s12: Cerrado aceptado, ninguna partición empeora
  s13: Cerrado aceptado, alguna partición empeora
  [*] --> s0
  s0 --> s1: edita pipeline.py
  s1 --> s2: eval.py falla o se pasa de tiempo
  s1 --> s3: eval.py puntúa completo y tres particiones
  s1 --> s4: eval.py puntúa completo y tres particiones
  s2 --> s5: revierte el cambio
  s3 --> s6: commit del código
  s3 --> s7: eval.py --marcar discarded
  s4 --> s8: commit del código
  s4 --> s7: eval.py --marcar discarded
  s6 --> s9: eval.py --marcar accepted
  s7 --> s5: git reset --hard
  s7 --> s10: revierte sólo su diff
  s8 --> s11: eval.py --marcar accepted
  s9 --> s12: commit de la bitácora
  s11 --> s13: commit de la bitácora
  classDef breaks fill:#ffecee,stroke:#e72e3b,stroke-width:2.5px,color:#cd2834
  class s0 blue
  class s0 bugPath
  class s1 blue
  class s1 bugPath
  class s2 blue
  class s2 bugPath
  class s3 purple
  class s4 purple
  class s4 bugPath
  class s5 teal
  class s5 breaks
  class s5 bugPath
  class s6 purple
  class s7 purple
  class s8 purple
  class s8 bugPath
  class s9 purple
  class s10 teal
  class s11 purple
  class s11 breaks
  class s11 bugPath
  class s12 teal
  class s13 teal
  class s13 breaks
```

Reglas que se rompen:

- **TodaCorridaRegistrada.** Una corrida que falla o se pasa de tiempo no deja fila. Camino: hipótesis → edita → eval.py falla o se pasa de tiempo → revierte. `eval.invoke_pipeline` lanza `RuntimeError` antes de `append_experiment`. El otro camino que la rompe es `git reset --hard` después de `--marcar discarded`: `experiments.tsv` está en git y la fila todavía no se commiteó.
- **AceptadaNoEmpeoraParticion.** `eval.py --marcar accepted` acepta aunque una partición haya empeorado. Camino: hipótesis → edita → puntúa (alguna partición empeora) → commit del código → `--marcar accepted`. `mark_experiment` sólo cambia el estado. La comparación por tarea y partición contra el comparador de `program.md` la hace a mano quien corre el loop. Además `dia_1_10` no tiene columna en el TSV, sólo aparece dentro de `componentes`.

Qué deja afuera: el puntaje concreto, la elección de tarea A/B/mixta, el piso de precisión ≥0,9, el desempate por tiempo, varias filas pendientes a la vez y el loop entre experimentos (se modela uno).

```sh
<skill statechart>/scripts/statechart docs/statecharts/experimento-loop/ExperimentoLoop.tla --config docs/statecharts/experimento-loop/ExperimentoLoop.cfg --view docs/statecharts/experimento-loop/view.ts --out /tmp/experimento-loop-nuevo
```

## 4. Demo: recorrer el vault de Obsidian

`export_vault.py` escribe `index.md`, una nota por narrativa, por operación y por fuente. Los enlaces reales son índice → narrativa y operación, narrativa ↔ operación, y las dos hacia y desde fuentes. Ninguna nota enlaza de vuelta al índice. El modelo distingue si existen los Parquet auxiliares de `salida/final/`, que no están en git.

```mermaid
---
title: "Demo: recorrer el vault de Obsidian"
---
stateDiagram-v2
  state "Legend" as legend {
    lg0: indice
    lg1: narrativa
    lg2: otras
    lg3: Breaks OperacionListadaImplicaAmplificada
    lg4: Path to the OperacionListadaImplicaAmplificada bug
  }
  class lg0 teal
  class lg1 purple
  class lg2 tan
  class lg3 breaks
  class lg4 bugPath
  s0: Índice
  s1: Narrativa sin operación
  s2: Operación coordinada
  s3: Narrativa con operación, 0 días amplificada
  s4: Narrativa amplificada, con su operación
  s5: Fuente (medio)
  [*] --> s0
  s0 --> s1: abre una narrativa de la tabla
  s0 --> s2: abre una operación de la tabla
  s0 --> s3: abre una narrativa [sin salida/final]
  s0 --> s4: abre una narrativa de la tabla
  s1 --> s0: vuelve con Atrás (no hay enlace al índice)
  s1 --> s5: abre una fuente relacionada
  s2 --> s3: abre una narrativa que empuja
  s2 --> s5: abre una fuente relacionada
  s3 --> s0: vuelve con Atrás (no hay enlace al índice)
  s3 --> s5: abre una fuente relacionada
  s3 --> s2: abre la operación relacionada
  s2 --> s4: abre una narrativa que empuja
  s4 --> s0: vuelve con Atrás (no hay enlace al índice)
  s4 --> s5: abre una fuente relacionada
  s4 --> s2: abre la operación relacionada
  s5 --> s2: abre una operación del medio
  classDef breaks fill:#ffecee,stroke:#e72e3b,stroke-width:2.5px,color:#cd2834
  class s0 teal
  class s0 bugPath
  class s1 purple
  class s2 tan
  class s3 purple
  class s3 breaks
  class s3 bugPath
  class s4 purple
  class s5 tan
```

Reglas que se cumplen:

- **NarrativaAmplificadaEnlazaOperacion.** Si una narrativa muestra días amplificada, su nota enlaza a la operación. El salto narrativa → operación existe (`operation_links_by_narrative`) y la operación vuelve con «Narrativas que empuja».

Reglas que se rompen:

- **OperacionListadaImplicaAmplificada.** Sin `salida/final/` la nota lista una operación y dice `dias_amplificada: 0`. Camino: índice → abre una narrativa [sin salida/final]. Reproducido con `entrega/` y el set final: `narrativa-n002.md` lista operaciones y muestra `volumen_total: 5`, `estado_actual: "desconocido"` y `dias_amplificada: 0`. Con los Parquet presentes la regla se cumple, porque `estados_por_dia` marca amplificado al menos el día de mayor cuota coordinada.

Qué deja afuera: Dataview, Quartz, el contenido de cada nota, cuántas narrativas u operaciones hay y el botón Atrás de Obsidian como historial (se modela como volver al índice). Oculta los saltos fuente → narrativa y la vuelta al índice desde operación y fuente, que repiten flechas ya dibujadas.

```sh
<skill statechart>/scripts/statechart docs/statecharts/demo-vault/DemoVault.tla --config docs/statecharts/demo-vault/DemoVault.cfg --view docs/statecharts/demo-vault/view.ts --out /tmp/demo-vault-nuevo
```
