#!/usr/bin/env python3
"""Parton level event generation: MadGraph5_aMC@NLO -> LHE.

Drell-Yan production of a colour singlet |Q| = 1 quirk pair with one hard
jet, p p > qk qk~ j, at LO with no merging. The quirk is a stable free
particle here: the infracolour string is applied later, in the detector
simulation.

  generate_lhe.py --mass 500 --events 1000 --out output/m500

--ptj cuts on the jet in the matrix element, so every event carries a hard
jet.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UFO = os.path.join(ROOT, "models", "QuirkDY_UFO")
PDGID = 10000100

PROC_CARD = """import model {ufo}
define p = g u c d s b u~ c~ d~ s~ b~
define j = p
generate p p > qk qk~ j
output {procdir} -f
"""

# Run card settings. nn23lo1 is NNPDF2.3 LO alpha_s = 0.130, built into
# MadGraph.
RUN_CARD = {
    "nevents": None,          # filled from the command line
    "iseed": None,
    "ptj": None,
    "ebeam1": 6800.0,         # 13.6 TeV
    "ebeam2": 6800.0,
    "use_syst": "False",      # no systematics weights
    "pdlabel1": "nn23lo1",
    "pdlabel2": "nn23lo1",
    "maxjetflavor": 5,
}


def set_run_card(path, settings):
    """Rewrite 'value = key' lines in a MadGraph run card, in place."""
    with open(path) as f:
        lines = f.readlines()
    seen = set()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(\S+)(\s*)=\s*(\w+)(\s*)(.*)$", line)
        if m and m.group(4) in settings:
            key = m.group(4)
            lines[i] = "  %s = %s %s\n" % (settings[key], key, m.group(6))
            seen.add(key)
    missing = set(settings) - seen
    if missing:
        sys.exit("run card has no entry for: %s" % ", ".join(sorted(missing)))
    with open(path, "w") as f:
        f.writelines(lines)


def set_quirk_mass(path, mass):
    """Set the quirk mass in the multichargedparticles block of the param card."""
    with open(path) as f:
        lines = f.readlines()
    block, done = None, False
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("block"):
            block = line.split()[1].lower()
        elif block == "multichargedparticles":
            parts = line.split()
            if parts and parts[0] == str(PDGID):
                lines[i] = "  %d %e # MQk\n" % (PDGID, mass)
                done = True
    if not done:
        sys.exit("no %d entry in the multichargedparticles block of %s" % (PDGID, path))
    with open(path, "w") as f:
        f.writelines(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mass", type=float, default=500.0, help="quirk mass [GeV]")
    ap.add_argument("--events", type=int, default=1000, help="LHE events to generate")
    ap.add_argument("--ptj", type=float, default=100.0,
                    help="jet pT cut in the matrix element [GeV]")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default=None, help="output directory (default output/m<mass>)")
    ap.add_argument("--procdir", default=None,
                    help="MadGraph process directory (default <out>/procdir, reused if present)")
    ap.add_argument("--keep-procdir", action="store_true",
                    help="do not delete the process directory afterwards (it is reusable)")
    args = ap.parse_args()

    out = os.path.abspath(args.out or os.path.join(os.environ.get("QG_OUT", "output"),
                                                   "m%g" % args.mass))
    os.makedirs(out, exist_ok=True)
    procdir = os.path.abspath(args.procdir or os.path.join(out, "procdir"))

    mg5 = shutil.which("mg5_aMC")
    if not mg5:
        sys.exit("mg5_aMC not on PATH, run: source setup.sh")

    # The process depends on the model alone, not on the mass or the cuts,
    # so one process directory serves every point.
    if not os.path.isdir(procdir):
        card = os.path.join(out, "proc_card.dat")
        with open(card, "w") as f:
            f.write(PROC_CARD.format(ufo=UFO, procdir=procdir))
        print("[generate_lhe] building the process in %s" % procdir, flush=True)
        # MadGraph writes parser caches and debug links into the working
        # directory, so keep it out of the source tree.
        subprocess.run([mg5, card], check=True, cwd=out)
    else:
        print("[generate_lhe] reusing the process in %s" % procdir, flush=True)

    settings = dict(RUN_CARD)
    settings["nevents"] = args.events
    settings["iseed"] = args.seed
    settings["ptj"] = args.ptj
    set_run_card(os.path.join(procdir, "Cards", "run_card.dat"), settings)
    set_quirk_mass(os.path.join(procdir, "Cards", "param_card.dat"), args.mass)

    run = "run_m%g_s%d" % (args.mass, args.seed)
    print("[generate_lhe] m = %g GeV, %d events, ptj > %g GeV, seed %d"
          % (args.mass, args.events, args.ptj, args.seed), flush=True)
    # generate_events takes the run name positionally.
    subprocess.run([os.path.join(procdir, "bin", "generate_events"), run, "-f"],
                   check=True, cwd=out)

    src = os.path.join(procdir, "Events", run, "unweighted_events.lhe.gz")
    if not os.path.exists(src):
        sys.exit("MadGraph produced no LHE file at %s" % src)
    dst = os.path.join(out, "events.lhe.gz")
    shutil.copyfile(src, dst)
    print("[generate_lhe] wrote %s" % dst)

    if not args.keep_procdir and args.procdir is None:
        shutil.rmtree(procdir, ignore_errors=True)


if __name__ == "__main__":
    main()
