---- MODULE modelo ----
EXTENDS Naturals, FiniteSets
\* Dos cuentas (a, b) y dos pares de comentarios k = 1..2 entre ellas.
\* Cada par puede coincidir por la vía exacta (pipeline.py:coordinacion, enlaces_exactos / candidatos_raw)
\* y por la vía semántica (bucle "for salto" sobre vecinos con coseno >= piso).
CONSTANTS DEDUP, UMBRAL, UNICA
Cuentas == {"a", "b"}
K == {1, 2}
Vias == {"exacta", "semantica"}
Ops == {"g001", "g002"}
VARIABLES detectado, eventos, marcadas, ops
vars == <<detectado, eventos, marcadas, ops>>

Init == /\ detectado = [k \in K |-> {}]
        /\ eventos = [k \in K |-> 0]
        /\ marcadas = {}
        /\ ops = {}

\* repeticiones[par] es un set de contextos (publicacion, guion): la segunda vía no suma si DEDUP.
Coincidir(k, v) == /\ v \notin detectado[k]
                   /\ detectado' = [detectado EXCEPT ![k] = @ \cup {v}]
                   /\ eventos' = [eventos EXCEPT ![k] = IF DEDUP /\ detectado[k] # {} THEN @ ELSE @ + 1]
                   /\ UNCHANGED <<marcadas, ops>>
Peso == eventos[1] + eventos[2]
\* pesos = {par: len(contextos) ... if len(contextos) >= 2}
Marcar == /\ Peso >= UMBRAL
          /\ marcadas # Cuentas
          /\ marcadas' = Cuentas
          /\ UNCHANGED <<detectado, eventos, ops>>
\* grupos = {cuenta: g... for c in connected_components(union)}
Agrupar(c, o) == /\ c \in marcadas
                 /\ UNICA => \A p \in ops : p[1] # c
                 /\ <<c, o>> \notin ops
                 /\ ops' = ops \cup {<<c, o>>}
                 /\ UNCHANGED <<detectado, eventos, marcadas>>
Fin == UNCHANGED vars /\ ~ENABLED (\E k \in K, v \in Vias : Coincidir(k, v))
Next == (\E k \in K, v \in Vias : Coincidir(k, v)) \/ Marcar \/ (\E c \in Cuentas, o \in Ops : Agrupar(c, o)) \/ Fin

ParesDistintos == Cardinality({k \in K : detectado[k] # {}})
UnEventoPorPar == \A k \in K : eventos[k] <= 1
PesoUnoNoMarca == marcadas # {} => ParesDistintos >= 2
CuentaUnaOperacion == \A c \in Cuentas : Cardinality({p \in ops : p[1] = c}) <= 1
====
