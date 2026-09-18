from dataclasses import replace

from excavation_sim.core import Observation
from excavation_sim.sensors import SensorConfig, SensorStream


def raw(tick):
    return Observation(tick, tick * 0.01, (float(tick), 0.0, 1.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))


def test_latency_never_exposes_future_sample_and_reports_capture_age():
    stream = SensorStream(SensorConfig(sample_every_actions=2, latency_actions=1), 2, 0.01)
    stream.reset(7)
    first = stream.sample(raw(0))
    assert not first.sensor_valid and first.tool_position_m == (0.0, 0.0, 0.0)
    second = stream.sample(raw(2))
    assert second.sensor_valid and second.sensor_capture_tick == 0 and second.sensor_age_s == 0.02
    third = stream.sample(raw(4))
    assert third.tool_position_m == raw(0).tool_position_m and third.sensor_age_s == 0.04
    fourth = stream.sample(raw(6))
    assert fourth.sensor_capture_tick == 4 and fourth.tool_position_m == raw(4).tool_position_m


def test_noise_reset_reproduces_and_channels_have_independent_streams():
    config = SensorConfig(position_noise_std_m=0.01, force_noise_std_n=0.1)
    a = SensorStream(config, 2, 0.01)
    b = SensorStream(replace(config, position_noise_std_m=10.0), 2, 0.01)
    a.reset(42)
    b.reset(42)
    first = a.sample(raw(0))
    other = b.sample(raw(0))
    assert first.soil_force_n == other.soil_force_n
    assert first.tool_position_m != other.tool_position_m
    a.reset(42)
    assert a.sample(raw(0)) == first
