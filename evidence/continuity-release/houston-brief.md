# Exercise: Ben Taub General Hospital
Region: Houston, Texas
Case: 41320fbe-f087-48d9-97aa-f1422765f13c
Evidence status: exercise
Source: Planning exercise created in LifelineTwin
Observed: 2026-10-29T21:56:00Z
Computed: 2026-10-29T21:56:53.342448+00:00
Input SHA-256: 78d12cf18a774b45d4f55cfa7d166784670a7ac9b414badb0994444feb38ee10

## Supported consequences
1 community reference points have longer routes; 0 lose access within the study graph.
Affected population: unavailable.

| Community | Baseline km | Scenario km | Alternative facility |
| --- | --- | --- | --- |
| Texas Medical Center | 0.541 | 0.541 | Houston Methodist Hospital |
| Central City | 1.966 | 2.978 | Houston Methodist Hospital |
| Southgate | 0.991 | 0.991 | Houston Methodist Hospital |

## Alternatives for review
- Restore availability of Ben Taub General Hospital: 0 reference points reconnected; 1 shorter routes; 1012.3 metres mean reduction among improved connected routes; 1012.3 summed reference-point metres saved. Requires operator verification of staffing, service capability, and feasibility.
- Explore a temporary service point at Southgate: 0 reference points reconnected; 1 shorter routes; 991.2 metres mean reduction among improved connected routes; 991.2 summed reference-point metres saved. Location-only access proxy; no hospital-equivalent service, capacity, land access, staffing, or deployment feasibility is established.

## Limits and verification tasks
- Community reference points represent locations, not every resident or a population-weighted catchment.
- Population impact is unavailable; no affected-person count is inferred from reference points.
- Only the explicitly documented emergency-service subset is compared; operator websites document services, not current availability, capacity or suitability for a particular patient.
- Distances exclude travel-time, traffic, and snap offsets; hospitals and roads outside the bounded snapshot are excluded.
- The observation time records the case source; the calculation uses the downloaded snapshot and does not reconstruct historical conditions.
- Live weather warnings do not automatically close roads. Facility outages and road restrictions are explicit case inputs.
- Interventions are independently modeled comparisons, not operational instructions.

## Documented service scope
- Ben Taub General Hospital: https://www.harrishealth.org/locations-hh/Pages/ben-taub.aspx (reviewed 2026-10-29; live availability unverified).
- Houston Methodist Hospital: https://www.houstonmethodist.org/locations/texas-medical-center/emergency-department/ (reviewed 2026-10-29; live availability unverified).
