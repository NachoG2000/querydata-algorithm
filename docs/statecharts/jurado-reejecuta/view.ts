export const title = "El jurado re-ejecuta el pipeline";
export const state = (v: any) => {
  const quien = v.codigo === "main" ? "main" : "commit de la entrega";
  const k = v.clave ? "con clave" : "sin clave";
  switch (v.paso) {
    case "clonado": return `Repo clonado (${quien}, ${k})`;
    case "modelos": return `Modelos bajados (${quien}, ${k})`;
    case "decidido": return v.llamoJev ? "Posturas decididas por Jev" : `Posturas decididas en local (${quien})`;
    case "comparado": return v.predIguales ? "Predicciones iguales, costo distinto" : "Predicciones distintas a entrega/";
  }
  return v.paso;
};
export const group = (v: any) => (v.paso === "comparado" ? "resultado" : "corrida");
export const colors = { corrida: "blue", resultado: "orange" };
export const step = (a: string) => ({
  CargaModelos: "baja los modelos de Hugging Face",
  DecideConJev: "manda raíces dudosas a Jev",
  DecideLocal: "decide postura con NLI local",
  Escribe: "escribe entrega/ y compara con la del repo",
  Fin: null,
} as any)[a];
