import hashlib
import zipfile

import pytest

from excavation_sim.intrusion_data import load_development_trial, parse_trial

RAW = b"scenario,speed\r\r\nleg,1\r\r\ntime,force\r\r\n0,-2\r\r\n0.1,3\r\r\n"


def test_raw_reader_preserves_sign_and_all_samples():
    trial = parse_trial(RAW)
    assert trial["metadata"] == {"scenario": "leg", "speed": "1"}
    assert trial["samples"].tolist() == [[0, -2], [0.1, 3]]
    assert trial["surface_alignment"] is None
    assert trial["excluded_samples"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        RAW.replace(b"0.1,3", b"0,3"),
        RAW.replace(b"0.1,3", b"0.1,nan"),
        RAW.replace(b"0.1,3", b"0.1,3,4"),
    ],
)
def test_invalid_trials_fail_closed(payload):
    with pytest.raises(ValueError):
        parse_trial(payload)


def test_partitions_and_checksums_are_enforced(tmp_path):
    path = tmp_path / "trials.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("trial.csv", RAW)
    record = {
        "archive": path.name,
        "member": "trial.csv",
        "partition": "holdout",
        "sha256": hashlib.sha256(RAW).hexdigest(),
    }
    manifest = {
        "trials": [record],
        "files": [{"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}],
    }
    with pytest.raises(ValueError, match="reserved"):
        load_development_trial(tmp_path, manifest, "trial.csv")
    record["partition"] = "calibration"
    assert load_development_trial(tmp_path, manifest, "trial.csv")["excluded_samples"] == 0
    record["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="trial checksum"):
        load_development_trial(tmp_path, manifest, "trial.csv")
    path.write_bytes(b"changed archive")
    with pytest.raises(ValueError, match="archive checksum"):
        load_development_trial(tmp_path, manifest, "trial.csv")
