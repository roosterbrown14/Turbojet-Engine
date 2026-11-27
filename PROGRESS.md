# Progress log

Read this first when resuming work. Last updated 2026-11-26. Units: SI metric (mm, N, kPa, °C, krpm); costs in CAD.

## Status
- Modelling, design, CAD and documentation are complete for a first full pass.
- **No engine has been built. No measured data exists.**
- Repository: https://github.com/roosterbrown14/Turbojet-Engine

## Completed
| Area | Where |
|---|---|
| Physics, governing equations, literature review (40 sources, 34 DOIs checked) | `docs/physics.md`, `docs/literature_review.md` |
| Gas properties, cycle, compressor and turbine meanline, combustor, off-design, rotordynamics, materials models | `src/tj/` |
| Phase A design point; B cycle trades; C compressor; D turbine; E materials; F combustor and fuels; G off-design; H rotordynamics; I sensitivity, Monte Carlo, design-space search | `simulations/`, `docs/results/` |
| Verification (JANAF, first law, exact beam and disc solutions, off-design consistency) and published-engine benchmark (±7 %) | `simulations/verification.py`, `docs/methodology.md` |
| Recommendations answering 16 research questions | `docs/recommendations.md` |
| 3-D models of every part, assembly, viewers, BOM, interference check | `cad/` |
| Drawings: assembled section, cutaway, exploded views (2-D and 3-D), parts sheet, parts list | `prototypes/` |
| Test plan, log template, analysis script, safety (Canadian references) | `experiments/`, `docs/safety.md` |
| Project report (PDF) | `docs/report/` |
| 18 automated tests, run on GitHub for every push | `tests/`, `.github/workflows/tests.yml` |

## Main findings (model-based, unvalidated)
- TJ-110: 111 N, 0.37 L/min kerosene, EGT 715 °C at 110 krpm; Ø119 mm.
- PR is limited by the Al 2618 impeller (SF 1.24 at PR 2.8). Titanium allows PR ≈ 3.2+.
- Bearings must be soft-mounted (O-rings, ≈ 1.5 × 10⁶ N/m): hard mounts put two critical speeds in the operating range.
- Builder-controlled factors that matter most: compressor quality, combustor pressure loss, turbine tip clearance.
- Hot starts, not steady creep, limit turbine life at the design TIT.

## In progress
- CAD write-ups: `cad/README.md`, `prototypes/README.md` (manufacturing routes, assembly, balancing, CAD cost estimate `prototypes/TJ110_cost_estimate.csv`, blank results sheet). Paused awaiting the author's go-ahead.

## Known limitations
- Loss correlations calibrated on larger machines; no CFD.
- Low-speed compressor map assumed: idle prediction (51 krpm) is likely pessimistic.
- Material data are approximate handbook trends; no certified IN713C creep data located.
- No transient, heat-transfer or unbalance-response models.

## Next actions
1. Get quotes for the cast IN713C turbine blank and 5-axis machining of the impeller (or choose a commercial turbo wheel and re-match the diffuser).
2. Build the rotor and run test T0 (balance, spin through the rigid-body modes on the starter).
3. Run T1–T6 per `experiments/test_plan.md`; calibrate compressor efficiency, combustion efficiency and the low-speed map.
4. Add a transient start-up model (spool-up with starter torque and fuel schedule).
5. CFD of the impeller and diffuser to replace the build-quality assumption.
6. Fill in `docs/design_log.md` (author's own account) and add photos and video once built.
