---- MODULE JuradoReejecuta ----
\* El jurado clona el repo y corre: python pipeline.py --datos datos/final --entrega entrega
\* codigo: "main" (60c4a68, codigo posterior a la entrega) o "c7406f3" (el que genero entrega/).
\* clave: hay TYPESAFE_API_KEY en el entorno o en .env.
VARIABLES paso, codigo, clave, descargoHF, llamoJev, predIguales, costoIgual
vars == <<paso, codigo, clave, descargoHF, llamoJev, predIguales, costoIgual>>

Init == /\ paso = "clonado"
        /\ codigo \in {"main", "c7406f3"}
        /\ clave \in BOOLEAN
        /\ descargoHF = FALSE /\ llamoJev = FALSE
        /\ predIguales = FALSE /\ costoIgual = FALSE

\* Maquina nueva: .cache/ no esta en git, los pesos no estan en disco.
\* pipeline.embeddings y LocalNLI bajan los modelos fijados de Hugging Face.
CargaModelos == /\ paso = "clonado"
                /\ paso' = "modelos" /\ descargoHF' = TRUE
                /\ UNCHANGED <<codigo, clave, llamoJev, predIguales, costoIgual>>

\* decisores.DecisionEngine: mode jev solo si hay clave; en c7406f3 el default es local.
DecideConJev == /\ paso = "modelos" /\ clave /\ codigo = "main"
                /\ paso' = "decidido" /\ llamoJev' = TRUE
                /\ UNCHANGED <<codigo, clave, descargoHF, predIguales, costoIgual>>
DecideLocal == /\ paso = "modelos" /\ ~(clave /\ codigo = "main")
               /\ paso' = "decidido"
               /\ UNCHANGED <<codigo, clave, descargoHF, llamoJev, predIguales, costoIgual>>

\* Predicciones: deterministas solo con el mismo codigo y decisor local.
\* costo.json: .cache/reportes esta vacio, asi que guarda segundos y hardware del jurado.
Escribe == /\ paso = "decidido"
           /\ paso' = "comparado"
           /\ predIguales' = (codigo = "c7406f3" /\ ~llamoJev)
           /\ costoIgual' = FALSE
           /\ UNCHANGED <<codigo, clave, descargoHF, llamoJev>>

Fin == paso = "comparado" /\ UNCHANGED vars

Next == CargaModelos \/ DecideConJev \/ DecideLocal \/ Escribe \/ Fin
Spec == Init /\ [][Next]_vars

SinClaveNoLlamaJev == ~clave => ~llamoJev
SinClaveSinRed == ~clave => ~descargoHF
PrediccionesIgualesAEntrega == paso = "comparado" => predIguales
CostoIgualAEntrega == paso = "comparado" => costoIgual
====
