#!/usr/bin/env bash
# Uso: STATECHART=<script statechart de pstack> PYTHON=<python con pandas> .claude/skills/verificar-entrega/run.sh [--romper] [--tests]
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${OUT:-${TMPDIR:-/tmp}/verificar-entrega-$(date +%Y%m%d-%H%M%S)-$$}"
PY="${PYTHON:-python}"
mkdir -p "$OUT"
estado=0
if [ -n "${STATECHART:-}" ]; then
  "$STATECHART" "$DIR/modelo.tla" --config "$DIR/modelo.cfg" --view "$DIR/view.ts" --out "$OUT/real" > "$OUT/real.txt" 2>&1
  "$STATECHART" "$DIR/modelo.tla" --config "$DIR/modelo-guardado.cfg" --view "$DIR/view.ts" --out "$OUT/guardado" > "$OUT/guardado.txt" 2>&1
  echo "== modelo tal como opera el repo (modelo.cfg)"; grep -E "breaks|^[A-Z][A-Za-z]+(, [A-Za-z]+)*$" "$OUT/real.txt"
  echo "== modelo con las tres guardas (modelo-guardado.cfg)"; grep -E "breaks|^[A-Z][A-Za-z]+(, [A-Za-z]+)*$" "$OUT/guardado.txt"
  grep -q "breaks" "$OUT/guardado.txt" && estado=1
else
  echo "STATECHART no definido: se omite el modelo TLA+"
fi
cd "$DIR/../../.." && "$PY" "$DIR/verificar.py" "$@" || estado=1
echo "salida TLA+ en $OUT"
exit $estado
