from dataclasses import replace

import numpy as np

from excavation_sim.core import Observation
from excavation_sim.inspection import InspectionRecorder


def test_display_sampling_does_not_copy_full_state_between_frames(tmp_path):
    class World:
        calls = 0

        def inspection_state(self):
            self.calls += 1
            return {"body_poses": np.array([[0, 0, 0, 0, 0, 0, 1]], dtype=np.float32),
                    "particles": np.array([[0.123456789, 0, 0]], dtype=np.float32)}

    world = World()
    recorder = InspectionRecorder(frame_interval_s=0.1)
    initial = Observation(0, 0.0, (0, 0, 0), (0, 0, 0), (0, 0, 0))
    for tick in range(11):
        recorder(world, replace(initial, tick=tick, time_s=tick * 0.02))
    assert world.calls == 3
    assert [f["observation"]["tick"] for f in recorder.frames] == [0, 5, 10]
    assert recorder.frames[0]["particles"][0][0] == 0.12346
    output = tmp_path / "inspection.html"
    recorder.write(output)
    assert "__EPISODE_DATA__" not in output.read_text(encoding="utf-8")
