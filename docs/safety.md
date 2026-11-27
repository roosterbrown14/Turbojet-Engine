# Safety

**A small turbojet is dangerous.** Its wheels store enough energy to go through a person if they burst. It
burns several litres of fuel per run, its exhaust is ~700 °C and over 400 m/s, and it is loud enough to cause
permanent hearing damage. Build and run it only with experienced supervision (a university lab, or an
experienced model-turbine builder), never alone.

## 1. Stored energy and containment

| Rotating part | Mass | Kinetic energy at 110 krpm |
|---|---|---|
| Compressor wheel | ≈ 75 g | ≈ 1.9 kJ |
| Turbine wheel | ≈ 175 g | ≈ 5 kJ |

Together that is more than the muzzle energy of a high-powered hunting rifle. The 1 mm stainless casing **will not contain a wheel burst.**

- Never stand in the **plane of rotation** of either wheel while the engine runs. Mark it on the stand.
- Run behind a barrier: steel plate or sandbags on the plane of the wheels, polycarbonate for viewing.
- The ECU must **limit speed** (110 krpm max) and shut down on loss of the speed signal.
  The impeller reaches yield at about +11 % overspeed.
- **Inspect the wheels** before every run day: blade tips, nicks from ingested debris, signs of rubbing.
  Fit an inlet screen.

## 2. Fire and fuel

- Kerosene (Jet A-1 / K-1) only. **Never gasoline.**
- Run outdoors or in a test cell, with **two CO₂ fire extinguishers** within reach (a CO₂ extinguisher won't
  damage the engine). Have a person whose only job is the extinguisher.
- **Hot start** is the most common accident: too much fuel before light-off, then a fireball from the nozzle.
  Never pump fuel before the propane flame is established. Have a procedure for "wet start: stop fuel,
  keep spinning with the starter to purge".
- Store fuel in approved containers, away from the stand. Fuel lines: fuel-rated tubing with clamps; fuel
  shut-off valve operated by the ECU and a manual one.
- Propane start gas: regulator, solenoid valve, leak test with soapy water.

## 3. Hot parts and exhaust

- The exhaust is ~630 °C and 440 m/s at the nozzle, and still dangerous 2 m behind. Keep a clear zone behind
  the engine and point it away from anything that can burn.
- The casing, nozzle and stand will burn skin for many minutes after shutdown.

## 4. Noise

Expect 120–130 dB(A) near the engine. **Ear protection (plugs + muffs) for everyone within 15 m.**
Check local noise bylaws before running outdoors.

## 5. Running procedure (summary)

1. Pre-run checklist: wheels inspected and free to spin, nuts torqued and marked, fuel and gas lines
   leak-tested, sensors working, area clear, extinguishers and barrier in place, ear protection on.
2. Starter to ~8–10 krpm, propane on, igniter on, confirm light-off by EGT rise.
3. Kerosene in gradually, accelerate to idle under ECU control. Starter off above self-sustaining speed.
4. Never exceed the EGT limit (750 °C steady, 850 °C for a few seconds).
5. Shutdown: throttle to idle 30 s, fuel off, keep the starter spinning to cool and purge for 30–60 s.

## 6. Canadian rules to know about

- **Flying** a turbine-powered model aircraft in Canada falls under Transport Canada's drone/RPAS rules (Canadian
  Aviation Regulations, Part IX) and, in practice, Model Aeronautics Association of Canada (MAAC) turbine rules.
  This project is a **ground test stand only**.
- **Workplace / university labs:** your provincial occupational health and safety regulations apply (hearing
  conservation, hot work, flammable liquids); follow your institution's hot-work and test-cell procedures.
- Flammable-liquid storage follows the National Fire Code of Canada and local fire-department rules.

This list is a pointer, not legal advice. Check the current rules for your province and institution.
