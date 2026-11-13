export const title = "Demo: recorrer el vault de Obsidian";
export const state = (v: any) => {
  switch (v.nota) {
    case "indice": return "Índice";
    case "operacion": return "Operación coordinada";
    case "fuente": return "Fuente (medio)";
    case "narrativa":
      if (!v.conOp) return "Narrativa sin operación";
      return v.diasAmp ? "Narrativa amplificada, con su operación" : "Narrativa con operación, 0 días amplificada";
  }
  return v.nota;
};
export const group = (v: any) => (v.nota === "indice" ? "indice" : v.nota === "narrativa" ? "narrativa" : "otras");
export const colors = { indice: "teal", narrativa: "purple", otras: "tan" };
export const step = (a: string, from: any, to: any) => {
  if (a === "VuelveAlIndice") return from.nota === "narrativa" ? "vuelve con Atrás (no hay enlace al índice)" : null;
  if (a === "IndiceANarrativa") return to.conOp && !to.diasAmp ? "abre una narrativa [sin salida/final]" : "abre una narrativa de la tabla";
  if (a === "FuenteANarrativa") return null;
  if (a === "OperacionANarrativa") return "abre una narrativa que empuja";
  return ({
    IndiceAOperacion: "abre una operación de la tabla",
    NarrativaAOperacion: "abre la operación relacionada",
    NarrativaAFuente: "abre una fuente relacionada",
    OperacionAFuente: "abre una fuente relacionada",
    FuenteAOperacion: "abre una operación del medio",
  } as any)[a];
};
