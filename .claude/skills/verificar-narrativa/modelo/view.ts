export const title = "Ciclo de vida de una narrativa (pipeline por lotes)";
const nombres: Record<string, string> = { suelto: "Suelto", candidata: "Candidata", nacida: "Nacida", activa: "Activa", mutando: "Mutando", latente: "Latente" };
export const state = (v: any) => nombres[v.estado];
export const group = (v: any) => (["suelto", "candidata"].includes(v.estado) ? "antes" : "viva");
export const colors = { antes: "tan", viva: "teal" };
export const step = (a: string, from: any, to: any) =>
  ({ AparecenCercanos: "aparecen comentarios cercanos", NoPasaValidacion: "no pasa la validación (ruido)",
     Nace: "pasa los filtros y nace", OtroDia: `pasa un día: ${nombres[to.estado].toLowerCase()}` } as any)[a] ?? a;
