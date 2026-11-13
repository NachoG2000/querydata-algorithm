---- MODULE EntregaFinal ----
\* program.md, "Proteccion de main y cierre", y FINAL_RUN.md (cierre real).
\* origenCodigo: codigo publicado en origin/main. origenEntrega: codigo que genero entrega/ publicada.
\* local*: lo mismo en el main local antes de subir.
VARIABLES fase, mejor, localCodigo, localEntrega, origenCodigo, origenEntrega
vars == <<fase, mejor, localCodigo, localEntrega, origenCodigo, origenEntrega>>

Init == /\ fase = "rama"
        /\ mejor \in BOOLEAN
        /\ localCodigo = "c7406f3" /\ localEntrega = "c7406f3"
        /\ origenCodigo = "c7406f3" /\ origenEntrega = "c7406f3"

Verifica == /\ fase = "rama" /\ mejor
            /\ fase' = "verificado"
            /\ UNCHANGED <<mejor, localCodigo, localEntrega, origenCodigo, origenEntrega>>
NoSupera == /\ fase = "rama" /\ ~mejor
            /\ fase' = "intacto"
            /\ UNCHANGED <<mejor, localCodigo, localEntrega, origenCodigo, origenEntrega>>
Merge == /\ fase = "verificado"
         /\ fase' = "integrado" /\ localCodigo' = "nuevo"
         /\ UNCHANGED <<mejor, localEntrega, origenCodigo, origenEntrega>>
CorreEnFrio == /\ fase = "integrado"
               /\ fase' = "regenerado" /\ localEntrega' = "nuevo"
               /\ UNCHANGED <<mejor, localCodigo, origenCodigo, origenEntrega>>
SubeConEntrega == /\ fase = "regenerado"
                  /\ fase' = "publicado"
                  /\ origenCodigo' = localCodigo /\ origenEntrega' = localEntrega
                  /\ UNCHANGED <<mejor, localCodigo, localEntrega>>
\* Cierre real (FINAL_RUN.md): el usuario pide subir todo y parar sin regeneracion fria.
SubeSinRegenerar == /\ fase = "integrado"
                    /\ fase' = "publicado"
                    /\ origenCodigo' = localCodigo /\ origenEntrega' = localEntrega
                    /\ UNCHANGED <<mejor, localCodigo, localEntrega>>
Fin == fase \in {"publicado", "intacto"} /\ UNCHANGED vars

Next == Verifica \/ NoSupera \/ Merge \/ CorreEnFrio \/ SubeConEntrega \/ SubeSinRegenerar \/ Fin
Spec == Init /\ [][Next]_vars

MainTieneEntregaDeSuCodigo == origenEntrega = origenCodigo
====
