# Literature review

Bibliography: [`references/references.bib`](../references/references.bib) is generated from Crossref by
`references/build_bib.py`. All DOIs below resolve on Crossref, and the title, authors and year of each
were checked against what is cited here. Textbooks and reports without a DOI are hand-entered in the
same script and are marked "(book)" or "(report)".

**How to read this document.** Each summary reports what a paper states in its abstract or what it is
widely known for. Where a number is quoted from a paper, it comes from that paper's own abstract
unless marked otherwise. Correlations marked *textbook form* are the standard forms as reproduced in
the textbooks listed in section 1 (mainly Dixon & Hall, Saravanamuttoo et al., Japikse, Lefebvre &
Ballal). The original papers were **not** read in full in this session, so the exact constants should
be checked against the textbook before they are frozen in code. Several entries have no abstract in
Crossref; for those, only the title and the paper's general reputation are used, and this is stated.
Nothing here was measured by this project. Units are SI throughout (K, Pa, kg/s, m, N).

## 1. Gas-turbine fundamentals and cycle analysis

| Ref | Contribution relevant to this project |
|---|---|
| Saravanamuttoo et al. 2017 (book) | *Gas Turbine Theory*, 7th ed. Standard treatment of Brayton-cycle design-point analysis with component efficiencies and pressure losses, plus chapters on centrifugal and axial turbomachinery and off-design matching. Main reference for the cycle model. |
| [Mattingly 2006](https://doi.org/10.2514/4.861789) | *Elements of Propulsion*. Parametric (on-design) and performance (off-design) analysis of turbojets, with specific thrust and TSFC as functions of compressor pressure ratio and turbine inlet temperature. Used for the turbojet thrust and nozzle equations. |
| Hill & Peterson 1992 (book) | *Mechanics and Thermodynamics of Propulsion*, 2nd ed. Turbojet cycle, nozzle flow and turbomachinery fundamentals. Independent cross-check of the cycle equations. |
| Dixon & Hall 2014 (book) | *Fluid Mechanics and Thermodynamics of Turbomachinery*, 7th ed. Velocity triangles, slip factors (Stanitz, Wiesner), the Smith chart and the Soderberg loss correlation. Main secondary source for the meanline models. |
| [Walsh & Fletcher 2004](https://doi.org/10.1002/9780470774533) | *Gas Turbine Performance*. Component maps, matching, off-design and transient performance, and typical component loss values. Used for the off-design matching approach and for sanity ranges on pressure losses. |
| [Lefebvre & Ballal 2010](https://doi.org/10.1201/9781420086058) | *Gas Turbine Combustion*, 3rd ed. Combustor sizing, the θ loading parameter, combustion efficiency, stability, and vaporizer and spray fuel injection. Main reference for the combustor model. |

## 2. Micro gas turbines and micro turbojets

| Ref | Findings (from the abstract unless noted) |
|---|---|
| [van den Hout & Koullen 1996](https://doi.org/10.1115/96-gt-456) | Design and operation of a very small turbojet for model aircraft and drones, built around an automotive turbocharger rotor with a new single-stage diffuser and a 110 mm reverse-flow combustor. Design point at ISO: 40 N gross thrust, 0.150 kg/s, compressor pressure ratio 1.90, TIT 680 °C (953 K), 100 000 rpm, SFC 0.225 kg/(N·h) (62.5 mg/(N·s)). Engine is 110 mm diameter, 310 mm long, 2.2 kg. The authors name the combustor, bearing and balancing, and diffuser as the three main challenges. **Closest published analogue to this project in size and speed.** |
| [Rodgers 2003](https://doi.org/10.1115/GT2003-38027) | Review of how size and clearance gaps affect small gas turbine performance. Sets about 100 krpm and above as the "small" regime and notes that parasitic friction and component heat transfer become significant at the smallest sizes. Used for the size penalty on component efficiencies. |
| [Pampreen 1973](https://doi.org/10.1115/1.3445730) | Small axial and centrifugal compressors and fans. Gives correlations of efficiency against Reynolds number and clearance. Clearance effects dominate when designs are scaled down, and Reynolds effects dominate as density falls. The correlation constants were not accessed in this session. |
| [Epstein 2004](https://doi.org/10.1115/1.1739245) | Review of the MIT MEMS "microengine". Millimetre-scale centrifugal machines with pressure ratios of 2 to 4 and TIT of 1200–1600 K, giving projected performance on a par with 1940s gas turbines. Thermodynamics are unchanged with scale, but mechanics, manufacturing and heat transfer differ. Gives context for scaling trends below our size. |
| [Isomura et al. 2006](https://doi.org/10.1088/0960-1317/16/9/s13) | Experimental check that a 100 W class micro gas turbine with a 10 mm impeller is feasible. No abstract in Crossref, so only the title is used. This is a lower bound on scale, about ten times smaller than our engine. |
| [Badami, Nuccio & Signoretto 2013](https://doi.org/10.1016/j.enconman.2013.07.043) | Experimental and numerical analysis of a small-scale (model-aircraft class) turbojet. No abstract in Crossref. A potential validation dataset if the full text can be obtained. |
| [Badami et al. 2014](https://doi.org/10.1016/j.enconman.2014.03.026) | Performance of the same class of small turbojet on conventional and alternative fuels. No abstract in Crossref. |
| Schreckling 1994 (book) | *Gas Turbines for Model Aircraft*. Hobby design and build guide for a home-built engine. Not peer reviewed. Historical root of the KJ-66 and "JetCat" class of engines, but its numbers are not used for calibration. |

**Gap in this review.** No peer-reviewed paper with a full component-by-component dataset for a KJ-66
class engine was verified in this session. Badami et al. are the most promising, but there is no
abstract and the full text was not accessed. Kamps' *Model Jet Engines* (Traplet) was left out
because its edition and year could not be confirmed.

## 3. Centrifugal compressor design

| Ref | Contribution |
|---|---|
| [Wiesner 1967](https://doi.org/10.1115/1.3616734) | Review of slip-factor methods. Concludes that Busemann's 1929 result is still the most generally applicable, and gives a very simple empirical fit to it. The fit holds up to a limiting inlet-to-outlet radius ratio, with a correction beyond that limit. Checked against more than 60 impellers. **Used for the slip factor.** |
| [Stanitz 1952](https://doi.org/10.1115/1.4015817) | Relaxation solutions for impeller flow, studying flow rate, tip speed, blade number and blade curvature. Source of the Stanitz slip factor (textbook form) used as a cross-check on Wiesner. Published in Trans. ASME 74; Crossref lists it under J. Fluids Eng. |
| [Aungier 2000](https://doi.org/10.1115/1.800938) | *Centrifugal Compressors* (book). Full meanline design and analysis system with loss models for the impeller, vaned diffuser and volute. Reference for the meanline loss breakdown. |
| Japikse 1996 (book) | *Centrifugal Compressor Design and Performance*. Two-zone (jet-wake) impeller modelling and diffuser pressure-recovery data. Reference for vaned-diffuser recovery assumptions. |
| [Senoo & Ishida 1987](https://doi.org/10.1115/1.3262070) | Tip-clearance loss theory for unshrouded impellers, including how clearance changes slip. At equal exit clearance ratio, the efficiency drop is smaller for high-pressure-ratio stages than for low-pressure-ratio stages. Directly relevant because our low-PR (about 2 to 3) impeller is in the more sensitive group. |
| [Casey 1985](https://doi.org/10.1115/1.3239767) | Reynolds-number correction for centrifugal stage efficiency, based on friction losses. It depends on surface roughness, exit width ratio and work coefficient, and has one calibrated coefficient. **Used for the size and Reynolds penalty on compressor efficiency.** The exact equation is to be taken from the paper or from Dixon & Hall. |
| [Casey & Robinson 2013](https://doi.org/10.1115/1.4006590) | Algebraic performance-map method built on four parameters: flow coefficient, work coefficient, tip Mach number and efficiency. For turbochargers with vaneless diffusers it predicts efficiency and pressure ratio to within ±2%. The surge line is less certain. Candidate for the off-design compressor map. |
| [Ziegler, Gallus & Niehuis 2003](https://doi.org/10.1115/1.1516814) | Vaned-diffuser experiments varying the radial gap between impeller and vanes. A smaller gap usually gives higher diffuser pressure recovery and stage efficiency, while impeller efficiency barely changes. Used for choosing the diffuser leading-edge radius ratio. |
| [Verstraete et al. 2010](https://doi.org/10.1115/1.3144162) | Coupled aerodynamic and structural optimization of a small radial impeller for a micro gas turbine. Blade centrifugal stress can be reduced a lot with no loss in efficiency. Relevant to the aluminum-impeller stress limit. |

## 4. Axial turbine design and loss

| Ref | Contribution |
|---|---|
| [Smith 1965](https://doi.org/10.1017/S0001924000059108) | Rolls-Royce correlation of the efficiency of about 70 turbine stages against the velocity triangles, using flow coefficient φ = c_x/U and loading ψ = Δh₀/U². It predicts efficiency to better than ±2% within its scope (abstract). **Used for the turbine meanline efficiency.** In the textbook form the data are corrected to zero tip clearance and are for large, high-Reynolds-number turbines, so they are an upper bound for this engine. |
| Ainley & Mathieson 1951 (report) | ARC R&M 2974. Original profile, secondary and tip-clearance loss system at a reference diameter. No DOI. Cited through the two papers below. |
| [Dunham & Came 1970](https://doi.org/10.1115/1.3445349) | Review of Ainley-Mathieson against modern turbines, with improved secondary-loss and tip-clearance-loss formulas. They judge it still valuable for preliminary design. |
| [Kacker & Okapuu 1982](https://doi.org/10.1115/1.3227240) | Development of Ainley-Mathieson into a meanline loss system, tested against the Smith chart and 33 turbines. Predicts design-point efficiency within ±1.5% for conventional stage loadings. Option for a second-level turbine loss model. |
| [Denton 1993](https://doi.org/10.1115/1.2929299) | Physical origins of loss as entropy generation: boundary layers, trailing edges, tip leakage, endwalls, mixing and heat transfer. Background for why small-scale losses (thick trailing edges, large relative clearances, low Reynolds number) increase. |
| [Haas & Kofskey 1979](https://doi.org/10.1115/79-gt-42) | Experiments on tip clearance in a **12.77 cm tip-diameter** single-stage axial reaction turbine, at nearly our scale. A recessed casing does better than a shortened blade, and the best recessed-casing blade height puts the rotor tip at the stator tip diameter. The loss numbers are in the paper but not in the abstract. |
| Soderberg (via Dixon & Hall 2014) | Simple blade-row loss correlation in terms of deflection, aspect ratio and Reynolds number (textbook form). Used as a cross-check on the Smith-chart efficiency. The original Soderberg work is unpublished and is known only through textbooks. |

## 5. Combustion in small engines

| Ref | Contribution |
|---|---|
| [Lefebvre & Ballal 2010](https://doi.org/10.1201/9781420086058) | Combustion efficiency correlated with the θ loading parameter, reference-area sizing, and the design of vaporizer ("walking-stick") and spray injectors (textbook). **Main source for combustor sizing.** |
| [Lefebvre 1985](https://doi.org/10.1115/1.3239693) | Analysis of fuel-property data from eight production combustors (J79, F101, TF41, J85 and others). Combustion efficiency and lean blowout and light-off limits depend only slightly on fuel chemistry. They depend strongly on the physical properties that set atomization and evaporation. Supports modelling efficiency through θ and evaporation rather than through chemistry. |
| [Savary & Gresy 2022](https://doi.org/10.2514/6.2022-0363) | Removable additively manufactured combustor vaporizer technology. No abstract in Crossref, so only the title is used. Relevant to how vaporizer tubes are built and replaced. |

**Gap in this review.** No peer-reviewed measurement of combustion efficiency or residence time in a
model-scale (about 100 N) vaporizer combustor was verified in this session. Below its calibrated
range, the θ correlation is an **extrapolation** for this engine.

## 6. Materials

| Ref | Contribution |
|---|---|
| [Reed 2006](https://doi.org/10.1017/CBO9780511541285) | *The Superalloys* (book). Physical metallurgy, γ′ strengthening, creep and the processing of cast and wrought nickel superalloys, including the cast alloys of the IN 713 family. Reference for turbine-wheel and nozzle-guide-vane material choice. |
| [Pollock & Tin 2006](https://doi.org/10.2514/1.18239) | Review of nickel superalloy chemistry, microstructure and properties for turbine engines. No abstract in Crossref. General reference only. |
| [Larson & Miller 1952](https://doi.org/10.1115/1.4015909) | Time-temperature parameter for rupture and creep, applied to several different alloys. Shows how short tests can predict long-time properties. **Used for creep life.** Published in Trans. ASME 74; Crossref lists it under J. Fluids Eng. |
| [Brinkman, Booker & Ding 1991](https://doi.org/10.7449/1991/superalloys_1991_519_536) | Creep and creep-rupture behaviour of Alloy 718 (*Superalloys 718, 625 and Various Derivatives*). No abstract in Crossref. Candidate source for Inconel 718 Larson-Miller data (shaft and nut). |
| [Boyer 1996](https://doi.org/10.1016/0921-5093(96)10233-1) | Overview of titanium use in aerospace, including Ti-6Al-4V. No abstract in Crossref. Reference for a possible Ti-6Al-4V compressor wheel. |
| [Nový, Janeček & Král 2009](https://doi.org/10.1016/j.jallcom.2009.08.014) | Microstructure changes in aluminum alloy 2618 during ageing and creep. No abstract in Crossref. Supports the known concern that 2618 (the usual turbocharger-wheel alloy) overages and creeps at elevated temperature, which limits compressor exit temperature. |

**Gap in this review.** No verified source gives tabulated creep-rupture data for **Inconel 713C**,
the usual cast turbine-wheel alloy. Until a datasheet or paper is found, its Larson-Miller curve in
the model is a placeholder and must be flagged as such.

## 7. Rotordynamics and high-speed bearings

| Ref | Contribution |
|---|---|
| [Jeffcott 1919](https://doi.org/10.1080/14786440308635889) | Classic analysis of the lateral vibration of a loaded shaft near its whirling (critical) speed and the effect of unbalance. No abstract in Crossref. Basis of the single-mass (Jeffcott) rotor model used for first-critical-speed estimates. |
| [Vance, Zeidan & Murphy 2010](https://doi.org/10.1002/9780470903704) | *Machinery Vibration and Rotordynamics* (book). Critical speeds, unbalance response, bearing and support stiffness, and squeeze-film damping. Reference for the rotordynamics module. |
| [Buchner 1993](https://doi.org/10.1520/stp24829s) | Spindle ball bearings with silicon nitride (ceramic) balls compared with steel at very high speed. The lower density reduces ball centrifugal force. The higher modulus raises contact stiffness and Hertzian pressure. Hardness of about DPH 1600 cuts wear when lubrication is briefly poor. Test rigs showed better temperature and wear behaviour. Supports the choice of hybrid ceramic bearings. |

## 8. How each source is used in this project

| Model module | Sources | What is taken from them |
|---|---|---|
| Cycle model (design point and off-design) | saravanamuttoo2017, mattingly2006, hill1992, walsh2004 | Brayton cycle with component efficiencies and pressure losses, nozzle thrust, TSFC, and compressor-turbine matching. Benchmark: vandenhout1996 (40 N, PR 1.9, 0.15 kg/s, 100 krpm, TIT 953 K). |
| Compressor meanline | wiesner1967, stanitz1952, dixon2014, aungier2000, japikse1996, casey1985, pampreen1973, rodgers2003, senoo1987, ziegler2003, casey2013 | Slip factor (Wiesner, Stanitz as check), loss breakdown, Reynolds and size penalty on efficiency, clearance penalty, vaned-diffuser recovery and radial gap, off-design map. |
| Turbine meanline | smith1965, dixon2014 (Soderberg), kacker1982, dunham1970, ainley1951, denton1993, haas1979 | Choice of φ and ψ and efficiency from the Smith chart, Soderberg cross-check, and tip-clearance and small-scale penalties. |
| Combustor sizing | lefebvre2010, lefebvre1985, savary2022 | Reference area, θ loading parameter, combustion efficiency against θ, vaporizer tube layout, and pressure loss. |
| Material creep | larson1952, reed2006, pollock2006, brinkman1991, boyer1996, novy2009, verstraete2010 | Larson-Miller life for the turbine wheel and NGV (IN 713C, placeholder data) and shaft (IN 718), plus temperature and stress limits for the 2618 or Ti-6Al-4V compressor wheel. |
| Rotordynamics | jeffcott1919, vance2010, buchner1993 | First bending critical from a Jeffcott and Rayleigh model, separation margin from operating speed, and support and bearing stiffness for hybrid ceramic bearings. |
| Scaling context | epstein2004, isomura2006, rodgers2003, badami2013, badami2014, schreckling1994 | Which way efficiencies move with size. Possible validation data (Badami, if the full text is obtained). |

## 9. Key correlations for the model

These are *textbook forms* unless marked otherwise. Check the constants against the cited source
before freezing them.

| Correlation | Form | Key |
|---|---|---|
| Wiesner slip factor | σ = 1 − √(cos β₂ᵦ) / Z^0.7, with β₂ᵦ the exit blade angle from radial and Z the blade number. Valid for r₁/r₂ ≤ ε_lim = exp(−8.16 cos β₂ᵦ / Z). Beyond that, σ is multiplied by [1 − ((r₁/r₂ − ε_lim)/(1 − ε_lim))³]. | wiesner1967, dixon2014 |
| Stanitz slip factor (check) | σ = 1 − 0.63π / Z for radial blades | stanitz1952, dixon2014 |
| Smith chart | ψ = Δh₀/U², φ = c_x/U. The highest efficiencies (above 90%, corrected to zero clearance) lie roughly in φ ≈ 0.5–0.9 and ψ ≈ 1–2.5. Accuracy is ±2% within its scope (abstract). Apply a size and clearance debit. | smith1965, dixon2014 |
| Soderberg blade-row loss | ζ* = 0.04 + 0.06 (ε/100)², with ε the deflection in degrees, at Re = 10⁵ and H/b = 3, plus aspect-ratio and (10⁵/Re)^0.25 corrections | dixon2014 |
| Kacker-Okapuu accuracy | ±1.5% on design-point efficiency (abstract) | kacker1982 |
| Reynolds correction (compressor) | A friction-based correction in terms of roughness, b₂/D₂ and work coefficient, with one calibrated coefficient (abstract). The equation is not transcribed here. | casey1985 |
| Combustor loading | θ = P₃^1.75 A_ref D_ref^0.75 exp(T₃/b) / ṁ_A, with b ≈ 300 K near stoichiometric. η_c is correlated against θ. | lefebvre2010 |
| Larson-Miller | LMP = T (C + log₁₀ t_r), with T in K, t_r in h, and C ≈ 20 | larson1952 |
| Jeffcott critical speed | ω_c = √(k/m), where unbalance response peaks and the phase passes through 90° | jeffcott1919, vance2010 |
| Size benchmark | 110 mm engine: 40 N, 0.150 kg/s, PR 1.90, 953 K TIT, 100 krpm, 62.5 mg/(N·s) (abstract) | vandenhout1996 |
