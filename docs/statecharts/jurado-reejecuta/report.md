# JuradoReejecuta

TLC reached 16 states and 16 steps. The chart draws 13 states and 11 arrows.
The view hides 4 steps, so the chart does not draw them.

## SinClaveSinRed breaks
The shortest path has 1 step:
0. Repo clonado (main, sin clave)
1. baja los modelos de Hugging Face: Modelos bajados (main, sin clave)

## PrediccionesIgualesAEntrega breaks
The shortest path has 3 steps:
0. Repo clonado (main, sin clave)
1. baja los modelos de Hugging Face: Modelos bajados (main, sin clave)
2. decide postura con NLI local: Posturas decididas en local (main)
3. escribe entrega/ y compara con la del repo: Predicciones distintas a entrega/

## CostoIgualAEntrega breaks
The shortest path has 3 steps:
0. Repo clonado (main, sin clave)
1. baja los modelos de Hugging Face: Modelos bajados (main, sin clave)
2. decide postura con NLI local: Posturas decididas en local (main)
3. escribe entrega/ y compara con la del repo: Predicciones distintas a entrega/

## Rules that hold
SinClaveNoLlamaJev, NoDeadlock
