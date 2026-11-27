# Test plan

Goal: measure TJ-110's real performance and compare it with the model, so that the uncertain assumptions
(compressor quality, low-speed map, combustion efficiency, clearances) can be calibrated.

**Read [`docs/safety.md`](../docs/safety.md) first.**

## 1. Instruments

| Quantity | Sensor | Accuracy wanted |
|---|---|---|
| Shaft speed | Magnetic or optical pickup on the compressor nut (2 pulses/rev) | ±0.5 % |
| Thrust | Test stand on linear bearings + load cell (200 N) | ±1 N |
| EGT | K-type thermocouple, 1.5 mm sheathed, in the nozzle at mid-radius | ±5 °C |
| Compressor delivery pressure | Pressure transducer (0–300 kPa gauge) on a casing static tap behind the diffuser | ±1 kPa |
| Fuel flow | Weigh the fuel tank on a scale (g/s from slope), or a turbine flow meter | ±2 % |
| Ambient | Thermometer and barometer | ±0.5 °C, ±0.2 kPa |
| Vibration | Accelerometer on the front casing flange | trend only |

Log everything at ≥ 10 Hz; `experiments/run_log_template.csv` has the columns.

## 2. Sequence

| Step | What | Pass criterion |
|---|---|---|
| T0 | Rotor balance; spin-down test with starter only | Smooth run through 23 / 36 krpm; free spin-down > 10 s from 20 krpm |
| T1 | Propane ignition at 8–10 krpm | Stable flame inside the liner, no flame at the nozzle |
| T2 | Kerosene transition, accelerate to self-sustaining | Record self-sustaining speed and EGT |
| T3 | Idle hold 2 min | Stable EGT; record idle speed, thrust, fuel flow |
| T4 | Steps of 10 krpm to 80 krpm, 30 s each | EGT below 750 °C |
| T5 | Steps to 110 krpm | EGT below 750 °C; thrust and fuel recorded |
| T6 | Nozzle tuning | Adjust D9 to reach EGT ≈ 700 °C at 110 krpm |

Stop the run at once if: EGT > 850 °C, vibration rises suddenly, speed signal lost, fuel or fire outside the engine.

## 3. Analysis

`experiments/analyze.py` reads the logs, corrects to ISA conditions (θ = T0/288.15, δ = p0/101.325 kPa),
and overlays measured thrust, EGT and fuel flow on the model's throttle curve, with uncertainty bands.

| Measured | Calibrates |
|---|---|
| Compressor delivery pressure vs speed | Compressor efficiency / build penalty |
| Thrust and fuel flow vs speed | Overall model; combustion efficiency |
| Idle speed | Low-speed compressor map |
| EGT vs nozzle area | Turbine efficiency and capacity |

```
.venv/bin/python experiments/analyze.py experiments/runs/*.csv
```
