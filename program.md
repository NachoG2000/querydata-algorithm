# Experimentos y criterio de aceptación

## Restricciones de ingeniería

1. **Un comando, determinista.** `python pipeline.py --datos <dir> --entrega <dir>`. Semillas fijas en todo lo estocástico (UMAP, HDBSCAN, muestreos, cualquier orden de iteración). Dos corridas iguales dan archivos idénticos.
2. **Funciona sin claves.** El modo local es 100% local y se selecciona explícitamente para comparar variantes. Jev se activa sólo si existe `TYPESAFE_API_KEY`; sin clave se conserva el reemplazo local. La integración de `.env` y el selector Jev se desarrollan en la misma rama de mejoras.
3. **Cero secretos en git.** Claves en variables de entorno, `.env` en `.gitignore`, `.env.example` commiteado.
4. **Todo gasto medido.** Cada llamada externa pasa por un wrapper que cuenta tokens, dólares y latencia, y lo vuelca en `costo.json`. También se reporta qué fracción de comentarios necesitó IA.
5. **Datos sucios.** Textos vacíos, fechas mal formadas, `respuesta_a` que apunta a comentarios inexistentes, duplicados: se manejan sin romper, y se loguea cuántos hubo.
6. **Nada específico del set de práctica.** Prohibido codificar palabras, frases, temas, número de narrativas o de campañas, o umbrales absolutos ajustados a mano. Preferir umbrales relativos a los datos: percentiles, ventanas estimadas de la distribución, comparaciones contra lo esperable.
7. **La verdad es solo para medir.** Se usa a través de `puntuar.py`. Puedes leer las descripciones de narrativas y campañas una sola vez para entender qué TIPOS de fenómenos y trampas existen, y anotarlo en `NOTES.md` en términos genéricos, nunca su contenido.

Nota sobre costos: el agente que desarrolla (esta sesión y la nocturna) corre con la suscripción de Claude y NO es costo del pipeline. Cualquier IA que use el pipeline al correr sí lo es.

## Protocolo vigente: aceptación por tarea

Esta regla reemplaza la aceptación histórica por métrica combinada y margen 0,20. `evaluacion/puntuar.py` y los datos permanecen congelados. La única modificación autorizada a `eval.py` es agregar `dia_1_10`: los primeros diez días locales, del mismo largo que el set final. El resto se conserva exactamente como en `c7406f3`. La columna combinada que imprime el arnés se conserva para el historial; no decide la aceptación. El diagnóstico solicitado en `NOTES.md` autoriza una auditoría de la verdad para medir evidencia y mezclas, nunca para introducir vocabulario, IDs, temas, cantidades de campañas o fechas de práctica en producción.

1. Antes de editar, declara tarea **A** (narrativas), **B** (coordinación) o **mixta**, y una hipótesis genérica. El trabajo nuevo se hace exclusivamente en `mejora-a`. Se integran los cambios de Jev solicitados; las hipótesis cambian `pipeline.py` y la configuración o implementación local de decisiones cuando sea necesario para NLI. No se vuelve a modificar el arnés ni el scorer.
2. Usa exclusivamente los puntos oficiales de `puntuar.py`: `narrativas.puntos` (hasta 30) para A y `coordinacion.puntos` (hasta 25) para B. Los subcomponentes se registran para explicar el resultado; no se sustituyen por una métrica propia.
3. Para la tarea elegida, el completo debe mejorar y ninguna de las tres particiones bloqueantes (`dia_1_7`, `dia_8_14`, `dia_1_10`) puede perder puntos de esa tarea frente a su propio comparador. En una hipótesis mixta, ambas tareas deben conservar completo y particiones, y al menos una debe mejorar. Registra siempre el efecto sobre la otra tarea; no atribuyas una mejora de B a los puntos de A.
4. Para B, prioriza recall con **precisión oficial ≥0,9** en el completo y en cada partición con predicciones. No declarar precisión alta si no hay predicciones: allí se sigue contrastando el puntaje y la disponibilidad de evidencia. Una partición con actividad y detección vacía no se omite.
5. El tiempo sólo desempata puntajes iguales. Si sólo cambia el tiempo, repite la medición y compara medianas. Un aumento de **más de 30%** en tiempo de pipeline completo, con hardware, modo local, resto de etapas y caché comparables, bloquea el cambio. No compares ese tiempo con una arquitectura de A distinta, como TF-IDF de la base. El presupuesto del arnés sigue siendo 10 minutos por experimento; preparar modelos y embeddings antes de medir.
6. Referencia protegida: el código de `c7406f3`, idéntico al que generó la entrega publicada en `main` con `8a1f5be`. A = **13,37 / 11,58 / 17,25** y B = **19,79 / 5,63 / 12,14** en completo / días 1–7 / días 8–14. Se mide además la referencia de días 1–10 con ese mismo código y el arnés extendido antes de aceptar cambios. Las referencias vigentes completas están en el registro de la rama y en `.cache/mejora-a/reference.json`. Las aceptaciones antiguas no reemplazan este comparador.
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
6. Continúa hasta que el usuario indique parar, 55/55 en el completo y las tres particiones, 120 filas nuevas desde las 139 iniciales (máximo 259), o el límite de cuatro horas iniciado el 13/11/2026 a las **08:57:35 de Salta**. El límite total es **12:57:35 de Salta** (15:57:35 UTC), incluyendo el cierre. Se reserva tiempo dentro de ese máximo para la regeneración final con embeddings desde cero y las comprobaciones. El corte de nuevas pruebas se ajusta al tiempo medido de preparación NLI y al menos a los 856,1 s de la codificación final anterior, con margen; no se inicia una prueba que impida cerrar dentro del límite.

## Protección de main y cierre

- `main` y `origin/main` conservan `8a1f5be` y los cuatro archivos de entrega del set final, verificados contra el manifiesto de hashes. El código de `pipeline.py` es el mismo de `c7406f3`. Todo trabajo posterior, incluida la integración Jev, permanece en `mejora-a` hasta pasar la aceptación.
- Se compara cada candidato con el mejor admisible de su tarea en el completo y las tres particiones. Se registra el efecto sobre la otra tarea. Para promover a `main`, el candidato debe superar a `c7406f3` en A o B, conservar ambas tareas en las cuatro ventanas y mantener precisión ≥0,9 cuando se cambie coordinación. Una mejora de tiempo sola no basta para promover.
- Si hay un mejor candidato admisible, se integra a `main`, se corre sobre el set final con una carpeta de caché de embeddings vacía (los pesos públicos descargados pueden reutilizarse), y se reemplaza `entrega/` exclusivamente por la salida automática de esa corrida. `costo.json` conserva el costo y tiempo de esa corrida real. Se vuelve a commitear y subir la entrega con su código.
- Si no lo hay, `main` y la entrega quedan intactos. En ambos casos se comprueba funcionamiento sin claves, dos corridas con archivos idénticos y estado de Git limpio en el worktree de la tarea. El worktree original con cambios ajenos se preserva. El estado de la rama, referencias, hashes y plazo se registran en `.cache/mejora-a/goal-state.json`.

## Backlog, en este orden

1. **Postura.** Activar NLI multilingüe local para raíces y para la relación con el padre en respuestas. Calibrar umbrales con el completo y las tres particiones. Deduplicar y cachear inferencias locales por modelo, revisión, tokenización y textos; preparar las inferencias antes de medir comparaciones con caché comparable. Jev sólo con `TYPESAFE_API_KEY`; sin clave el pipeline debe seguir funcionando.
2. **Emergentes.** Dentro de cada cluster, detectar subgrupos con comienzo posterior y centroide distinto, y partirlos. Resolver los clusters propios antes de ajustar `fecha_origen`. No asumir fechas ni número de narrativas.
3. **Agrupamiento.** Atacar la causa dominante de 1a. El diagnóstico de esta rama encuentra mayor pérdida de recall B-cubed: priorizar fusión de fragmentos por centroide, conservando la separación de subgrupos emergentes. Si otra medición muestra fusión dominante, usar clusters más finos o partición jerárquica. Medir ambos componentes.
4. **Ruido.** Calibrar exclusión de comentarios sin afirmación, preservando respuestas con relación válida al padre y sin convertirlas automáticamente en ruido por longitud.
5. **Recall de coordinación en períodos cortos.** Umbrales normalizados por exposición y oportunidades, medidos también en días 1–10, manteniendo precisión oficial ≥0,9. La primera mitad sigue bloqueando; no se exime por su mal resultado.
6. **Fragmentación de operaciones.** Consolidar sólo con evidencia independiente repetida, sin fijar el número de campañas ni introducir IDs o contenido de la verdad.

## Cierre solicitado por el usuario

El 13/11/2026 el usuario pidió terminar la iteración en curso, pushear todo a main y parar. La iteración 147 se descartó; la mejor aceptada es la 145. Luego indicó que no había tiempo para esperar más. Se detuvo el loop y se conserva sin cambios la entrega final generada por c7406f3 y publicada en 8a1f5be. La regeneración fría prevista queda pendiente: las mejoras de postura del código nuevo aún no se aplicaron a esos cuatro archivos. Se suben código validado, diagnóstico, protocolo y registro completo de experimentos. No se inicia ninguna otra hipótesis.
