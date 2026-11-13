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

## Bucle de trabajo

1. Lee `RESULTS.md`, la última fila aceptada en `experiments.tsv` y el último commit. Usa el mismo hardware, modo local y caché de embeddings para comparar tiempos.
2. Escribe una hipótesis y cambia solo `pipeline.py`. Si necesitas ajustar el decisor, cambia solo sus `PARAMS` cuando existan. Mantén `eval.py`, `evaluacion/puntuar.py` y los datos congelados.
3. Ejecuta `python eval.py --resumen "hipótesis"`. El presupuesto máximo de evaluación es 10 minutos por experimento. La descarga de otro modelo se prepara antes de medir.
4. Conserva el cambio si sube `completo` frente a la última fila aceptada y cada mitad cae como máximo 0,20 puntos combinados frente a su propio valor anterior. La métrica resta 0,001 puntos por segundo de pipeline y un punto por USD por mil comentarios.
5. Si pasa, haz un commit de código que explique la hipótesis y ejecuta `python eval.py --marcar accepted`. Si falla, ejecuta `python eval.py --marcar discarded`, quita los cambios experimentales del índice con `git reset -- pipeline.py decisores.py` y restaura solo esos cambios. Conserva su fila del TSV. Si había cambios ajenos, restaura solo el diff del experimento.
6. Descarta cualquier mejora que dependa del tema, frases, etiquetas, fechas concretas o cantidad de grupos de práctica. Una vez aceptado un cambio, mantén un único commit de código por hipótesis.
7. Si se corta la sesión, lee `experiments.tsv` y `git log -1`. Revisa el diff antes de decidir si terminas o descartas la fila pendiente. El TSV conserva el historial incluso si se descarta el código.

Las ventanas contienen días locales 1–7 y 8–14 de práctica. Se corre el pipeline de cero en cada ventana, con los embeddings fijos reutilizados. El puntaje de origen de una emergente se incluye en la ventana que contiene el origen real.

## Backlog inicial

1. Compara MiniLM, MPNet multilingüe y E5-small. Fija cada revisión y precalcula su caché.
2. Barre `min_cluster_size`, `min_samples` y `n_neighbors`. Vigila precisión y recall de B-cubed para detectar fragmentación.
3. Evalúa filtros de afirmación, persistencia y cuentas distintas. Mide el efecto de descontar coordinadas antes de validar.
4. Une variantes temporales de una misma afirmación y comprueba que una reaparición conserva su ID.
5. Compara la fecha del primer comentario del núcleo con estimadores que consideren borde y persistencia.
6. Compara la similitud de mismo guion y las ventanas estimadas por publicación. Mide cuentas genuinas marcadas.
7. Barre peso mínimo de aristas y compara Louvain con otra detección de comunidades.
8. Compara NLI local y Jev en casos ambiguos. Varía la cobertura según confianza y registra costo y latencia.
