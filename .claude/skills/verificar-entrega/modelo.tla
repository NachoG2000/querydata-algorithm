---- MODULE modelo ----
\* Entrega del set final (docs/contexto.md 2.5).
\* rama_experimental -> verificada -> mergeada -> corrida_final -> entregada
\* Los tres flags describen guardas que el repo NO implementa como código:
\*   GUARDA_MERGE: el merge a main exige que el mejor commit supere al vigente
\*     (hoy es una regla en prosa de program.md:47; nada la ejecuta).
\*   CACHE_FRIA: la corrida final borra .cache antes de correr
\*     (pipeline.py:embeddings reutiliza .cache/embeddings y
\*      pipeline.py:reporte_referencia reutiliza "segundos" de .cache/reportes).
\*   REGENERAR: tras un merge a main se exige una corrida final antes de entregar
\*     (60c4a68 cerró con código de de7ebd0 en main y entrega/ de c7406f3).
EXTENDS Naturals

CONSTANTS GUARDA_MERGE, CACHE_FRIA, REGENERAR

VARIABLES fase, supera, codigoMain, codigoEntrega, entregaValida, cacheCaliente, costoPropio, claves

vars == <<fase, supera, codigoMain, codigoEntrega, entregaValida, cacheCaliente, costoPropio, claves>>

\* códigos: 0 = vigente (c7406f3), 1 = candidato de la rama experimental
Init == /\ fase = "rama_experimental"
        /\ supera \in BOOLEAN
        /\ codigoMain = 0
        /\ codigoEntrega = 0
        /\ entregaValida = TRUE
        /\ cacheCaliente \in BOOLEAN
        /\ costoPropio = TRUE
        /\ claves = FALSE

\* python eval.py sobre la rama: decide si el candidato supera al vigente
Verificar == /\ fase = "rama_experimental"
             /\ fase' = "verificada"
             /\ UNCHANGED <<supera, codigoMain, codigoEntrega, entregaValida, cacheCaliente, costoPropio, claves>>

\* git merge a main: con GUARDA_MERGE sólo si supera
Mergear == /\ fase = "verificada"
           /\ (GUARDA_MERGE => supera)
           /\ fase' = "mergeada"
           /\ codigoMain' = 1
           /\ UNCHANGED <<supera, codigoEntrega, entregaValida, cacheCaliente, costoPropio, claves>>

\* pipeline.py:ejecutar sobre datos/final; escribir_entrega reemplaza entrega/ atómicamente
CorridaFinal == /\ fase = "mergeada"
                /\ fase' = "corrida_final"
                /\ codigoEntrega' = codigoMain
                /\ cacheCaliente' = IF CACHE_FRIA THEN FALSE ELSE cacheCaliente
                /\ costoPropio' = ~cacheCaliente'
                /\ UNCHANGED <<supera, codigoMain, entregaValida, claves>>

\* El candidato no supera: main y entrega/ quedan con el vigente
Descartar == /\ fase = "verificada"
             /\ ~supera
             /\ fase' = "entregada"
             /\ UNCHANGED <<supera, codigoMain, codigoEntrega, entregaValida, cacheCaliente, costoPropio, claves>>

\* Cierre sin regenerar: se entrega lo que ya estaba (caso 60c4a68)
EntregarSinRegenerar == /\ fase = "mergeada"
                        /\ ~REGENERAR
                        /\ fase' = "entregada"
                        /\ UNCHANGED <<supera, codigoMain, codigoEntrega, entregaValida, cacheCaliente, costoPropio, claves>>

Entregar == /\ fase = "corrida_final"
            /\ fase' = "entregada"
            /\ UNCHANGED <<supera, codigoMain, codigoEntrega, entregaValida, cacheCaliente, costoPropio, claves>>

Done == fase = "entregada" /\ UNCHANGED vars

Next == Verificar \/ Descartar \/ Mergear \/ CorridaFinal \/ EntregarSinRegenerar \/ Entregar \/ Done

Spec == Init /\ [][Next]_vars

\* 1. main siempre contiene una entrega/ válida
MainConEntregaValida == entregaValida

\* 2. Sólo se mergea si el mejor commit supera al vigente
MergeSoloSiSupera == codigoMain = 1 => supera

\* 3. La corrida final calcula embeddings desde cero y su costo.json es el que se entrega
CostoDeCorridaFria == fase = "entregada" => (costoPropio /\ codigoEntrega = codigoMain)

\* 4. Dos corridas del commit entregado dan archivos idénticos, sin claves:
\*    el commit en main debe ser el que generó entrega/
EntregaReproducibleDesdeMain == fase = "entregada" => (codigoEntrega = codigoMain /\ ~claves)
====
