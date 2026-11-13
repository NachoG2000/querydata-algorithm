#!/usr/bin/env bash
# Uso: STATECHART=<ruta al script statechart de /statechart> .claude/skills/verificar-loop/run.sh [--romper]
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$DIR/../../.." && pwd)"
PY="${PYTHON:-python}"
OUT="${OUT:-${TMPDIR:-/tmp}/verificar-loop}"
CFG="modelo.cfg"
[ "${1:-}" = "--romper" ] && CFG="modelo-roto.cfg"
estado=0
if [ -n "${STATECHART:-}" ]; then
  echo "== Modelo TLA+ ($CFG) -> $OUT"
  (cd "$DIR" && "$STATECHART" modelo.tla --config "$CFG" --view view.ts --out "$OUT") || estado=1
else
  echo "== Modelo TLA+ omitido: definí STATECHART (ver /statechart)"
fi
echo "== Chequeo sobre experiments.tsv y git"
(cd "$RAIZ" && "$PY" "$DIR/verificar.py" "$@") || estado=1
exit $estado
