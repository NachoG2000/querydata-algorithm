export const title = "Recorrido de un comentario (respuesta_a)";
export const state = (v: any) => {
  const r = Object.values(v.resuelto).filter(Boolean).length;
  return r === 3 ? "Todos con narrativa o ninguna" : r === 0 ? "Recién asignados por clustering" : "Propagando por respuesta_a";
};
export const step = (a: string) =>
  ({ ResolverRaiz: "el decisor fija la postura de una raíz", Heredar: "una respuesta toma lo del padre", CortarCiclo: "se detecta un ciclo y se corta", Terminado: "fin del lote" } as any)[a] ?? a;
