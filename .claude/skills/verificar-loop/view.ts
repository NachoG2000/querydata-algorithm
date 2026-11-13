const nombres: Record<string, string> = {
  inicio: "Sin experimento en curso",
  propuesta: "Hipótesis editada",
  corriendo: "eval.py corriendo",
  evaluada: "Fila pendiente en experiments.tsv",
  aceptada: "Aceptada (commit)",
  descartada: "Descartada (git reset)",
  registrada: "Registrada en experiments.tsv",
};
export const title = "Loop de experimentación";
export const state = (v: any) => nombres[v.fase] ?? v.fase;
export const step = (accion: string) =>
  ({
    Proponer: "el agente edita el código",
    Correr: "se lanza python eval.py",
    Evaluar: "eval.py puntúa y agrega la fila",
    Aceptar: "la regla de aceptación pasa",
    Descartar: "la regla falla",
    Marcar: "python eval.py --marcar",
    Fin: "se agota el presupuesto",
  })[accion] ?? accion;
