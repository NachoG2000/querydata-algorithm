# Experimentos nocturnos

## Restricciones de ingeniería

1. **Un comando, determinista.** `python pipeline.py --datos <dir> --entrega <dir>`. Semillas fijas en todo lo estocástico (UMAP, HDBSCAN, muestreos, cualquier orden de iteración). Dos corridas iguales dan archivos idénticos.
2. **Funciona sin claves.** El modo por defecto es 100% local. Las APIs externas (Jev, un LLM) son opcionales y se activan solo si existe su variable de entorno. Sin clave, cada paso tiene un reemplazo local que produce salida válida.
3. **Cero secretos en git.** Claves en variables de entorno, `.env` en `.gitignore`, `.env.example` commiteado.
4. **Todo gasto medido.** Cada llamada externa pasa por un wrapper que cuenta tokens, dólares y latencia, y lo vuelca en `costo.json`. También se reporta qué fracción de comentarios necesitó IA.
5. **Datos sucios.** Textos vacíos, fechas mal formadas, `respuesta_a` que apunta a comentarios inexistentes, duplicados: se manejan sin romper, y se loguea cuántos hubo.
6. **Nada específico del set de práctica.** Prohibido codificar palabras, frases, temas, número de narrativas o de campañas, o umbrales absolutos ajustados a mano. Preferir umbrales relativos a los datos: percentiles, ventanas estimadas de la distribución, comparaciones contra lo esperable.
7. **La verdad es solo para medir.** Se usa a través de `puntuar.py`. Puedes leer las descripciones de narrativas y campañas una sola vez para entender qué TIPOS de fenómenos y trampas existen, y anotarlo en `NOTES.md` en términos genéricos, nunca su contenido.

Nota sobre costos: el agente que desarrolla (esta sesión y la nocturna) corre con la suscripción de Claude y NO es costo del pipeline. Cualquier IA que use el pipeline al correr sí lo es.

## Protocolo vigente: aceptación por tarea

Esta regla reemplaza la aceptación histórica por métrica combinada y margen 0,20. `eval.py`, `evaluacion/puntuar.py` y los datos permanecen congelados. La columna combinada que imprime el arnés se conserva para el historial; no decide la aceptación. El diagnóstico solicitado en `NOTES.md` autoriza una auditoría de la verdad para medir evidencia y mezclas, nunca para introducir vocabulario, IDs, temas, cantidades de campañas o fechas de práctica en producción.

1. Antes de editar, declara tarea **A** (narrativas), **B** (coordinación) o **mixta**, y una hipótesis genérica. Sólo cambia `pipeline.py`; como máximo, `PARAMS` de `decisores.py` cuando corresponda.
2. Usa exclusivamente los puntos oficiales de `puntuar.py`: `narrativas.puntos` (hasta 30) para A y `coordinacion.puntos` (hasta 25) para B. Los subcomponentes se registran para explicar el resultado; no se sustituyen por una métrica propia.
3. Para la tarea elegida, el completo debe mejorar y ninguna partición bloqueante puede perder puntos de esa tarea frente a su propio comparador. En una hipótesis mixta, ambas tareas deben conservar completo y particiones, y al menos una debe mejorar. Registra siempre el efecto sobre la otra tarea; no atribuyas una mejora de B a los puntos de A.
4. Para B, prioriza recall con **precisión oficial ≥0,9** en el completo y en cada partición con predicciones. No declarar precisión alta si no hay predicciones: allí se sigue contrastando el puntaje y la disponibilidad de evidencia. Una partición con actividad y detección vacía no se omite.
5. El tiempo sólo desempata puntajes iguales. Si sólo cambia el tiempo, repite la medición y compara medianas. Un aumento de **más de 30%** en tiempo de pipeline completo, con hardware, modo local, resto de etapas y caché comparables, bloquea el cambio. No compares ese tiempo con una arquitectura de A distinta, como TF-IDF de la base. El presupuesto del arnés sigue siendo 10 minutos por experimento; preparar modelos y embeddings antes de medir.
6. Referencias iniciales de esta revisión: A = **13,13 / 11,46 / 17,20**, evaluada en las variantes 15/31. B = base oficial **9,44 / 1,60 / 0,39** (completo / días 1–7 / días 8–14), precisión 1 / 1 / sin predicciones. La variante 31 no se usa como comparador admisible de B: su precisión completa es 0,0998. Establecer una implementación de B admisible al retomar; no conservar el antiguo punto de operación por haber sido aceptado con la regla anterior.
7. **Días 1–7 sigue bloqueando B.** El diagnóstico encuentra 114 cuentas coordinadas activas, 597 comentarios, 16 pares con repetición exacta y 34 con repetición semántica de coseno ≥0,9 en la ventana diagnóstica común; la segunda mitad tiene 113, 468, 11 y 39. No se aplica la excepción de actividad insuficiente. La ausencia de detección de la variante 23 es evidencia de umbrales que no generalizan. Cualquier futura excepción requiere otra auditoría documentada de evidencia, no un mal puntaje del detector.

## Umbrales y evidencia de coordinación

- Obtener duración efectiva, volumen, publicaciones y oportunidades por cuenta de la entrada actual. Nada debe asumir 14 días: el final tiene 10 y las validaciones, una fracción del volumen.
- Expresar evidencia como tasas, exceso respecto de un nulo o cuantiles calibrados con esas oportunidades. El soporte de repetición y los límites de comunidad deben ajustarse a la exposición observada, no copiar cuentas/eventos absolutos del set completo a una mitad.
- Estimar escalas temporales con la distribución de retrasos de coincidencias y actividad por publicación. El intervalo entre comentarios generales no equivale al retraso de un guion coordinado. Calibrar similitud con la geometría del modelo y el fondo del corpus; longitud, soporte y tamaño de ráfaga usan distribuciones relativas al volumen. Los límites de cómputo se distinguen de los umbrales de decisión y no deben descartar operaciones por un tamaño fijo aprendido de práctica.
- La exigencia lógica de repetición necesita al menos dos eventos independientes; no es un corte ajustado a la duración. Identificar y deduplicar eventos: pasar texto exacto y coseno para el mismo par de comentarios no suma dos votos. Documentar y medir cómo cambia el soporte al acortar la exposición.
- Nunca codificar IDs, etiquetas de verdad, palabras, temas, fechas o número de narrativas/campañas. La verdad queda fuera del pipeline. Las consultas diagnósticas no se convierten en reglas específicas del set.

## Bucle de trabajo y recuperación

1. Lee `NOTES.md`, este protocolo, las referencias admisibles por tarea en `experiments.tsv` y el último commit. No uses automáticamente la última fila histórica `accepted` si pertenece al protocolo anterior o viola el piso de precisión.
2. Congela el resto de etapas, escribe la hipótesis con etiqueta A/B/mixta y modifica sólo los archivos permitidos. Verifica también la escala temporal y de volumen de cualquier umbral de B.
3. Ejecuta `python eval.py --resumen "[A|B|mixta; protocolo por tarea] hipótesis y referencia"`. Registra puntos oficiales por tarea y partición, precisión/recall, agrupación de operaciones, tiempos y costo. No edites el scorer ni las particiones para favorecer el experimento.
4. Si pasa, un único commit de código por hipótesis aceptada y `python eval.py --marcar accepted`. Si falla, `python eval.py --marcar discarded` y restaura sólo el diff propio del experimento; conserva su fila del TSV. Los commits de bitácora pueden agrupar filas, conservando la mejor configuración.
5. Si se corta la sesión, revisa fila pendiente, diff, procesos y logs antes de repetir. Completa o descarta el experimento según este protocolo. No borres cambios ajenos.
6. Continúa hasta puntuar 55/55 en completo y ambas particiones, las 07:00 de Argentina del viernes 13/11/2026, o 150 filas de experimentos. Al cerrar: mejor configuración en el último commit, reevaluación sobre ese commit, dos corridas con archivos idénticos, modo sin claves y `git status` limpio.

## Backlog, en este orden

1. **Recall de cuentas con precisión ≥0,9.** Similitud por embeddings para paráfrasis y grafo de repeticiones independientes; combinar evidencia complementaria sin multiplicar falsos positivos. Escalar soporte a duración y volumen, contrastando las tres particiones.
2. **Fragmentación de operaciones.** Comprobar si distintos guiones de una misma operación quedan en comunidades separadas; comparar agrupación y unión con evidencia repetida. No fijar la cantidad de campañas.
3. **Emergentes con clusters propios, después `fecha_origen`.** Resolver primero mezclas con narrativas anteriores y fragmentación; sólo después estimar origen robusto del núcleo. Comparar representaciones, densidad y fusiones adaptativas sin lista de temas. Los modelos alternativos descargados pueden prepararse cuando se aborde esta tarea.
4. **Postura por aristas.** Evaluar relación con el padre, herencia e inversión de postura; conservar el tratamiento de huérfanos y ciclos. NLI o Jev son opcionales y no reemplazan el camino local.
