#!/usr/bin/env python3
"""Particle level event generation: Pythia8 showers an LHE into HepMC3.

The quirks are stable, charge +-1, spin 1/2 colour singlets, free particles
in the record. The infracolour string between them belongs to the detector
simulation.

  shower.py --lhe events.lhe --out events.hepmc --mass 500
"""
import argparse
import json
import os
import sys

import pythia8
from pyHepMC3 import HepMC3 as hm

PDGID = 10000100
# String tension Lambda^2 from eV^2 to MeV/mm: 1e-12 / (hbar c = 1.9733e-10 MeV mm).
STRINGFORCE_PER_EV2 = 5.068e-3

# A14 tune. PDF:pSet 13 is NNPDF2.3 QCD+QED LO alpha_s = 0.130, built
# into Pythia.
A14 = [
    "Tune:ee = 7", "Tune:pp = 14", "PDF:pSet = 13",
    "SpaceShower:rapidityOrder = on", "SpaceShower:rapidityOrderMPI = on",
    "SigmaProcess:alphaSvalue = 0.140",
    "SpaceShower:pT0Ref = 1.56", "SpaceShower:pTmaxFudge = 0.91",
    "SpaceShower:pTdampFudge = 1.05", "SpaceShower:alphaSvalue = 0.127",
    "TimeShower:alphaSvalue = 0.127",
    "BeamRemnants:primordialKThard = 1.88",
    "MultipartonInteractions:pT0Ref = 2.09",
    "MultipartonInteractions:alphaSvalue = 0.126",
    "ColourReconnection:range = 1.71",
    "ParticleDecays:limitTau0 = on", "ParticleDecays:tau0Max = 10.0",
    "Main:timesAllowErrors = 500", "Check:epTolErr = 1e-2",
]


def to_hepmc(event, number, xsec):
    """Pythia event -> HepMC3 GenEvent, in GeV and mm.

    Particles keep Pythia's HepMC status (4 beam, 1 final, 2 decayed), and
    each distinct set of mothers becomes one vertex.
    """
    evt = hm.GenEvent(hm.Units.GEV, hm.Units.MM)
    evt.set_event_number(number)

    parts, groups = {}, {}
    for i in range(1, event.size()):
        p = event[i]
        gp = hm.GenParticle(hm.FourVector(p.px(), p.py(), p.pz(), p.e()),
                            p.id(), p.statusHepMC())
        gp.set_generated_mass(p.m())
        parts[i] = gp
        mothers = tuple(sorted(m for m in p.motherList() if m > 0))
        groups.setdefault(mothers, []).append(i)

    for mothers, children in groups.items():
        if not mothers:                      # the two beams
            for i in children:
                evt.add_beam_particle(parts[i])
            continue
        first = event[children[0]]
        vtx = hm.GenVertex(hm.FourVector(first.xProd(), first.yProd(),
                                         first.zProd(), first.tProd()))
        for m in mothers:
            vtx.add_particle_in(parts[m])
        for c in children:
            vtx.add_particle_out(parts[c])
        evt.add_vertex(vtx)

    cs = hm.GenCrossSection()
    cs.set_cross_section(xsec, 0.0)
    evt.set_cross_section(cs)
    return evt


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lhe", required=True)
    ap.add_argument("--out", default="events.hepmc")
    ap.add_argument("--mass", type=float, default=500.0, help="quirk mass [GeV]")
    ap.add_argument("--lam", "--lambda", dest="lam", type=float, default=400.0,
                    help="infracolour scale [eV], recorded in the metadata only")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    pythia = pythia8.Pythia()
    pythia.readString("Beams:frameType = 4")
    pythia.readString("Beams:LHEF = %s" % args.lhe)
    pythia.readString("Random:setSeed = on")
    pythia.readString("Random:seed = %d" % args.seed)
    for cmd in A14:
        pythia.readString(cmd)
    # spin 1/2, charge +1 (3 x e/3), colour singlet, zero width, stable
    pythia.readString("%d:new = qk qk~ 2 3 0 %g 0.0 0.0 0.0 0.0" % (PDGID, args.mass))
    pythia.readString("%d:isResonance = false" % PDGID)
    pythia.readString("%d:mayDecay = false" % PDGID)

    if not pythia.init():
        sys.exit("shower: Pythia failed to initialise on %s" % args.lhe)

    writer = hm.WriterAscii(args.out)
    n = 0
    while True:
        if not pythia.next():
            if pythia.infoPython().atEndOfFile():
                break
            continue
        n += 1
        writer.write_event(to_hepmc(pythia.event, n,
                                    pythia.infoPython().sigmaGen() * 1e9))
    writer.close()
    pythia.stat()

    # Pythia reports mb, the metadata is in pb.
    sigma_pb = pythia.infoPython().sigmaGen() * 1e9
    meta = {
        "pdgid": PDGID,
        "charge": 1,
        "mass_gev": args.mass,
        "lambda_ev": args.lam,
        "stringforce_mev_per_mm": args.lam ** 2 * STRINGFORCE_PER_EV2,
        "n_infracolour": 2,
        "sigma_pb": sigma_pb,
        "sigma_pb_times_nic": 2.0 * sigma_pb,
        "events": n,
        "seed": args.seed,
    }
    path = os.path.splitext(args.out)[0] + ".json"
    with open(path, "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    print("[shower] wrote %d events to %s" % (n, args.out))
    print("[shower] wrote %s" % path)
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
