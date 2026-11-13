# ExperimentoLoop

TLC reached 17 states and 23 steps. The chart draws 14 states and 15 arrows.
The view hides 6 steps, so the chart does not draw them.

## TodaCorridaRegistrada breaks
The shortest path has 3 steps:
0. Hipótesis declarada (A, B o mixta)
1. edita pipeline.py: Cambio sin commitear
2. eval.py falla o se pasa de tiempo: Corrida cortada, sin fila
3. revierte el cambio: Ciclo cerrado sin fila

## AceptadaNoEmpeoraParticion breaks
The shortest path has 4 steps:
0. Hipótesis declarada (A, B o mixta)
1. edita pipeline.py: Cambio sin commitear
2. eval.py puntúa completo y tres particiones: Fila pendiente, alguna partición empeora
3. commit del código: Código commiteado, alguna partición empeora
4. eval.py --marcar accepted: Fila aceptada, alguna partición empeora

## Rules that hold
NoDeadlock
