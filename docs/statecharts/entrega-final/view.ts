export const title = "Entrega final: de la rama a main";
export const state = (v: any) => {
  switch (v.fase) {
    case "rama": return "Candidato en la rama de mejoras";
    case "intacto": return "Main y entrega intactos";
    case "verificado": return "Candidato supera la referencia";
    case "integrado": return "Merge local, entrega vieja";
    case "regenerado": return "Entrega regenerada en frío";
    case "publicado": return v.origenEntrega === v.origenCodigo ? "Main publicado con su entrega" : "Main publicado con entrega de otro código";
  }
  return v.fase;
};
export const group = (v: any) => (v.fase === "publicado" || v.fase === "intacto" ? "main" : "trabajo");
export const colors = { trabajo: "blue", main: "teal" };
const labels: Record<string, string | null> = {
  Verifica: "pasa completo y las tres particiones",
  NoSupera: "no supera a c7406f3",
  Merge: "merge a main",
  CorreEnFrio: "corre el set final sin caché de embeddings",
  SubeConEntrega: "commit y push de código y entrega/",
  SubeSinRegenerar: "push sin regenerar [cierre apurado]",
  Fin: null,
};
export const step = (a: string) => labels[a];
