from dataclasses import asdict, replace

import pytest
from test_sensors import raw

from excavation_sim.episodes import observation_from_dict
from excavation_sim.sensors import SensorConfig, SensorStream
from excavation_sim.surface import SurfacePacket


def test_masked_values_cannot_leak_through_surface_packet():
    with pytest.raises(ValueError, match="masked"):
        SurfacePacket((0, 0), 0.1, 1, 1, (0.2,), (False,))
    packet = SurfacePacket((0, 0), 0.1, 2, 1, (0.2, 0.0), (True, False))
    observation = replace(raw(0), surface=packet)
    assert observation_from_dict(asdict(observation)) == observation


def test_surface_obeys_latency_and_does_not_leak_initial_capture():
    packet = SurfacePacket((0, 0), 0.1, 1, 1, (0.2,), (True,))
    stream = SensorStream(SensorConfig(surface_enabled=True, latency_actions=1), 2, 0.01)
    stream.reset(0)
    assert stream.sample(replace(raw(0), surface=packet)).surface is None
    next_packet = replace(packet, heights_m=(0.5,))
    delivered = stream.sample(replace(raw(2), surface=next_packet))
    assert delivered.surface == packet
    assert delivered.sensor_capture_tick == 0
