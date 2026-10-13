#!/bin/bash
# MadGraph -> LHE -> Pythia8 -> HepMC3, in one command.
#
#   source setup.sh
#   scripts/run_chain.sh --mass 500 --events 1000
#
#   --mass G      quirk mass in GeV                 (default 500)
#   --events N    events to generate                (default 1000)
#   --ptj G       jet cut in the matrix element GeV (default 100)
#   --lambda EV   infracolour scale, recorded only  (default 400)
#   --seed N      random seed                       (default 1)
#   --out DIR     output directory                  (default $QG_OUT/m<mass>)
set -e
MASS=500; EVENTS=1000; PTJ=100; LAMBDA=400; SEED=1; OUT=
while [ $# -gt 0 ]; do
    case $1 in
        --mass) MASS=$2; shift 2;;
        --events) EVENTS=$2; shift 2;;
        --ptj) PTJ=$2; shift 2;;
        --lambda) LAMBDA=$2; shift 2;;
        --seed) SEED=$2; shift 2;;
        --out) OUT=$2; shift 2;;
        -h|--help) sed -n '2,13p' "$0"; exit 0;;
        *) echo "unknown option: $1" >&2; exit 2;;
    esac
done
[ -n "$QG_ROOT" ] || { echo "run: source setup.sh" >&2; exit 1; }
OUT=${OUT:-$QG_OUT/m$MASS}
mkdir -p "$OUT"

python3 "$QG_ROOT/scripts/generate_lhe.py" --mass "$MASS" --events "$EVENTS" \
        --ptj "$PTJ" --seed "$SEED" --out "$OUT"

# Pythia reads an uncompressed LHE file.
gunzip -fc "$OUT/events.lhe.gz" > "$OUT/events.lhe"
python3 "$QG_ROOT/scripts/shower.py" --lhe "$OUT/events.lhe" \
        --out "$OUT/events.hepmc" --mass "$MASS" --lambda "$LAMBDA" --seed "$SEED"
rm -f "$OUT/events.lhe"

echo
echo "quirk-gen done:"
echo "  $OUT/events.hepmc        particle level events for the simulation"
echo "  $OUT/events.json         mass, lambda, cross section, event count"
