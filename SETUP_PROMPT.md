# Prompt de setup: desafío QualyData (track Big Data)

## 0. Quién eres y qué hacemos en esta sesión

Eres el ingeniero principal de un equipo que compite en el Hackathon Argentina Space 2026 (Centro de Convenciones de Salta, 11 al 13 de noviembre de 2026), track Big Data de QualyData.

Esta sesión es SOLO de setup. No optimices el puntaje. El objetivo es dejar un repositorio, una arquitectura y un arnés de evaluación sólidos para que otra sesión de agente itere toda la noche de forma autónoma (patrón "autoresearch" de Karpathy: el agente edita un solo archivo, corre, mide, conserva o descarta, repite).

Fechas que importan:
- Hoy es jueves 12 de noviembre de 2026.
- El viernes 13 a la mañana se publica el set final. Ese día se corre el pipeline, se pushea `entrega/`, se carga el proyecto en Hacki y se hace el pitch.
- La ventana real para iterar es la noche del jueves al viernes. Todo lo que hagas tiene que acortar el tiempo por experimento.

Antes de escribir código, lee completo el enunciado oficial: https://github.com/qualydata-org/desafio-qualydata (README, `ejemplos/linea_base.py`, `evaluacion/puntuar.py`). Si algo de este prompt contradice el enunciado, manda el enunciado: anótalo en `NOTES.md` y sigue.

---

## 1. El problema

QualyData integra grandes volúmenes de datos de múltiples fuentes para modelar escenarios. El desafío: dada una conversación pública con miles de comentarios, responder rápido y barato tres preguntas: **qué circula, desde cuándo y quién lo empuja**.

- **Tarea A, narrativas.** Una narrativa es una afirmación o encuadre que se repite con distintas palabras (ejemplo del enunciado: "la obra está parada porque se robaron la plata"). Hay que descubrirlas sin lista previa, asignar cada comentario a una narrativa o marcarlo como ruido, dar su postura (apoya/rechaza) y estimar la fecha de origen de cada narrativa.
- **Tarea B, coordinación.** Detectar cuentas que actúan coordinadas (mismo texto, mismo momento, mismos lugares, una y otra vez) y agruparlas por operación, separándolas de la opinión genuina.

### Datos (todos sintéticos)

| Archivo | Contenido |
|---|---|
| `fuentes.csv` | 8 fuentes: medios, radios, comunidades, instituciones |
| `publicaciones.csv.gz` | ~500 publicaciones en 14 días |
| `comentarios.csv.gz` | 200.000 comentarios: `comentario_id, publicacion_id, cuenta_id, fecha, texto, respuesta_a, me_gusta` |
| `cuentas.csv.gz` | ~16.000 cuentas: `cuenta_id, usuario, fecha_creacion, seguidores, siguiendo` |

Fechas en hora argentina (-03:00). `respuesta_a` es el comentario al que responde o vacío.

El set incluye a propósito: narrativas que cambian de redacción con los días, narrativas que aparecen a mitad del período (rumores), ruido (reacciones, menciones, fuera de tema), campañas coordinadas de distintos estilos (fáciles y difíciles) y trampas (momentos virales genuinos donde mucha gente comenta a la vez, y frases que se copian sin coordinación).

El set final: misma estructura, ~150.000 comentarios en 10 días, otros temas, otras narrativas, otras campañas.

### Entrega (`entrega/`, formato exacto del enunciado)

- `comentarios.csv`: `comentario_id, narrativa, postura` (narrativa vacía o `ninguna` si es ruido; postura `apoya` o `rechaza`).
- `narrativas.csv`: `narrativa, titulo, frases_clave, fecha_origen` (ISO con zona horaria).
- `cuentas.csv`: `cuenta_id, grupo` (vacío si es genuina).
- `costo.json`: comentarios procesados, segundos, tokens de IA, USD de IA, USD por mil comentarios, hardware, almacenamiento, notas.

Reglas fijas de postura del enunciado:
- Las respuestas cortas que solo acompañan ("Tal cual", "Exacto") heredan narrativa y postura del comentario al que responden.
- Una respuesta que contradice al anterior pertenece a la misma narrativa con la postura opuesta.

### Puntaje (100)

| Criterio | Puntos | Cómo |
|---|---|---|
| Narrativas | 30 | Automático: 50% agrupamiento (B-cubed F1 sobre comentarios con narrativa), 15% ruido (F1 de "ninguna"), 20% postura (macro-F1), 15% origen de narrativas emergentes (completo a menos de 3 h, cero a 48 h) |
| Coordinación | 25 | Automático: 70% detección de cuentas (F1), 30% agrupamiento por operación (B-cubed F1) |
| Costo, escala y almacenamiento | 20 | Jurado: `costo.json`, tiempo, dónde y por qué guardamos los datos, cómo escalaría a millones de comentarios por día |
| Robustez | 15 | Jurado: corre con un comando, maneja datos sucios, reproducible |
| Claridad y visualización | 10 | Jurado: ¿se entiende en un minuto qué circula, desde cuándo y quién lo empuja? |

La línea base del repo (TF-IDF + k-means, postura por lista de palabras, mismo texto en ráfagas) saca ~17 de 55 automáticos.

### Reglas excluyentes

- Repo público con `entrega/` commiteada, video de demo y pitch.
- README que explique cómo correr el pipeline, dónde guardamos los datos y por qué esa base, y qué código o librerías existían antes del evento.
- El pipeline corre de punta a punta con un comando sobre el set final. Nada de etiquetado manual. El jurado puede volver a correrlo.
- Sin claves ni secretos en el repo.
- Se permite IA, pero todo gasto va en `costo.json`. La consigna pide usarla donde suma y no como único motor.

---

## 2. Restricciones de ingeniería (no negociables)

1. **Un comando, determinista.** `python pipeline.py --datos <dir> --entrega <dir>`. Semillas fijas en todo lo estocástico (UMAP, HDBSCAN, muestreos, cualquier orden de iteración). Dos corridas iguales dan archivos idénticos.
2. **Funciona sin claves.** El modo por defecto es 100% local. Las APIs externas (Jev, un LLM) son opcionales y se activan solo si existe su variable de entorno. Sin clave, cada paso tiene un reemplazo local que produce salida válida.
3. **Cero secretos en git.** Claves en variables de entorno, `.env` en `.gitignore`, `.env.example` commiteado.
4. **Todo gasto medido.** Cada llamada externa pasa por un wrapper que cuenta tokens, dólares y latencia, y lo vuelca en `costo.json`. También se reporta qué fracción de comentarios necesitó IA.
5. **Datos sucios.** Textos vacíos, fechas mal formadas, `respuesta_a` que apunta a comentarios inexistentes, duplicados: se manejan sin romper, y se loguea cuántos hubo.
6. **Nada específico del set de práctica.** Prohibido codificar palabras, frases, temas, número de narrativas o de campañas, o umbrales absolutos ajustados a mano. Preferir umbrales relativos a los datos: percentiles, ventanas estimadas de la distribución, comparaciones contra lo esperable.
7. **La verdad es solo para medir.** Se usa a través de `puntuar.py`. Puedes leer las descripciones de narrativas y campañas una sola vez para entender qué TIPOS de fenómenos y trampas existen, y anotarlo en `NOTES.md` en términos genéricos, nunca su contenido.

Nota sobre costos: el agente que desarrolla (esta sesión y la nocturna) corre con la suscripción de Claude y NO es costo del pipeline. Cualquier IA que use el pipeline al correr sí lo es.

---

## 3. Modelo conceptual: dos máquinas de estado

El desafío se resuelve en lote (tenemos todos los días de entrada), pero diseñamos con estas máquinas de estado porque: (a) ordenan las decisiones del pipeline, (b) alimentan la demo y el vault de Obsidian, y (c) demuestran el argumento de escala (el mismo código puede correr en modo streaming). En lote, cada transición puede mirar el pasado y el futuro del grupo; en streaming, solo el pasado.

### 3.1 Ciclo de vida de una narrativa

```
Comentario suelto ──(aparecen otros cercanos en significado)──▶ Candidata
Candidata ──(no se sostiene)──▶ vuelve a ruido
Candidata ──(pasa los filtros de validación)──▶ Narrativa nacida (se fija fecha_origen)
Narrativa nacida ──(crece)──▶ Activa
Activa ⇄ Mutando        (la redacción deriva pero el significado se mantiene)
Activa ⇄ Amplificada    (cuentas coordinadas la empujan; es un atributo, puede pasar desde el nacimiento)
Activa ⇄ Latente        (baja el volumen; si revive, se reasigna a la MISMA narrativa)
```

Definiciones operativas:

- **Comentario suelto:** punto aislado en el espacio de embeddings o reacción sin afirmación.
- **Candidata:** grupo de comentarios cercanos en significado que todavía no sabemos si es una narrativa. En lote, es un cluster de HDBSCAN antes de validar.
- **Filtros de validación (candidata → nacida):**
  1. Es una afirmación, no pura reacción ("se robaron la plata" vs "qué vergüenza").
  2. Tamaño suficiente (relativo a la distribución de tamaños de cluster).
  3. Sostenida por cuentas distintas, DESCONTANDO las coordinadas. Veinte cuentas coordinadas repitiendo algo no prueban que la idea circule; prueban que alguien la empuja. Por eso la tarea B alimenta a la tarea A.
  4. Persistencia: aparece en más de una publicación o en más de una ventana de tiempo.
- **fecha_origen:** retroactiva. Es el comentario más antiguo del NÚCLEO del grupo (no del borde, para evitar outliers que adelanten la fecha), no el momento en que el grupo se confirmó. Vale 15% de narrativas y decae a cero a las 48 h de error.
- **Mutando:** los comentarios nuevos siguen asignados al grupo pero el centroide por día se desplaza. Error típico a evitar: partir una narrativa que muta en dos (castiga el B-cubed).
- **Amplificada:** porcentaje relevante de los comentarios del grupo viene de cuentas en operaciones detectadas. Se calcula por día.
- **Latente/revive:** el volumen diario cae por debajo de un percentil y luego vuelve. Debe reasignarse a la narrativa existente.

Implementación en lote: después del clustering, calcula por narrativa una tabla diaria (volumen, % apoyo, % rechazo, % de cuentas coordinadas, distancia del centroide diario al centroide global) y deriva de ahí el estado por día. Esa tabla se guarda en Parquet y la usan el vault de Obsidian y la demo.

### 3.2 Recorrido de un comentario

```
Llega
 └─▶ Embedding (desde caché)
      └─▶ ¿Es respuesta corta que acompaña?  ── sí ─▶ hereda narrativa y postura del padre
      └─▶ ¿Es respuesta que contradice?       ── sí ─▶ misma narrativa del padre, postura opuesta
      └─▶ Asignación por clustering
            ├─ Asignado con confianza alta  ─▶ narrativa
            ├─ Ruido claro                  ─▶ ninguna
            └─ Dudoso (entre dos grupos o en el borde) ─▶ decisor (ver §5)
      └─▶ Postura del comentario raíz ─▶ decisor
      └─▶ Final: (narrativa, postura)
```

"Postura por aristas": para las respuestas no se pregunta "¿qué postura tiene?", sino "¿apoya o contradice al de arriba?", y se propaga el signo por el árbol de `respuesta_a`. Juzgar la relación entre dos comentarios es más fácil que juzgar uno suelto, y resuelve el caso "es mentira que X", que comparte palabras con X. Primero mide en `NOTES.md` qué porcentaje del set son respuestas, para saber cuánto cubre esto.

---

## 4. Decisiones de diseño (semáforo)

Estas ideas se evaluaron antes de esta sesión. Respétalas.

**Adoptadas (verde):**
- **Motor barato, árbitro caro.** Embeddings y clustering locales descubren narrativas sin costo; la IA solo resuelve lo dudoso. Métrica de pitch: qué porcentaje de comentarios necesitó IA.
- **Texto a columnas.** Respuestas tipadas por comentario guardadas como columnas en Parquet; el resto es SQL (DuckDB) y clustering clásico. La IA pasa de motor a sensor. Hacer POCAS preguntas y solo donde cambian una decisión (cada pregunta multiplica llamadas y latencia).
- **Postura por las aristas** (ver §3.2).
- **¿Mismo guion?** Un método barato propone pares de comentarios parecidos (MinHash/LSH o coseno de embeddings); el decisor confirma solo los dudosos. Los "sí" arman un grafo de cuentas; las operaciones son comunidades. Una frase copiada una vez no arma grafo; una cuenta que repite, sí.
- **Loop nocturno con validación en días no vistos** (versión simple: un agente + regla de aceptación, ver §7).
- **Curva de costo real:** replicar el set N veces (por ejemplo ×1, ×5, ×20, ×50) y medir tiempo y costo, para demostrar escala con números.

**Opcionales si sobra tiempo (amarillo):**
- **Modo streaming día por día** con el mismo código, para la demo de escala. La entrega oficial sale del modo lote, que puntúa mejor.
- **Desacuerdo entre dos decisores** como señal de duda. Si se hace, que sea local vs Jev, no dos APIs.
- **Sets sintéticos propios** con otros temas y campañas plantadas para medir generalización.

**Descartadas (rojo):**
- **"If gigante"** (un LLM propone la lista de narrativas y otro clasifica todo): IA como motor único, pierde narrativas que nacen a mitad del período.
- **Un pedido por publicación** como arquitectura: las narrativas cruzan publicaciones. Sí se rescata pasar el hilo como contexto al juzgar postura de respuestas.

---

## 5. Modelos por etapa

| Etapa | Por defecto (local, sin clave) | Opcional (API) | Notas |
|---|---|---|---|
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (384 dim) | — | Dejar listo para comparar `paraphrase-multilingual-mpnet-base-v2` y `multilingual-e5-small` por puntaje y velocidad. Caché por nombre de modelo. |
| Reducción + clustering | UMAP (n_neighbors=15, n_components=5, coseno) + HDBSCAN (min_cluster_size ~50, min_samples menor, para barrer 10–100) | — | Punto de partida de la literatura (configuración de BERTopic y estudios con cientos de miles de textos). Semillas fijas. |
| ¿Afirmación o reacción? | Heurística + clasificador NLI multilingüe local | Jev | Filtro de validación de candidatas y de ruido. |
| Postura de respuestas | Relación con el padre (apoya/contradice/acompaña) con NLI local | Jev | Propagar por el árbol. |
| Postura de raíces | NLI local contra el título/centroide de la narrativa | Jev | Solo para los de confianza baja si se usa API. |
| Asignación dudosa | Vecino más cercano entre grupos | Jev (hasta 255 opciones) | Solo comentarios entre dos grupos o en el borde. |
| ¿Mismo guion? | Coseno > 0,7 en ventanas de 1 día, o MinHash | Jev para pares dudosos | Umbral de la literatura de coordinación (Pacheco et al.). |
| Grafo de coordinación | Peso = coincidencias repetidas; descartar aristas de peso 1; percentil alto de peso; comunidades (Louvain/Leiden) | — | Ventana de coordinación estimada de los datos, no fija (idea de CooRnet). Señales extra: antigüedad de cuenta, ráfagas vs lo esperable por publicación, `me_gusta`. |
| Título y frases clave | c-TF-IDF del grupo + comentario más central como título | LLM chico vía API (una llamada por narrativa) | `narrativas.csv` exige `titulo` y `frases_clave`: el modo local debe generarlos igual. |

### Jev (TypeSafe AI)

- Modelo de decisiones estructuradas: entra texto, salen decisiones tipadas con probabilidades calibradas, sin generar texto. Docs: https://docs.typesafe.ai
- Encaja en: postura, afirmación vs reacción, asignación dudosa, confirmación de "mismo guion". NO sirve para nombrar narrativas (no genera texto) ni reemplaza al clustering.
- Precio publicado: USD 0,042 por millón de tokens de entrada; salida sin costo. Estimado grueso: 150.000 consultas × ~100 tokens ≈ 15M tokens ≈ USD 0,63.
- Latencia publicada: 70–500 ms por llamada. Hace falta concurrencia, y usarlo solo donde la confianza local es baja.
- Está en acceso anticipado: si no hay `TYPESAFE_API_KEY`, todo funciona igual en modo local. Nunca en el camino crítico.
- Usa las probabilidades para enrutar: aceptar lo seguro, mandar lo dudoso a un paso más caro o a ruido.

---

## 6. Tareas de esta sesión

1. **Repo y entorno.** Clona el repo del desafío y arma el nuestro: entorno virtual, `requirements.txt` con versiones fijadas, `.gitignore` con `salida/`, `datos/final/`, `.cache/`, `.env`, `vault/`. La carpeta `entrega/` queda reservada para el set final.

2. **Línea base.** Corre `ejemplos/linea_base.py` y `evaluacion/puntuar.py` sobre práctica. Registra el desglose en `RESULTS.md`. Debería dar ~17/55; si no, investiga antes de seguir.

3. **Exploración → `NOTES.md`.** Volumen por día y por publicación; % de respuestas; largo de textos; distribución de antigüedad de cuentas, seguidores y `me_gusta`; picos por hora; tipos de trampas según la verdad (solo el tipo). Incluye cualquier contradicción entre este prompt y el enunciado.

4. **Almacenamiento.** CSV.gz → Parquet con tipos correctos; consultas con DuckDB. Explica en el README por qué (columnar, comprimido, sin servidor, escala por particiones de fecha; cómo pasaría a millones por día).

5. **Caché de embeddings.** Calcula una vez los embeddings de práctica con el modelo por defecto y guárdalos en `.cache/embeddings/<modelo>.parquet` (o `.npy` + índice) por `comentario_id`. Mide y anota el tiempo. El pipeline calcula y cachea si no existen (para el set final).

6. **`pipeline.py`.** Un solo archivo, editable por el agente nocturno. Parámetros agrupados en un dict `PARAMS` arriba de todo. Funciones por etapa, siguiendo §3 y §5:
   - `cargar()` → `embeddings()` → `agrupar()` → `validar_candidatas()` → `asignar_y_ruido()` → `postura()` (aristas + raíces) → `fecha_origen()` → `coordinacion()` → `estados_por_dia()` → `escribir_entrega()`.
   - El orden real puede requerir una pasada de coordinación antes de validar candidatas (filtro 3 de §3.1). Hazlo explícito.
   - Flag `--decisor local|jev` (por defecto `local`; `jev` solo si hay clave, y si falta, cae a `local` con un aviso).
   - Escribe también `salida/.../estados.parquet` (tabla diaria por narrativa) y `salida/.../metricas.json` (tiempos por etapa, fracción con IA).

7. **Wrapper de decisores (`decisores.py`).** Interfaz común `decidir(lote) -> [(etiqueta, prob)]`. Implementaciones `local` y `jev`. Caché en SQLite por hash de la entrada, concurrencia configurable, reintentos con backoff, conteo de tokens y USD. Así las iteraciones nocturnas no pagan dos veces lo mismo.

8. **Arnés `eval.py`.**
   - Corre el pipeline sobre práctica completa y sobre dos particiones de validación (por ejemplo días 1–7 y 8–14), construyendo el subconjunto de datos y de verdad de cada una.
   - Puntúa cada corrida con `puntuar.py`.
   - Calcula una métrica combinada que incluya puntaje, tiempo y costo (por ejemplo: puntaje − penalidad por segundos y por USD por mil comentarios), con pesos en un solo lugar.
   - Imprime una tabla y agrega una fila a `experiments.tsv`: fecha, commit, resumen de `PARAMS`, puntajes por componente y partición, segundos, USD, fracción con IA.
   - Tiempo objetivo por corrida completa del arnés: lo más bajo posible. Mídelo y anótalo. Si pasa de ~10 minutos, propone cómo bajarlo (caché, muestreo para barridos rápidos, paralelismo).

9. **`program.md` (instrucciones para el agente nocturno).** Debe incluir:
   - Que solo edita `pipeline.py` (y como mucho `PARAMS` en `decisores.py`). Nunca `eval.py`, `puntuar.py` ni los datos.
   - Las restricciones de §2, copiadas literal.
   - Regla de aceptación: un cambio se queda solo si mejora la métrica combinada en el set completo Y no empeora ninguna partición más allá de un margen pequeño. Si no, `git reset` y se registra igual en `experiments.tsv` como descartado.
   - Un commit por cambio aceptado, con mensaje que explique la hipótesis.
   - Presupuesto de tiempo por experimento.
   - Backlog inicial priorizado: comparar modelos de embeddings; barrer `min_cluster_size` / `min_samples` / `n_neighbors`; filtros de validación de candidatas; tratamiento de mutación (no partir narrativas); estimación de `fecha_origen` (núcleo vs borde); umbral de "mismo guion" y ventana de coordinación estimada; peso mínimo de aristas y algoritmo de comunidades; descontar coordinadas al validar narrativas; fracción de comentarios enviados al decisor según confianza.
   - Prohibición explícita de atajos: si una mejora depende de algo específico del tema de práctica, se descarta.
   - Qué hacer si se corta la sesión: leer `experiments.tsv` y el último commit, y seguir.

10. **Exportador para Obsidian (`export_vault.py`).** Fuera del loop de puntaje. Lee la salida del pipeline y genera `vault/`:
    - Una nota por narrativa con frontmatter (`fecha_origen`, volumen total, % apoyo, % rechazo, estado actual, días amplificada) y cuerpo con título, frases clave, 5 comentarios de ejemplo (más centrales) y la serie diaria como tabla.
    - Una nota por operación coordinada (cuentas, antigüedad media, ráfagas, narrativas que empuja).
    - Una nota índice con tablas compatibles con el plugin Dataview.
    - Enlaces `[[...]]` narrativa ↔ operación ↔ fuente, para que la vista de grafo muestre quién empuja qué.
    - Solo agregados: nunca una nota por comentario.
    - Debe poder publicarse como sitio estático con Quartz para la demo (deja instrucciones en el README).

11. **Curva de costo (`escala.py`).** Replica el set ×1, ×5, ×20 (y ×50 si el tiempo lo permite) cambiando ids, corre el pipeline y registra tiempo y costo. Guarda los resultados para el pitch. Puede quedar preparado sin correr las réplicas grandes.

12. **README.** Secciones obligatorias del enunciado, más: arquitectura en una imagen o diagrama Mermaid, las dos máquinas de estado, modo local vs modo con API, cómo reproducir exactamente, y la tabla de costo.

13. **Preguntas abiertas → `PREGUNTAS.md`.** Lista lo que hay que preguntar a la organización, empezando por: cómo vuelve a correr el jurado un pipeline que usa una clave de API si no puede haber claves en el repo, y qué pasa si el resultado de la re-ejecución difiere.

---

## 7. Criterio de terminado

- La línea base reproduce su puntaje y está en `RESULTS.md`.
- `python pipeline.py --datos datos/practica --entrega salida/practica` corre SIN claves y produce los cuatro archivos con formato válido, más `estados.parquet` y `metricas.json`.
- Dos corridas seguidas producen archivos idénticos.
- `python eval.py` imprime puntajes del set completo y de ambas particiones, la métrica combinada, y agrega una fila a `experiments.tsv`.
- `python export_vault.py` genera un vault que abre en Obsidian.
- `program.md`, `NOTES.md`, `RESULTS.md`, `PREGUNTAS.md` y README están escritos.
- Todo commiteado y `git status` limpio.

Al terminar, escribe un resumen corto con: puntaje del primer `pipeline.py` vs línea base, tiempo por corrida del arnés, cuellos de botella detectados y riesgos que veas para la noche y para el viernes.