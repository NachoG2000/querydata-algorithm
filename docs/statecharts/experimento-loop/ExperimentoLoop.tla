---- MODULE ExperimentoLoop ----
\* Un ciclo de program.md "Bucle de trabajo" con eval.py tal como esta.
\* fila: estado de la fila de esta corrida en experiments.tsv (archivo versionado en git).
\* empeora: alguna particion (dia_1_7, dia_8_14, dia_1_10) pierde puntos de la tarea.
VARIABLES fase, fila, empeora
vars == <<fase, fila, empeora>>

Init == fase = "propuesta" /\ fila = "ninguna" /\ empeora = FALSE

Edita == fase = "propuesta" /\ fase' = "editado" /\ UNCHANGED <<fila, empeora>>
\* eval.invoke_pipeline levanta RuntimeError (falla o timeout) antes de append_experiment.
CorridaFalla == fase = "editado" /\ fase' = "fallo" /\ UNCHANGED <<fila, empeora>>
CorridaTermina == /\ fase = "editado" /\ fase' = "medido"
                  /\ fila' = "pendiente" /\ empeora' \in BOOLEAN
\* eval.mark_experiment no compara particiones: acepta lo que se le pida.
CommitCodigo == fase = "medido" /\ fase' = "commiteado" /\ UNCHANGED <<fila, empeora>>
MarcaAceptada == /\ fase = "commiteado" /\ fila = "pendiente"
                 /\ fase' = "aceptado" /\ fila' = "aceptada" /\ UNCHANGED empeora
MarcaDescartada == /\ fase = "medido" /\ fila = "pendiente"
                   /\ fase' = "descartado" /\ fila' = "descartada" /\ UNCHANGED empeora
RestauraSoloSuDiff == fase = "descartado" /\ fase' = "cerrado" /\ UNCHANGED <<fila, empeora>>
\* experiments.tsv esta en git: un reset duro antes del commit de bitacora borra la fila.
GitResetHard == fase = "descartado" /\ fase' = "cerrado" /\ fila' = "ninguna" /\ UNCHANGED empeora
RestauraTrasFalla == fase = "fallo" /\ fase' = "cerrado" /\ UNCHANGED <<fila, empeora>>
CommitBitacora == fase = "aceptado" /\ fase' = "cerrado" /\ UNCHANGED <<fila, empeora>>
Fin == fase = "cerrado" /\ UNCHANGED vars

Next == Edita \/ CorridaFalla \/ CorridaTermina \/ CommitCodigo \/ MarcaAceptada \/ MarcaDescartada
        \/ RestauraSoloSuDiff \/ GitResetHard \/ RestauraTrasFalla \/ CommitBitacora \/ Fin
Spec == Init /\ [][Next]_vars

TodaCorridaRegistrada == fase = "cerrado" => fila \in {"aceptada", "descartada"}
AceptadaNoEmpeoraParticion == fila = "aceptada" => ~empeora
====
