---- MODULE Comentario ----
\* Propagación de narrativa y postura por respuesta_a en pipeline.py:postura (líneas 515-608).
EXTENDS Naturals

CONSTANTS Coms, ROTO
NADIE == "nadie"
FANTASMA == "fantasma"
Narr == {"n1", "ninguna"}

VARIABLES padre, relacion, etiqueta, postura, fuente, resuelto, ciclos
vars == <<padre, relacion, etiqueta, postura, fuente, resuelto, ciclos>>

\* enlaces: padre inexistente o autorrespuesta no generan arista (línea 521)
Enlace(i) == padre[i] \in Coms /\ padre[i] # i
P(i) == padre[i]

Init ==
  /\ padre \in [Coms -> Coms \cup {NADIE, FANTASMA}]
  /\ relacion \in [Coms -> {"acompaña", "contradice"}]
  /\ etiqueta \in [Coms -> Narr]
  /\ postura = [i \in Coms |-> ""]
  /\ fuente = [i \in Coms |-> "ninguna"]
  /\ resuelto = [i \in Coms |-> FALSE]
  /\ ciclos = 0

\* raíz con narrativa: el decisor decide (líneas 559-579); el decisor del modelo siempre dice "rechaza"
ResolverRaiz(i) ==
  /\ ~resuelto[i] /\ ~Enlace(i)
  /\ resuelto' = [resuelto EXCEPT ![i] = TRUE]
  /\ postura' = [postura EXCEPT ![i] = IF etiqueta[i] = "ninguna" THEN "" ELSE "rechaza"]
  /\ fuente' = [fuente EXCEPT ![i] = IF etiqueta[i] = "ninguna" THEN "ninguna" ELSE "decisor"]
  /\ UNCHANGED <<padre, relacion, etiqueta, ciclos>>

Opuesta(p) == IF p = "apoya" THEN "rechaza" ELSE "apoya"

\* hijo con padre resuelto (líneas 600-606); orientacion arranca en 1 = "apoya" (línea 570)
Heredar(i) ==
  /\ ~resuelto[i] /\ Enlace(i) /\ resuelto[P(i)]
  /\ resuelto' = [resuelto EXCEPT ![i] = TRUE]
  /\ IF etiqueta[P(i)] # "ninguna" \/ ROTO = "ninguna-propaga"
       THEN /\ etiqueta' = [etiqueta EXCEPT ![i] = etiqueta[P(i)]]
            /\ postura' = [postura EXCEPT ![i] =
                 IF etiqueta[P(i)] = "ninguna" THEN ""
                 ELSE IF relacion[i] = "contradice" /\ ROTO # "contradiccion-sin-signo" THEN Opuesta(postura[P(i)]) ELSE postura[P(i)]]
            /\ fuente' = [fuente EXCEPT ![i] = "arista"]
       ELSE /\ etiqueta' = etiqueta
            /\ postura' = [postura EXCEPT ![i] = IF etiqueta[i] = "ninguna" THEN "" ELSE "apoya"]
            /\ fuente' = [fuente EXCEPT ![i] = IF etiqueta[i] = "ninguna" THEN "ninguna" ELSE "defecto"]
  /\ UNCHANGED <<padre, relacion, ciclos>>

Arriba(x) == IF x \in Coms THEN (IF Enlace(x) THEN P(x) ELSE NADIE) ELSE NADIE
Saltos(i) == <<Arriba(i), Arriba(Arriba(i)), Arriba(Arriba(Arriba(i)))>>
EnCiclo(i) == \E k \in 1..3 : Saltos(i)[k] = i
MiembrosCiclo(i) == {Saltos(i)[k] : k \in 1..3}

\* ciclo detectado: todos sus miembros quedan en ninguna (líneas 584-598)
CortarCiclo(i) ==
  /\ ROTO # "sin-deteccion-ciclos"
  /\ ~resuelto[i] /\ EnCiclo(i)
  /\ resuelto' = [j \in Coms |-> resuelto[j] \/ j \in MiembrosCiclo(i)]
  /\ etiqueta' = [j \in Coms |-> IF j \in MiembrosCiclo(i) THEN "ninguna" ELSE etiqueta[j]]
  /\ postura' = [j \in Coms |-> IF j \in MiembrosCiclo(i) THEN "" ELSE postura[j]]
  /\ ciclos' = ciclos + 1
  /\ UNCHANGED <<padre, relacion, fuente>>

Fin == \A i \in Coms : resuelto[i]
Terminado == Fin /\ UNCHANGED vars

Next == \E i \in Coms : ResolverRaiz(i) \/ Heredar(i) \/ CortarCiclo(i) \/ Terminado

Spec == Init /\ [][Next]_vars

UnaNarrativa == \A i \in Coms : etiqueta[i] \in Narr /\ (Fin => (postura[i] = "") = (etiqueta[i] = "ninguna"))
AcompanaHereda == Fin => \A i \in Coms :
  (Enlace(i) /\ relacion[i] = "acompaña" /\ etiqueta[P(i)] # "ninguna" /\ etiqueta[i] # "ninguna")
    => etiqueta[i] = etiqueta[P(i)] /\ postura[i] = postura[P(i)]
ContradiceOpuesta == Fin => \A i \in Coms :
  (Enlace(i) /\ relacion[i] = "contradice" /\ etiqueta[P(i)] # "ninguna" /\ etiqueta[i] # "ninguna")
    => etiqueta[i] = etiqueta[P(i)] /\ postura[i] = Opuesta(postura[P(i)])
NingunaNoPropaga == Fin => \A i \in Coms : (Enlace(i) /\ etiqueta[P(i)] = "ninguna") => fuente[i] # "arista"
PosturaConOrigen == Fin => \A i \in Coms : etiqueta[i] # "ninguna" => fuente[i] \in {"decisor", "arista"}
====
