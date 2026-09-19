# Qualification for a named excavator and worksite

The requested qualification target is now a specific real excavator operating at a
specific worksite. The machine and site have not yet been identified. The current
procedural bench-scale articulation cannot stand in for that machine.

## Required target definition

Record machine make/model and configuration, bucket geometry and capacity, payload
range, joint travel, operational speeds, hydraulic/control modes and relevant sensor
configuration. Record site boundaries, soil layers, bulk density, particle-size
distribution, moisture, compaction/preparation, and buried-obstacle conditions.

The claim must name the tasks and outputs being predicted, such as bucket reaction
force, tracking, removed mass, deposited mass and final terrain. Accuracy thresholds
must be useful for those tasks and fixed before viewing held-out results. A match
to one force curve does not qualify all of these outputs.

## Measurement package

| Measurement | Required context |
|---|---|
| Joint/bucket trajectory | Timestamps, coordinate frames, calibration, sampling and synchronization uncertainty |
| Hydraulic pressures or measured forces | Sensor calibration, piston areas, linkage geometry, friction and pressure-to-force assumptions |
| Commands and control state | Operator/autonomy inputs, controller settings, saturation and hydraulic modes |
| Before/after terrain | Registered scans, survey datum, masks and per-point or surface uncertainty |
| Excavated and deposited mass | Independent weighing or justified volume/density measurement with uncertainty |
| Soil and preparation | Trial locations, sampling method, density/moisture, layering and preparation history |
| Trial identity | Machine configuration, site location, date, reset/preparation identity, failures and exclusions |

Provide raw records plus a data dictionary. Pressure alone is not bucket force;
planned commands alone are not measured motion; simulated mass accounting is not
an independent weighing measurement. Repeated samples within one trial are not
independent excavation trials.

## Staged comparison

1. **Machine without digging:** motion/actuator checks over the intended range,
   unloaded and with independently known loads. Identify delays, compliance,
   friction, saturation and sensor effects using calibration trials.
2. **Controlled interaction:** probing and single cuts with measured soil state,
   trajectory, reaction and surface change. Establish numerical convergence using
   the matched geometry and operating range before interpreting model error.
3. **Repeated excavation:** multiple cuts and transport/deposit cycles. Check
   independent mass balance, evolving terrain, drift and accumulated model error.
4. **Held-out worksite trials:** freeze model, parameters, preprocessing and
   acceptance criteria. Separate trials by preparation/location as appropriate,
   rather than randomly splitting nearby timestamps from the same dig.
5. **Qualification report:** report errors and uncertainty by output, failures,
   valid operating ranges, excluded conditions, dependency/source hashes and
   evidence hashes. A failed output remains failed even if another output passes.

Public intrusion datasets support component studies. They do not replace these
machine/site measurements. The current validation ledger remains unqualified;
no real-machine certificate can be issued from the available evidence.
