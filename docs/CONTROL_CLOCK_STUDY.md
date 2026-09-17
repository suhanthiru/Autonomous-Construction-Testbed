# Fixed-controller timestep study

## Question and protocol

Does contact-force sensitivity persist when controller timing stays fixed?

The driven fixture runs for 1.2 seconds, using a 5 ms controller period in every
case. Physics timesteps are 5, 2.5, and 1.25 ms; each retains four rigid substeps.
The controller samples velocity and updates actuator force only on integer-aligned
controller ticks. Invalid clock ratios raise an error instead of rounding silently.
The command reverses at 0.8 seconds in every case. Soil resolution, particle layout,
solver iterations, actuator gain, and force limit remain unchanged.

```sh
python scripts/check_soil_coupling.py --drive --control-dt 0.005 --dt 0.005 --steps 240 --output runs/fixed-5ms.json
python scripts/check_soil_coupling.py --drive --control-dt 0.005 --dt 0.0025 --steps 480 --output runs/fixed-2p5ms.json
python scripts/check_soil_coupling.py --drive --control-dt 0.005 --dt 0.00125 --steps 960 --output runs/fixed-1p25ms.json
python scripts/summarize_fixture.py runs/fixed-5ms.json runs/fixed-2p5ms.json runs/fixed-1p25ms.json
```

## Measurement definition

Raw peak force is still reported. A second metric integrates the vertical soil
impulse within nonoverlapping, time-zero-aligned 20 ms windows and divides by 20 ms.
This gives every run the same measurement duration. It is an explicitly averaged
measurement, not a replacement for the raw peak or a calibrated force sensor.
Incomplete windows are rejected so a terminal impulse cannot be silently discarded.

No acceptance tolerance was established from physical data. This study reports
sensitivity; it cannot certify physical accuracy. Rigid and soil integration steps
still change together, and a single deterministic particle layout does not establish
robustness across seeds or material conditions.
