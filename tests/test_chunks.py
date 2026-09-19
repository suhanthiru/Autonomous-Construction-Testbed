from dataclasses import replace

from test_sensors import raw

from excavation_sim.chunks import ChunkExecutor
from excavation_sim.core import ToolCommand


def test_interruption_discards_pending_chunk_and_replans():
    class Planner:
        calls = 0

        def reset(self, seed):
            self.calls = 0

        def plan(self, observation):
            self.calls += 1
            return [ToolCommand((self.calls, 0, 0))] * 3

    planner = Planner()
    executor = ChunkExecutor(planner, ToolCommand((0, 0, 0)))
    executor.reset(0)
    assert executor.act(raw(0)).velocity_m_s[0] == 1
    assert executor.act(replace(raw(1), sensor_valid=False)).velocity_m_s[0] == 0
    assert executor.events[-1]["discarded_actions"] == 2
    assert executor.act(raw(2)).velocity_m_s[0] == 2
