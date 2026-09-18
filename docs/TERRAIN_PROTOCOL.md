# Development protocol before independent terrain evaluation

The current replay is exploratory. The following choices are declared before the
next parameter trials, all using **trial 0 only**:

1. Compare the existing 14 mm grid / 7 mm particles with a 10 mm grid / 5 mm particles
   at 1 ms. Report simulated-surface differences separately from physical target error.
2. At the coarse development discretization (14 mm / 7 mm, 2.5 ms), evaluate friction
   0.35 and 0.9 alongside the existing 0.6 result. Keep density 1,600 kg/m³, wall and
   tool friction 0.5, air drag 1.0, and the same prescribed motion and plane boundaries.
3. Use full-grid height MAE as the declared development score. Preserve RMSE, empty
   cells, full error maps, failures, and the unchanged-bed baseline. Do not translate
   or rotate predicted surfaces, change amplitude, or fit per-trial offsets.
4. Treat this small parameter sweep as sensitivity/development evidence, not proof
   of a unique material coefficient or a completed calibration procedure.
5. Do not choose a final parameter set or run independent trial 1 until numerical
   sensitivity and useful acceptance criteria are explicitly resolved. No threshold
   is inferred merely from the best observed score.

This protocol deliberately does not promise a physical pass. The permitted material
envelope and uncertainty remain limited by the source-data admission audit.
