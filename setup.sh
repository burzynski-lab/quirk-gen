# Environment for quirk-gen: an LCG view providing MadGraph5_aMC@NLO,
# Pythia8 with python bindings and pyHepMC3.
#   source setup.sh
LCG_VIEW=${LCG_VIEW:-/cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc13-opt}
if [ ! -d "$LCG_VIEW" ]; then
    echo "no LCG view at $LCG_VIEW, set LCG_VIEW to one that exists" >&2
    return 1
fi
source "$LCG_VIEW/setup.sh" || return 1
export QG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export QG_OUT="${QG_OUT:-$QG_ROOT/output}"
export PATH="$QG_ROOT/scripts:$PATH"
echo "quirk-gen: $QG_ROOT"
echo "  view     $LCG_VIEW"
echo "  mg5_aMC  $(readlink -f "$(command -v mg5_aMC)" | sed 's|.*/madgraph5amc/||; s|/.*||')"
echo "  pythia8  $(pythia8-config --version 2>/dev/null)"
echo "  python   $(python3 -V 2>&1 | awk '{print $2}')"
echo "  output   $QG_OUT"
