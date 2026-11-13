# Contexto y decisiones del proyecto

Este documento resume las conversaciones de diseño previas al código y lo aprendido durante la optimización. Sirve para que cualquier agente o persona entienda por qué el pipeline es como es.

## 1. El problema, en una historia

Un medio publica "La obra de la ruta está frenada hace dos meses". Llegan cientos de comentarios: casi todo es ruido ("qué vergüenza", menciones). Una cuenta escribe "se robaron la plata, por eso no avanza". Un solo comentario no es narrativa. Otras personas, en otras publicaciones, dicen lo mismo con otras palabras ("¿y los fondos?"): se forma un grupo por significado. Si se sostiene (cuentas distintas, varias publicaciones, persistencia en el tiempo), es una narrativa, y su origen es el primer comentario del grupo, no el momento en que se detectó. Crece, aparecen rechazos ("es mentira, fue por las lluvias") que pertenecen a la misma narrativa con postura opuesta, y respuestas tipo "Tal cual" que heredan. Un día, cuentas nuevas publican casi lo mismo a las 3 de la mañana en varias publicaciones: la narrativa es genuina, pero alguien la amplifica. La redacción deriva ("otra obra fantasma"), baja el volumen, y puede revivir.

El desafío pide reconstruir todo eso sin etiquetas, en lote, barato y de forma que generalice a temas nuevos.

## 2. Máquinas de estado e invariantes

Las invariantes son las propiedades que las skills de verificación formal deben modelar y chequear.

### 2.1 Ciclo de vida de una narrativa

Estados: `suelto`, `candidata`, `nacida`, `activa`, `mutando`, `latente`. `amplificada` es un atributo ortogonal, no un estado excluyente: puede valer desde el nacimiento.

Transiciones:
- `suelto → candidata`: aparecen otros comentarios cercanos en significado.
- `candidata → suelto` (ruido): no pasa la validación.
- `candidata → nacida`: pasa los cuatro filtros: (1) es afirmación, no reacción; (2) tamaño suficiente relativo a la distribución; (3) sostenida por cuentas distintas, descontando las coordinadas; (4) persiste en más de una publicación o ventana.
- `nacida → activa`, `activa ⇄ mutando`, `activa ⇄ latente`.

Invariantes:
- `fecha_origen` = comentario más antiguo del núcleo del grupo (no del borde). Nunca posterior a ningún comentario del núcleo.
- Una narrativa que revive desde `latente` conserva su identificador: no se crea una nueva.
- Una narrativa que muta conserva su identificador: partirla en dos es un error.
- Un sub-grupo que arranca días después con centroide distinto es candidato a narrativa emergente propia, no parte de la anterior.
- Ninguna candidata nace solo con apoyo de cuentas coordinadas.

### 2.2 Recorrido de un comentario

Pasos: embedding → ¿respuesta corta que acompaña? → ¿respuesta que contradice? → asignación por clustering (confiado / ruido / dudoso → decisor) → postura (aristas para respuestas, decisor para raíces).

Invariantes:
- Cada comentario termina con exactamente una narrativa o `ninguna`.
- Una respuesta que solo acompaña hereda narrativa y postura del padre.
- Una respuesta que contradice al padre tiene la misma narrativa y la postura opuesta.
- Un comentario con narrativa `ninguna` no propaga postura a sus hijos.
- El grafo de `respuesta_a` se trata como árbol: ciclos o padres inexistentes se detectan y no rompen la propagación.

### 2.3 Evidencia de coordinación

Pasos: par de comentarios similares (texto normalizado idéntico o paráfrasis por embeddings) dentro de una ventana → evento → arista entre cuentas, con peso igual a los eventos distintos → cuenta coordinada si supera el soporte → operación = comunidad del grafo.

Invariantes:
- Un par de comentarios aporta como mucho un evento, aunque coincida por vía exacta y semántica.
- Una arista de peso 1 (una sola coincidencia) no marca coordinación: lo que delata es la repetición.
- Las ventanas y umbrales se estiman de los datos y se escalan a la exposición (largo del período, volumen).
- Cada cuenta pertenece como mucho a una operación.
- La precisión de cuentas en práctica se mantiene ≥ 0,9.

### 2.4 Loop de experimentación

Estados: `propuesta → corriendo → evaluada → aceptada | descartada → registrada`.

Invariantes:
- Toda corrida queda registrada en `experiments.tsv`, aceptada o no.
- Un cambio aceptado no empeora la otra tarea ni ninguna partición respecto de su valor anterior.
- Una descartada deja el código exactamente como antes (`git reset`).
- El loop solo edita `pipeline.py` (y `PARAMS` de `decisores.py`).

### 2.5 Entrega del set final

Estados: `rama_experimental → verificada → mergeada → corrida_final → entregada`.

Invariantes:
- `main` siempre contiene una `entrega/` válida.
- Solo se mergea si el mejor commit supera al vigente según la regla de aceptación.
- La corrida final calcula embeddings desde cero, y su `costo.json` es el que se entrega.
- Dos corridas del commit entregado producen archivos idénticos, sin claves.

## 3. Decisiones de diseño

Adoptadas:
- **Motor barato, árbitro caro.** Embeddings y clustering locales; la IA solo para lo dudoso. Hoy la fracción de IA es 0.
- **Texto a columnas.** Respuestas tipadas guardadas como columnas en Parquet; el resto es DuckDB y clustering clásico.
- **Postura por aristas.** Juzgar la relación con el padre es más fácil que juzgar un comentario suelto, y resuelve "es mentira que X".
- **¿Mismo guion?** Pares baratos de candidatos; el grafo de cuentas que se repiten define las operaciones.
- **Loop nocturno con validación por particiones y regla por tarea.**
- **Curva de costo** replicando el set para demostrar escala con números.

Opcionales: modo streaming día por día para la demo; desacuerdo local vs Jev como señal de duda; sets sintéticos propios.

Descartadas: un LLM que propone la lista de narrativas y otro que clasifica todo (IA como motor único, pierde emergentes); un pedido por publicación como arquitectura (las narrativas cruzan publicaciones).

Jev (TypeSafe AI) es opcional: decisiones tipadas con probabilidades, sin generar texto. Encaja en postura, afirmación vs reacción, asignación dudosa y confirmación de guion. No nombra narrativas ni reemplaza al clustering. El modo sin clave siempre funciona.

## 4. Historia de resultados

- Línea base oficial: 21,96 / 55.
- Primera noche: el loop mejoró sobre todo coordinación. Commit `c7406f3`: 33,16 / 55 (A 13,37, B 19,79).
- Diagnósticos clave: la variante 31 tenía 10% de precisión en cuentas pese a un buen B-cubed; las cuentas detectadas por la base y por la variante 23 eran distintas (unión 52 de 115); días 1–7 tiene actividad coordinada; dos de tres emergentes quedan fusionados con narrativas anteriores; la postura no tenía modelo NLI activo.
- Cierre del loop: `c7406f3` generó la `entrega/` del set final (publicada en `8a1f5be`). Después se activó NLI local para la postura de raíces y la relación con el padre, y se agregó la ventana días 1–10. El mejor código aceptado, `de7ebd0`, da 33,81 / 55 en práctica (A 14,02, B 19,79), pero todavía no regeneró `entrega/`.

## 5. Preguntas abiertas

- Cómo vuelve a correr el jurado un pipeline que usa una clave de API, si no puede haber claves en el repo.
- Qué pasa si la re-ejecución del jurado no coincide con la entrega.

## 6. Glosario

- **Narrativa:** afirmación o encuadre que se repite con distintas palabras.
- **Ruido:** comentarios sin afirmación propia (reacciones, menciones, fuera de tema).
- **Candidata:** grupo cercano en significado que todavía no se validó como narrativa.
- **Núcleo:** comentarios centrales de un cluster, por oposición al borde.
- **Emergente:** narrativa que aparece a mitad del período.
- **Evento:** coincidencia entre dos comentarios de cuentas distintas dentro de una ventana.
- **Operación:** grupo de cuentas que actúan coordinadas.
- **Exposición:** cuánta oportunidad de evidencia hay (largo del período, volumen); los umbrales se escalan a ella.
