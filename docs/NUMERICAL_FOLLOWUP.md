# Coupling refinement follow-up

These checks use the existing 1.2-second force-limited vertical penetration fixture,
with a fixed 5 ms controller period, 40 mm grid, 20 mm particles, and a 60 N actuator
cap. MPM solves use 100 iterations and a 1e-5 tolerance. The tested physics steps are
5, 2.5 and 1.25 ms. These are additional diagnostics, not new acceptance thresholds.

| Transfer and relaxation | Physics dt ms | Peak 20 ms mean force N | Integrated vertical impulse N s |
|---|---:|---:|---:|
| Lagged, one iteration | 5 | 44.92 | 10.507 |
| Lagged, one iteration | 2.5 | 39.20 | 10.672 |
| Lagged, one iteration | 1.25 | 49.75 | 11.764 |
| Lagged, four iterations | 5 | 38.63 | 10.432 |
| Lagged, four iterations | 2.5 | 46.62 | 11.219 |
| Lagged, four iterations | 1.25 | 54.42 | 12.836 |
| Staggered, one iteration | 5 | 34.06 | 8.692 |
| Staggered, one iteration | 2.5 | 38.61 | 10.029 |
| Staggered, one iteration | 1.25 | 38.82 | 11.115 |

Additional proxy iterations do not resolve the observed sensitivity. Staggered
transfer makes the two finest averaged force peaks close, but integrated impulse
still differs by about 10.8%, and penetration depth still changes. A single apparently
stable metric is not sufficient to declare convergence. The default backend remains
lagged; no material coefficient was changed to hide a numerical discrepancy.

The matched one-iteration lagged control uses the same MPM iteration/tolerance settings
as the staggered check. Compare those rows when assessing transfer mode; the older
study also had different inner-solver settings. The four-iteration development study
records source-tree changes during execution. Its records retain individual source
identities; it is not presented as a frozen release comparison. The staggered study
has one shared source identity across all three records.

Raw records and summaries are in `evidence/coupling-refinement-four/`,
`evidence/coupling-staggered-control/`, and `evidence/coupling-matched-lagged/`.
Reproduce a control with:

```sh
python scripts/check_coupling_refinement.py --iterations 1 --mode lagged --output runs/lagged-control
python scripts/check_coupling_refinement.py --iterations 1 --mode staggered --output runs/staggered-control
```

The supported statement is that the configured discrete testbed executes the reported
tasks and exposes its measured sensitivity. These results do not establish physical
force accuracy, continuum convergence, or real-machine load limits. The force and
terrain convergence gates remain unresolved; physical calibration cannot replace them.

The [further refinement study](CONTACT_REFINEMENT.md) extends lagged coupling to
0.625 and 0.3125 ms and adds a tighter inner-solver control. It retains the failed
contact gate and documents which metrics begin to agree and which still differ.
