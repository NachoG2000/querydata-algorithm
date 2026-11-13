export const title = "Evidencia de coordinación entre dos cuentas";
export const state = (v: any) => {
  const pares = Object.values(v.detectado).filter((s: any) => s.length > 0).length;
  const fase = v.ops.length ? "En una operación" : v.marcadas.length ? "Cuentas coordinadas" : pares === 0 ? "Sin coincidencias" : pares === 1 ? "Una coincidencia" : "Dos coincidencias";
  return fase;
};
export const step = (accion: string) =>
  ({
    Coincidir: "un par de comentarios coincide (exacta o paráfrasis)",
    Marcar: "el peso de la arista supera el soporte",
    Agrupar: "la comunidad asigna una operación",
    Fin: "no hay más coincidencias",
  })[accion] ?? accion;
