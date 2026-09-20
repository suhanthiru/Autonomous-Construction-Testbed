# Prepared fine-grid iteration-cap check

The 10 mm grid, 5 mm particle-spacing fixture was repeated with 500,000 rather
than 200,000 inner iterations. Both records use the same source and all nine
recorded prepared-state fingerprints agree. The independent comparison verifies
that the iteration cap is the only changed MPM configuration field.

| Cap | Vertical impulse (N s) | Peak 20 ms mean (N) | Digging solver failures |
| --- | ---: | ---: | ---: |
| 200,000 | 50.3339768 | 510.946787 | 1 / 960 |
| 500,000 | 50.3319037 | 510.859870 | 1 / 960 |

The higher cap still fails at 0.76125 s: the reported infinity residual is
1.6369001e-5 against tolerance 1e-5, after 500,001 reported iterations.
Both preparation sequences pass their inner residual checks. The higher-cap
process exits with code 1, and its complete raw record is retained.

The response changes are small (-0.00412% impulse and -0.01701% peak), but the
residual gate remains failed. This result does not establish time or spatial
convergence. Further increases in the cap are not justified by this check alone.

Reproduce the audit with:

```powershell
.venv/Scripts/python.exe docs/evidence/contact-grid-inner-cap/reproduce.py
```

Raw compressed evidence, canonical checksums, comparison, and the original run
command are in `docs/evidence/contact-grid-inner-cap/`. Evidence integrity passes;
physical validation remains false.
