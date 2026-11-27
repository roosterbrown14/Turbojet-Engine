# Methodology

How the models are built, what they assume, and how they are checked.

## 1. Model structure

| Module | What it does | Key assumption |
|---|---|---|
| `src/tj/gas.py` | Semi-perfect gas properties; combustion fuel–air ratio; flame temperature | Complete combustion, no dissociation |
| `src/tj/fuels.py` | Fuel data (Jet A-1, kerosene, diesel, propane, butane, ethanol) | Handbook LHVs, surrogate formulas |
| `src/tj/compressor.py` | Meanline sizing of a centrifugal stage; semi-empirical map | Efficiency from correlations, not CFD |
| `src/tj/turbine.py` | Meanline axial turbine; blade and disc stresses | Soderberg losses; uniform disc |
| `src/tj/combustor.py` | Liner volume, residence time, loading, hole area, air split | Combustion efficiency is an input (0.90) |
| `src/tj/cycle.py` | Design-point cycle | Steady, 1-D, adiabatic |
| `src/tj/engine.py` | Integrates everything; iterates the cycle until component efficiencies agree | – |
| `src/tj/offdesign.py` | Running line / throttle curve | Map shape assumed; Stodola turbine |
| `src/tj/rotor.py` | Finite-element rotordynamics | Linear isotropic bearings, no damping |
| `src/tj/materials.py` | Strength vs temperature, Larson–Miller creep, costs | Approximate handbook trends (not allowables) |

The integrated design (`engine.build`) is not given component efficiencies. It sizes the compressor for the
flow, pressure ratio and speed, takes the resulting efficiency, runs the cycle, sizes the turbine for the
required work, takes *its* efficiency, and repeats until the two agree (typically 5–8 iterations).
That is what makes the parameter studies meaningful: changing the pressure ratio, for example, changes the
impeller diameter, its Reynolds number and its clearance-to-height ratio, and so its efficiency.

## 2. Assumptions with the biggest effect

| Assumption | Value | Why | Effect if wrong |
|---|---|---|---|
| Compressor "build quality" penalty | −4 efficiency points | Hand-made hobby/university parts are rougher, with less accurate blades than commercial wheels | ±3 points → +4.5 / −2.5 N thrust (I1) |
| Tip clearances | 0.30 mm both wheels | Realistic for careful home machining and bearing play | 0.15–0.5 mm → +3 / −5 N |
| Combustion efficiency | 0.90 | Reported range for small vaporizer combustors is 85–95 % | Fuel use only (±2.5 g/kN·s) |
| Combustor pressure loss | 5 % | Typical small annular liner | 3–8 % → +3 / −4 N |
| Mechanical efficiency | 0.98 | Two high-speed ball bearings | Small |
| Leakage | 2 % of air bypasses the turbine | Bearing cooling flow and labyrinth leakage | Small |
| Compressor map shape | Optimum flow ∝ n^1.5, surge at 0.66 × optimum flow | Typical small turbocharger maps | Governs idle speed and part-load results |
| Material data | Approximate handbook curves | No certified data for this project | Life and margins could be off by ×2–10 in time |

## 3. Numerical methods

- Isentropic and enthalpy inversions: Newton iteration to 10⁻⁶ K.
- Combustion fuel–air ratio: Newton iteration on the energy balance to 10⁻⁹.
- Design-point coupling: fixed-point iteration on turbine efficiency to 10⁻⁶.
- Off-design: bounded nonlinear least squares (`scipy.optimize.least_squares`) on three residuals,
  marching down in speed from the design point. A point is "converged" when every residual is below 10⁻⁵.
  Below about 51 krpm no solution exists: the model engine cannot sustain itself there.
- Rotordynamics: 40 Euler–Bernoulli beam elements (consistent mass), 2 DOF per node in the complex whirl
  coordinate; whirl frequencies from a linearized quadratic eigenproblem; critical speeds from the
  synchronous eigenproblem. 40 elements converge the first three modes to better than 10⁻⁵ (V3).

## 4. Verification (does the code solve the equations correctly?)

Run `simulations/verification.py`; results in `data/verification_summary.csv` and [V1](../charts/V1_verification.png).

| Check | Result |
|---|---|
| Air cp vs JANAF tables, 300–1500 K | within 0.45 % |
| First-law energy closure of an ideal engine | exact (< 10⁻⁶) |
| Beam natural frequencies vs exact solution | < 0.001 % |
| Disc stresses vs closed form | exact at the bore; average hoop within 0.5 % |
| Off-design solver at 100 % speed reproduces the design point | exact |
| 18 automated tests (`tests/`) | all pass; run on every push |

## 5. Validation (does the model match reality?)

There are **no measurements from this engine yet**. The only external check is a published 110 mm micro
turbojet (van den Hout & Koullen 1996). With the paper's stated pressure ratio, turbine inlet temperature,
mass flow and speed, and our own component models filling in everything else:

| Quantity | Published | This model | Difference |
|---|---|---|---|
| Thrust | 40 N | 42.6 N | +6 % |
| TSFC | 62.5 g/kN·s | 58.1 g/kN·s | −7 % |
| Outer diameter | 110 mm | 102 mm | −7 % |

That is encouraging but it is one engine, compared on abstract values only. The low-speed part of the
model (idle) is the least trustworthy: real engines of this class idle at 30–40 % speed, while the model
cannot sustain itself below about 46 % (51 krpm). Treat idle speed as unknown until measured.

## 6. Provenance labels

Every chart footer says where its numbers come from:

| Label | Meaning |
|---|---|
| numerical simulation | Output of the models above (unvalidated) |
| off-design matching | As above, using the assumed compressor map |
| finite-element rotordynamics | Beam FE model |
| analytical calculation | Closed-form equations |
| approximate handbook data | Material property trends, not design allowables |
| qualitative engineering assessment | Judgement, not measured |
