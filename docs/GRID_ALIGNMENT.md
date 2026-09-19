# Grid alignment controls

The initial sparse-grid comparison is not a matched-grid equivalence test. Source
inspection of the pinned Newton 1.6.0 and Warp 1.17.0 implementations identifies
a difference in where their cells lie relative to the physical geometry.

For voxel width `h`, Newton's fixed grid rounds its bounds to integer multiples
of `h`. Warp's `Grid3D.cell_position` places cell boundaries at those coordinates.
`Nanogrid.cell_position` instead subtracts one half from local cell coordinates
before applying the volume transform. The volume allocator used by Newton defaults
to zero translation. Sparse voxel centers therefore lie at integer multiples of
`h`, with boundaries half a voxel away from the fixed-grid boundaries.

At `h = 0.04 m`, this is a 20 mm offset in each axis. A force discrepancy between
these grids cannot yet be attributed exclusively to storage, topology or warm starts.

## Controlled translation

The diagnostic accepts `--world-offset x y z`. This translates the entire physical
fixture: initial particles, the box, its prescribed trajectory and ground height.
Velocities, gravity, masses, material parameters, relative penetration and elapsed
time are unchanged. The offset is recorded in the result; particle coordinates and
the recorded tool height remain in the translated world frame.

For the sparse grid, translating the physical fixture by `(h/2, h/2, h/2)` makes
its position relative to cell boundaries match the untranslated fixed-grid fixture,
up to floating-point rounding. In one dimension, subtracting the translated physical
origin from a sparse boundary gives `(i - 1/2)h - h/2 = (i - 1)h`, the same set of
relative boundaries as the fixed grid. This is a test setup, not evidence that the
two solvers will produce equivalent results.

## Rebuild and capacity controls

`--rebuildable-sparse` explicitly requires `--grid-type sparse` and sets grid
padding to zero. Construction must confirm that Newton activated its rebuildable
path. The diagnostic records the resolved stress warm-start mode and calls
`check_sparse_grid_rebuild_status()` after every step. Capacity or topology failure
must produce a failed run, not a silently accepted force curve.

The default fixed-grid behavior is unchanged. Grid-backed warm starts are rejected
for the rebuildable sparse path, as required by the pinned solver. `auto` and
`particles` are distinct requested values even when they resolve to the same mode.

## Completed rebuild control

The unshifted rebuildable control completed at 5 ms with 262,144 reserved active
cells, particle-backed stress warm starts, and a 20,000-iteration cap. Every one
of its 240 steps met both 1e-5 residual tolerances and passed the sparse capacity
check. Impulse was 62.187 N s and peak 20 ms mean force was 645.36 N. Evidence is
in `evidence/contact-rebuild-control/`.

The prior non-rebuildable sparse control produced 62.080 N s and 643.20 N. These
are close for this execution, but neither result is yet an equivalence certificate.
Both differ substantially from the untranslated fixed grid's 66.207 N s and
815.07 N, which motivates the alignment control.

Diagnostic runs can now print progress with `--progress-every N`. A progress line
is explicitly nonterminal, even when its completed-step count reaches the target;
the final residual checks and result record must still be inspected.

No grid equivalence, spatial convergence or physical qualification is claimed here.

## Matched translation comparison

The translated and untranslated rebuildable cases were repeated with the same
16,384-cell capacity and 50,000-iteration cap. All steps meet the unchanged 1e-5
inner residual tolerance, all capacity checks pass, and both source identities
remain unchanged during execution.

| Configuration | Impulse (N s) | Peak 20 ms mean (N) |
|---|---:|---:|
| Fixed reference, original coordinates | 66.207 | 815.07 |
| Rebuildable sparse, original coordinates | 62.187 | 645.36 |
| Rebuildable sparse, translated by 20 mm in every axis | 66.417 | 803.13 |

The translated case differs from the fixed reference by 0.32% in impulse and
1.46% in averaged peak magnitude. After removing the known translation, mean and
maximum final particle-position differences are 0.12 mm and 0.99 mm respectively.
Grid alignment accounts for much of the previously observed discrepancy in this
fixture; remaining differences prevent an exact-equivalence claim.

The smaller-capacity untranslated case has identical recorded particle positions
and step impulses to the earlier 262,144-cell control. This checks that capacity
reduction did not alter this particular comparison; it is not a general claim
that arbitrary capacities are safe.

Raw records, settings, source hashes and comparisons are in
`evidence/contact-grid-alignment/`. The fixed reference is the independently
recorded case in `evidence/contact-inner-converged/`. A first translated attempt
with a 20,000-iteration cap missed tolerance at one step and remains local in
`runs/numerical-grid-alignment/runs/aligned-control/`; it is not used as the final
matched comparison.

The next refinement holds the relative cell alignment fixed while halving the
grid width, particle spacing and timestep. It retains inner residual and capacity
checks. A smaller cell width alone is not a physical-validation pass.
