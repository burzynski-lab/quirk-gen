# quirk-gen

Event generation for the quirk search. MadGraph5_aMC@NLO produces the hard
process and Pythia8 showers it, giving HepMC3 files that feed a DD4hep based
detector simulation.

The physics is Drell-Yan production of a colour singlet quirk pair with one hard
jet, `p p > qk qk~ j` at 13.6 TeV. The quirk carries the quantum numbers of a
right handed charged lepton plus an infracolour charge, so production goes
through gamma*/Z only. The quirks leave the generator as **stable free
particles**: the infracolour string between them is applied later, in the
detector simulation, where the string tension is set by Lambda.

## 1. Setup

Everything comes from one LCG view on cvmfs, so there is nothing to install.

```bash
git clone <this repo> quirk-gen
cd quirk-gen
source setup.sh          # prints the versions it picked up
```

Use a different view with `LCG_VIEW=/cvmfs/sft.cern.ch/lcg/views/<rel>/<platform> source setup.sh`.

## 2. Generate events

```bash
scripts/run_chain.sh --mass 500 --events 1000
```

That writes, into `output/m500/`:

| file | what |
|---|---|
| `events.hepmc` | particle level events, HepMC3 ASCII, the input to the simulation |
| `events.json` | mass, Lambda, string tension, cross section, event count |
| `events.lhe.gz` | the parton level events, kept so the shower can be rerun |

Options:

```
--mass G      quirk mass in GeV                 (default 500)
--events N    events to generate                (default 1000)
--ptj G       jet cut in the matrix element GeV (default 100)
--lambda EV   infracolour scale, recorded only  (default 400)
--seed N      random seed                       (default 1)
--out DIR     output directory
```

The two steps can also be run separately, which is what you want when scanning
Lambda, since Lambda does not change the events at all:

```bash
python3 scripts/generate_lhe.py --mass 500 --events 1000 --out output/m500
python3 scripts/shower.py --lhe output/m500/events.lhe --out output/m500/events.hepmc --mass 500
```

The shower uses Pythia's python bindings and pyHepMC3.

## 3. What the settings mean

**The jet.** Only a quirk pair recoiling against a hard jet is usable: the two
quirks are produced back to back, so the transverse momentum of the pair, which
sets how central the whole system is, is a small residual unless something
recoils against it. That is what `--ptj` asks for, as a cut in the matrix
element. Every event therefore has a hard jet by construction, and nothing is
filtered anywhere: every generated event is written.

**Only one jet multiplicity is generated**, so there is no MLM merging and the
sample is not inclusive. It is exact at LO for one hard jet, and a second jet
comes from the shower alone. Do not use it for total cross sections.

**N_IC = 2 is applied by hand.** MadGraph computes the cross section for a
single infracolour state. The physical cross section is `N_IC x sigma_MG`, the
same way `q qbar > c cbar` carries a colour factor of 3. `events.json` reports
both.

**PDFs.** MadGraph uses `nn23lo1` and Pythia uses `PDF:pSet = 13`. Both are
NNPDF2.3 QCD+QED LO with alpha_s = 0.130 and are built in, so no PDF set has to
be downloaded. The shower runs the A14 tune.

**Lambda.** The infracolour scale changes nothing in generation. It is recorded
in `events.json`, together with the string tension the simulation wants,
`Lambda^2 / (hbar c)` in MeV/mm, so that one generated sample can feed every
Lambda point.

## 4. The model

`models/QuirkDY_UFO` is the `multichargedParticles` UFO with one charge 1
state appended, since the upstream model only has Q = 0.3, 0.4, 0.6, 0.7, 1.5
and 2.0. Renumbering an existing state would not work, because the couplings are
hard coded literals rather than functions of the charge, so `qb1p5` relabelled
would give a cross section 2.25 times too large and the wrong gamma*/Z
interference.

| | |
|---|---|
| PDG id | 10000100, anti-quirk -10000100 |
| spin, colour, charge | 1/2 Dirac, singlet, +-1 |
| width | exactly zero, stable through the whole chain |

Changing the mass needs no model change, it is an LHA parameter. Changing the
charge does: copy the four `qk` blocks in `particles.py`, `parameters.py`,
`couplings.py` and `vertices.py` and change the charge literal consistently.

## 5. Layout

| path | what |
|---|---|
| `setup.sh` | sources the LCG view and sets `QG_ROOT` and `QG_OUT` |
| `models/QuirkDY_UFO/` | the UFO model |
| `scripts/generate_lhe.py` | MadGraph driver, writes the process, run and param cards |
| `scripts/shower.py` | Pythia8 shower and HepMC3 writer |
| `scripts/run_chain.sh` | both steps in one command |
| `output/` | generated events, not in git |

The MadGraph process directory is rebuilt per output directory and deleted
afterwards unless you pass `--keep-procdir`. It depends only on the model, not
on the mass or the cuts, so keeping it makes a mass scan much faster.
