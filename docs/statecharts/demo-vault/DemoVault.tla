---- MODULE DemoVault ----
\* Navegacion por los enlaces [[...]] que escribe export_vault.py.
\* auxiliares: existen estados.parquet y detalles.parquet (salida/final/, fuera de git).
\* conOp: alguna cuenta de una operacion comento en la narrativa abierta (operation_links_by_narrative).
\* diasAmp: la nota muestra dias_amplificada > 0 (sale de estados.parquet).
VARIABLES nota, auxiliares, conOp, diasAmp
vars == <<nota, auxiliares, conOp, diasAmp>>

Init == nota = "indice" /\ auxiliares \in BOOLEAN /\ conOp = FALSE /\ diasAmp = FALSE

\* pipeline.estados_por_dia: si una cuenta coordinada comenta un dia, ese dia es el de cuota maxima o lo supera alguno, asi que hay al menos un dia amplificada.
AbreNarrativa(op) == /\ nota' = "narrativa" /\ conOp' = op
                     /\ diasAmp' = (op /\ auxiliares) /\ UNCHANGED auxiliares

IndiceANarrativa == nota = "indice" /\ \E op \in BOOLEAN : AbreNarrativa(op)
IndiceAOperacion == nota = "indice" /\ nota' = "operacion" /\ UNCHANGED <<auxiliares, conOp, diasAmp>>
NarrativaAOperacion == nota = "narrativa" /\ conOp /\ nota' = "operacion" /\ UNCHANGED <<auxiliares, conOp, diasAmp>>
OperacionANarrativa == nota = "operacion" /\ AbreNarrativa(TRUE)
NarrativaAFuente == nota = "narrativa" /\ nota' = "fuente" /\ UNCHANGED <<auxiliares, conOp, diasAmp>>
OperacionAFuente == nota = "operacion" /\ nota' = "fuente" /\ UNCHANGED <<auxiliares, conOp, diasAmp>>
FuenteANarrativa == nota = "fuente" /\ \E op \in BOOLEAN : AbreNarrativa(op)
FuenteAOperacion == nota = "fuente" /\ nota' = "operacion" /\ UNCHANGED <<auxiliares, conOp, diasAmp>>
\* Ninguna nota enlaza a index.md: la vuelta es el boton Atras o el buscador de Obsidian.
VuelveAlIndice == nota # "indice" /\ nota' = "indice" /\ conOp' = FALSE /\ diasAmp' = FALSE /\ UNCHANGED auxiliares

Next == IndiceANarrativa \/ IndiceAOperacion \/ NarrativaAOperacion \/ OperacionANarrativa
        \/ NarrativaAFuente \/ OperacionAFuente \/ FuenteANarrativa \/ FuenteAOperacion \/ VuelveAlIndice
Spec == Init /\ [][Next]_vars

\* Si la nota de una narrativa lista una operacion, muestra dias amplificada.
OperacionListadaImplicaAmplificada == (nota = "narrativa" /\ conOp) => diasAmp
\* Desde una narrativa con operacion siempre hay salto a esa operacion (y la operacion vuelve).
NarrativaAmplificadaEnlazaOperacion == (nota = "narrativa" /\ diasAmp) => conOp
====
