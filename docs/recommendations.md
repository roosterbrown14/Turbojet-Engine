# Recommendations

What to build, why, and what to test first. Everything below is from models, **nothing has been measured**.

## 1. Research questions and answers

| # | Question | Answer | Confidence | Evidence |
|---|---|---|---|---|
| 1 | What thrust can a ~120 mm hobby-buildable turbojet make? | ≈ 110 N (90 % range 100–121 N for build scatter) at 0.37 L/min of kerosene | Medium (±10 % model, benchmark within 7 %) | [cycle](results/cycle.md), [sensitivity](results/sensitivity.md) |
| 2 | Best pressure ratio? | 2.8: highest an aluminum 2618 impeller can deliver with SF ≥ 1.2 | High (trend), medium (exact value) | B1–B2, I3 |
| 3 | Best turbine inlet temperature? | 1100 K (827 °C); above 1200 K turbine creep life drops fast | Medium (approximate creep data) | B2, E4 |
| 4 | Best shaft speed? | 110 krpm: sets a 119 mm engine; limited by bearing DN, not wheel stress | High | C1, H5 |
| 5 | Impeller backsweep and blades? | 30°, 7 + 7 splitters | Medium | C2 |
| 6 | How much does tip clearance matter? | ~1.5 N per 0.1 mm at the turbine, ~0.7 N at the compressor | Medium | C3 |
| 7 | Turbine loading? | ψ = 1.3, φ = 0.65 (reaction 0.35): flat efficiency region, short blades, NGV Mach 0.75 | Medium | D1–D2 |
| 8 | Weakest part mechanically? | The impeller: yields at about +11 % overspeed. The ECU speed limit is essential. | High | D5, E5 |
| 9 | Materials for each part? | 2618 wheel, 17-4PH shaft, hybrid 608 bearings, 310 SS liner, IN625 NGV, cast IN713C turbine, 321 SS nozzle | High for ranking | [materials](results/materials.md) |
| 10 | Fuel? | Jet A-1 or K-1 kerosene + ~5 % turbine oil; propane/butane to start | High | F2 |
| 11 | Combustor size? | 75 mm annular liner, 8 vaporizers, 30/25/45 % air split, 5.9 ms residence time | Medium | F3–F4 |
| 12 | Rotor dynamics? | Soft-mount the bearings (O-rings, ≈ 1.5 × 10⁶ N/m) to put rigid-body modes below idle; span ≤ 95 mm | Medium–high | H1–H3 |
| 13 | Idle and throttle? | Thrust ∝ speed³; EGT is U-shaped with a minimum near 75–80 krpm. Model idle 51 krpm (pessimistic) | Low for idle | G1 |
| 14 | Weather effects? | −30 °C: +31 % thrust; +35 °C: −11 %; Calgary altitude −8 % | Medium | G2 |
| 15 | How to tune on the stand? | Nozzle diameter: −2 mm ≈ +6 N and +135 °C EGT | Medium | G3 |
| 16 | Is the design point a good one? | Yes: best feasible point in a 660-design search | Medium | I3 |

## 2. Build options

| Option | What | Thrust | Cost (CAD) | Difficulty |
|---|---|---|---|---|
| **TJ-110** (recommended) | Full design in this repository | ≈ 110 N | $5,035–17,880 total incl. ECU and stand ([build package](../prototypes/README.md)) | High: needs 5-axis milling, a cast turbine blank, TIG welding, balancing |
| TJ-110T | Same, with a commercial turbocharger compressor wheel of similar size | similar | lower | Medium; must re-match diffuser to the wheel |
| TJ-110Ti | Ti-6Al-4V impeller, PR 3.2 | ≈ 115 N, −6 % TSFC | +CAD 400–900 | Titanium machining |

## 3. What to test first (in this order)

1. **Spin and balance the rotor** without combustion (air-driven or starter only, to ~30 krpm). Check that the
   O-ring mounts let it pass the 23 / 36 krpm rigid-body modes smoothly.
2. **Gas-only (propane) ignition** at low speed, confirm the flame stays in the liner.
3. **Kerosene running to 60 krpm**, measuring speed, EGT, fuel flow, thrust and compressor delivery pressure.
   Compare with the throttle curve ([G1](../charts/G1_throttle_curve.png)).
4. **Find the real idle speed** and the lowest stable speed.
5. **Step up to full speed** in 10 krpm increments; tune the nozzle for EGT ≈ 700 °C.

The test plan is in [`experiments/test_plan.md`](../experiments/test_plan.md). Read [`safety.md`](safety.md) first.

## 4. Biggest uncertainties to resolve by measurement

1. Compressor efficiency of a home-made wheel (the "build quality" assumption).
2. The low-speed compressor map, which decides idle.
3. Combustion efficiency and liner wall temperatures.
4. Real running clearances (thermal growth at start-up).
