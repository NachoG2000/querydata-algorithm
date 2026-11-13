#!/usr/bin/env bash
# Uso (desde la raíz del repo): STATECHART=<script de /statechart> PYTHON=<python con pandas/sklearn/networkx> .claude/skills/verificar-coordinacion/run.sh [--romper]
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$DIR/../../.." && pwd)"
PY="${PYTHON:-python}"
OUT="${OUT:-${TMPDIR:-/tmp}/verificar-coordinacion}"
CFG="modelo.cfg"
[ "${1:-}" = "--romper" ] && CFG="modelo-roto.cfg"
estado=0
if [ -n "${STATECHART:-}" ]; then
  echo "== Modelo TLA+ ($CFG) -> $OUT"
  (cd "$DIR" && "$STATECHART" modelo.tla --config "$CFG" --view view.ts --out "$OUT") || estado=1
else
  echo "== Modelo TLA+ omitido: definí STATECHART (ver /statechart)"
fi
echo "== Chequeo sobre pipeline.coordinacion, pipeline.unir_detecciones, entrega/cuentas.csv y experiments.tsv"
(cd "$RAIZ" && "$PY" "$DIR/verificar.py" "$@") || estado=1
exit $estado
