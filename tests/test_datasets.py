import numpy as np
import pytest

from excavation_sim.datasets import read_triangle_obj, rheometer_volume_fraction, surface_height_map


def test_rheometer_units_sign_and_fixed_surface_offset(tmp_path):
    path = tmp_path / "volume.csv"
    path.write_text("0.009525,-1,,0.015875,-2\n")
    conditions = rheometer_volume_fraction(path)["conditions"]
    assert conditions[0]["depth_m"][0] == pytest.approx(0)
    assert conditions[1]["dimensionless_depth"][0] == pytest.approx(1)
    assert conditions[1]["resisting_force_n"] == [2]


def test_height_map_axis_and_outside_crop():
    points = np.array([[0.081, 0.087, 0.12], [0.32, 0.5, 100]])
    result = surface_height_map(points, 0)
    assert result[0, 1] == 0.12
    assert result.max() == 0.12


def test_obj_rejects_faces_outside_vertex_array(tmp_path):
    path = tmp_path / "bad.obj"
    path.write_text("v 0 0 0\nf 1 2 3\n")
    with pytest.raises(ValueError):
        read_triangle_obj(path)
