---- MODULE Narrativa ----
\* Ciclo de vida de una narrativa tal como lo produce pipeline.py en lote:
\* validar_candidatas (líneas 484-501) decide el nacimiento y estados_por_dia (642-678) el estado de cada día.
EXTENDS Naturals

CONSTANTS MaxDia, ROTO

VARIABLES estado, previo, id, idNacimiento, idsCreados, genuinas, coordinadas, amplificada, dia
vars == <<estado, previo, id, idNacimiento, idsCreados, genuinas, coordinadas, amplificada, dia>>

Vivos == {"nacida", "activa", "mutando", "latente"}
Permitidas == {<<"suelto", "candidata">>, <<"candidata", "suelto">>, <<"candidata", "nacida">>,
               <<"nacida", "activa">>, <<"activa", "mutando">>, <<"mutando", "activa">>,
               <<"activa", "latente">>, <<"latente", "activa">>,
               <<"activa", "activa">>, <<"mutando", "mutando">>, <<"latente", "latente">>}

Init ==
  /\ estado = "suelto" /\ previo = "suelto"
  /\ id = 0 /\ idNacimiento = 0 /\ idsCreados = 0
  /\ genuinas = 0 /\ coordinadas = 0 /\ amplificada = FALSE /\ dia = 0

\* agrupar: aparecen comentarios cercanos; cuántas cuentas son genuinas y cuántas coordinadas
AparecenCercanos ==
  /\ estado = "suelto"
  /\ estado' = "candidata" /\ previo' = estado
  /\ genuinas' \in 0..2 /\ coordinadas' \in 0..2
  /\ UNCHANGED <<id, idNacimiento, idsCreados, amplificada, dia>>

\* validar_candidatas: cuentas.ge(2) cuenta solo cuentas fuera de grupos (líneas 493 y 496)
Apoyo == IF ROTO = "cuenta-coordinadas" THEN genuinas + coordinadas ELSE genuinas

NoPasaValidacion ==
  /\ estado = "candidata" /\ Apoyo < 2
  /\ estado' = "suelto" /\ previo' = estado
  /\ UNCHANGED <<id, idNacimiento, idsCreados, genuinas, coordinadas, amplificada, dia>>

Nace ==
  /\ estado = "candidata" /\ Apoyo >= 2 /\ idsCreados = 0
  /\ estado' = "nacida" /\ previo' = estado
  /\ idsCreados' = 1 /\ id' = 1 /\ idNacimiento' = 1
  /\ amplificada' \in BOOLEAN
  /\ dia' = 1
  /\ UNCHANGED <<genuinas, coordinadas>>

\* estados_por_dia: cada día se clasifica sin mirar el estado anterior (líneas 669-676)
OtroDia ==
  /\ estado \in Vivos /\ dia < MaxDia
  /\ estado' \in {"activa", "mutando", "latente"} /\ previo' = estado
  /\ amplificada' \in BOOLEAN
  /\ dia' = dia + 1
  /\ IF ROTO = "revive-con-id-nuevo" /\ estado = "latente" /\ estado' = "activa"
       THEN /\ id' = idsCreados + 1 /\ idsCreados' = idsCreados + 1
       ELSE UNCHANGED <<id, idsCreados>>
  /\ UNCHANGED <<idNacimiento, genuinas, coordinadas>>

FinDelLote == (dia = MaxDia \/ estado \in {"suelto", "candidata"}) /\ UNCHANGED vars

Next == AparecenCercanos \/ NoPasaValidacion \/ Nace \/ OtroDia \/ FinDelLote

Spec == Init /\ [][Next]_vars

TransicionPermitida == previo = estado \/ <<previo, estado>> \in Permitidas
ConservaId == estado \in Vivos => id = idNacimiento
NoNaceSoloCoordinada == estado \in Vivos => genuinas >= 1
====
