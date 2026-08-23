# Decision Log

> Continuously maintained. Every decision involving architecture/physics/contracts is recorded here.

| Decision Item | Current Value | Change Date | Change Reason |
|---------------|---------------|-------------|---------------|
| Device orientation | BL–RRAM–NMOS–SL; WL→Gate | S00 | Default tutorial baseline |
| V_RRAM sign | V(top_electrode) − V(bottom_electrode), top = BL side | S00 | Consistent with profile |
| Polarity profile | SET: V_RRAM > 0; RESET: V_RRAM < 0; LRS=1, HRS=0 | S00 | Bipolar teaching baseline |
| Fidelity level | N/A (S00 no model) | S00 | — |
| State equations | N/A (S00 no model) | S00 | — |
| Sense rule | N/A (S00 not implemented) | S00 | — |
| Array bias policy | N/A (S00 not implemented) | S00 | — |
| Tolerance | N/A (S00 not implemented) | S00 | — |
| Golden versions | N/A (S00 not implemented) | S00 | — |
| Known limitations | S00 contains no RRAM physics logic | S00 | Bootstrap phase |
