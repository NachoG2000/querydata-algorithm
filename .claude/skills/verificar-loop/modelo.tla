---- MODULE modelo ----
EXTENDS Naturals, FiniteSets

CONSTANTS Archivos, Permitidos, Particiones, Puntos, MaxCorridas, Regla, Reset, Registra

VARIABLES fase, codigo, base, editados, resultado, mejor, previo, corridas, filas, pendientes

vars == <<fase, codigo, base, editados, resultado, mejor, previo, corridas, filas, pendientes>>

Cero == [p \in Particiones |-> 0]

Init ==
  /\ fase = "inicio"
  /\ codigo = 0 /\ base = 0
  /\ editados = {}
  /\ resultado = Cero /\ mejor = Cero /\ previo = Cero
  /\ corridas = 0 /\ filas = 0 /\ pendientes = 0

Mejora(r) ==
  IF Regla = "por_particion"
  THEN (\A p \in Particiones : r[p] >= mejor[p]) /\ (\E p \in Particiones : r[p] > mejor[p])
  ELSE r["completo"] > mejor["completo"] /\ (\A p \in Particiones : r[p] + 1 >= mejor[p])

Proponer ==
  /\ fase \in {"inicio", "registrada"}
  /\ corridas < MaxCorridas
  /\ \E f \in Archivos :
       /\ editados' = editados \cup {f}
  /\ codigo' = codigo + 1
  /\ fase' = "propuesta"
  /\ UNCHANGED <<base, resultado, mejor, previo, corridas, filas, pendientes>>

Correr ==
  /\ fase = "propuesta"
  /\ fase' = "corriendo"
  /\ corridas' = corridas + 1
  /\ UNCHANGED <<codigo, base, editados, resultado, mejor, previo, filas, pendientes>>

Evaluar ==
  /\ fase = "corriendo"
  /\ \E r \in [Particiones -> Puntos] : resultado' = r
  /\ filas' = IF Registra THEN filas + 1 ELSE filas
  /\ pendientes' = pendientes + 1
  /\ fase' = "evaluada"
  /\ UNCHANGED <<codigo, base, editados, mejor, previo, corridas>>

Aceptar ==
  /\ fase = "evaluada"
  /\ Mejora(resultado)
  /\ previo' = mejor
  /\ mejor' = resultado
  /\ base' = codigo
  /\ fase' = "aceptada"
  /\ UNCHANGED <<codigo, editados, resultado, corridas, filas, pendientes>>

Descartar ==
  /\ fase = "evaluada"
  /\ codigo' = IF Reset THEN base ELSE codigo
  /\ fase' = "descartada"
  /\ UNCHANGED <<base, editados, resultado, mejor, previo, corridas, filas, pendientes>>

Marcar ==
  /\ fase \in {"aceptada", "descartada"}
  /\ pendientes' = pendientes - 1
  /\ fase' = "registrada"
  /\ UNCHANGED <<codigo, base, editados, resultado, mejor, previo, corridas, filas>>

Fin ==
  /\ fase \in {"inicio", "registrada"}
  /\ corridas = MaxCorridas
  /\ UNCHANGED vars

Next == Proponer \/ Correr \/ Evaluar \/ Aceptar \/ Descartar \/ Marcar \/ Fin

Spec == Init /\ [][Next]_vars

TodaCorridaRegistrada ==
  fase \in {"inicio", "registrada", "propuesta"} => (filas = corridas /\ pendientes = 0)

AceptadaNoEmpeora == \A p \in Particiones : mejor[p] >= previo[p]

DescartadaRestaura == fase \in {"descartada", "registrada", "inicio"} => codigo = base

SoloPipelineYDecisores == editados \subseteq Permitidos
====
