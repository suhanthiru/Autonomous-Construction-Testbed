# Ideal overhead terrain sensor

Enable `surface_enabled` in a sensor configuration, for example:

```sh
python scripts/run_tool_episode.py --machine --sensor-config configs/sensors-surface.json --policy experiments/excavator_hold.py --policy-class HoldPolicy --actions 5 --output runs/surface-check
python scripts/check_surface_sensor.py --output runs/surface-occlusion-check
```

The observation's optional `surface` packet is a 32 by 32 grid with 0.025 m cells,
world XY origin (-0.4, -0.4), and world Z heights in metres. Arrays are flattened
row-major: index = y * width + x. For each column, the GPU reduces particle-center
heights to the largest Z. Empty columns are unknown. Ground height is not invented
for empty columns. Only the reduced grid crosses to the CPU; full particle positions
are not copied for this sensor.

A conservative visibility mask removes an entire cell when any rigid box's world
axis-aligned bounding box overlaps that cell above its surface. This intentionally
over-occludes rotated boxes and does not resolve gaps inside a bucket. Unsupported
shape types fail explicitly. Every invalid cell has height zero and visibility false;
zero height alone must not be interpreted as measured ground.

This is an ideal column-height observation, not a camera ray tracer or calibrated
depth sensor. It uses particle centers rather than a reconstructed continuous soil
surface. Surface height noise is not implemented. Position, velocity, force, and
joint noise remain separately configurable. Capture frequency, delivery latency,
validity and age apply to the whole observation packet, including the surface.
The first latency window contains no surface packet.

The GPU component fixture checks occlusion, invariance to changes in buried points,
and reveal after moving the covering body. A five-action machine episode exercises
capture, delay, recording and typed loading. CPU tests reject hidden nonzero samples
and verify that delayed packets cannot expose the next capture. These are sensor
implementation checks, not evidence of real-world sensing accuracy.
