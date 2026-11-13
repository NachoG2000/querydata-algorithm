const nombres: Record<string, string> = {
  rama_experimental: "Rama experimental",
  verificada: "Verificada con eval.py",
  mergeada: "Mergeada en main",
  corrida_final: "Corrida final sobre datos/final",
  entregada: "Entregada",
};
export const title = "Entrega del set final";
export const state = (v: any) => nombres[v.fase];
export const group = (v: any) => (v.fase === "entregada" ? "fin" : "proceso");
export const colors = { fin: "teal", proceso: "blue" };
export const step = (accion: string) =>
  ({
    Verificar: "eval.py compara contra el vigente",
    Descartar: "no supera al vigente: se entrega el vigente",
    Mergear: "se mergea la rama",
    CorridaFinal: "pipeline.py corre sobre el set final",
    EntregarSinRegenerar: "se cierra sin regenerar entrega/",
    Entregar: "se entrega",
    Done: null,
  } as Record<string, string | null>)[accion] ?? accion;
