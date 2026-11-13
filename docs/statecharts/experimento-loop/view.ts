export const title = "Un experimento del loop de mejora";
export const state = (v: any) => {
  const p = v.empeora ? "alguna partición empeora" : "ninguna partición empeora";
  switch (v.fase) {
    case "propuesta": return "Hipótesis declarada (A, B o mixta)";
    case "editado": return "Cambio sin commitear";
    case "fallo": return "Corrida cortada, sin fila";
    case "medido": return `Fila pendiente, ${p}`;
    case "commiteado": return `Código commiteado, ${p}`;
    case "aceptado": return `Fila aceptada, ${p}`;
    case "descartado": return "Fila descartada, diff por revertir";
    case "cerrado": return v.fila === "ninguna" ? "Ciclo cerrado sin fila" : v.fila === "aceptada" ? `Cerrado aceptado, ${p}` : "Cerrado descartado, fila guardada";
  }
  return v.fase;
};
export const group = (v: any) =>
  v.fase === "cerrado" ? "cierre" : ["medido", "commiteado", "aceptado", "descartado"].includes(v.fase) ? "registro" : "corrida";
export const colors = { corrida: "blue", registro: "purple", cierre: "teal" };
const labels: Record<string, string | null> = {
  Edita: "edita pipeline.py",
  CorridaFalla: "eval.py falla o se pasa de tiempo",
  CorridaTermina: "eval.py puntúa completo y tres particiones",
  CommitCodigo: "commit del código",
  MarcaAceptada: "eval.py --marcar accepted",
  MarcaDescartada: "eval.py --marcar discarded",
  RestauraSoloSuDiff: "revierte sólo su diff",
  GitResetHard: "git reset --hard",
  RestauraTrasFalla: "revierte el cambio",
  CommitBitacora: "commit de la bitácora",
  Fin: null,
};
export const step = (a: string) => labels[a];
