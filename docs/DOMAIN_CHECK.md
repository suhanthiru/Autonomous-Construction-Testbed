# Fixed-grid domain check

A fixed grid is allocated around the initial particles. Newton's `grid_padding`
counts cells. Keeping that count fixed while refining the voxel size shrinks the
physical domain. A preloaded bucket starting around z=0.4 m with 0.02 m cells and
10 padding cells did not have grid support down to the ground.

The freely rotating loaded-bucket fixture became nonfinite at tick 336 (0.84 s)
with a 0.2 m margin. With the same 0.02 m voxel size and active-cell capacity,
increasing the margin to 0.5 m let the three-second motion complete. The bucket
spilled its contents while rotating; zero final retained mass is not an error or a
successful carry. The constrained vertical-motion control carried 0.3808 kg of its
0.384 kg preload and reported approximately -3.767 N final soil reaction.

The configuration now expresses padding in metres, converting to a whole number
of cells. Particle escape diagnostics also use a conservative interior of that
support domain, intersected with the declared audit envelope. Changing resolution
therefore no longer silently shrinks the requested physical margin.

The finer articulated run also previously failed near 0.4 s. Its retry with the
larger physical margin completed 24 simulated seconds in 890.77 wall seconds,
with zero lifted or deposited mass. This resolves that observed numerical failure,
but the excavation task still failed. Source changed during this development run,
so it is not frozen benchmark evidence. Full numerical sensitivity,
capacity checks, and task-specific domain adequacy remain required.

Raw component reports are retained under `evidence/machine-development/`. This
correction changes the interpretation of the original free-bucket failure: it is
not sufficient evidence that free rotation or two-way coupling is intrinsically
unstable. It was a domain-sensitive configuration.
