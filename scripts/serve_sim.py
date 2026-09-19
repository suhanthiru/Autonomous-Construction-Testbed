"""Local live simulator inspection with serialized stepping and recorded resets."""

import argparse
import importlib.util
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

from excavation_sim.backends.newton_excavator import NewtonExcavatorWorld
from excavation_sim.backends.newton_tool import ToolWorldConfig
from excavation_sim.core import JointCommand
from excavation_sim.provenance import environment_info, source_identity
from excavation_sim.recording import EpisodeWriter
from excavation_sim.sensors import ObservedWorld, SensorConfig


class Session:
    def __init__(self, args):
        self.args = args
        args.output.mkdir(parents=True, exist_ok=False)
        self.config = ToolWorldConfig(**json.loads(args.world_config.read_text()))
        self.sensor_config = (
            SensorConfig(**json.loads(args.sensor_config.read_text()))
            if args.sensor_config
            else SensorConfig(surface_enabled=True, sample_every_actions=5)
        )
        self.world = ObservedWorld(NewtonExcavatorWorld(self.config), self.sensor_config)
        spec = importlib.util.spec_from_file_location("live_policy", args.policy)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.policy_kwargs = (
            json.loads(args.policy_kwargs.read_text()) if args.policy_kwargs else {}
        )
        self.policy = module.ExcavatorPolicy(**self.policy_kwargs)
        self.writer = None
        self.episode = -1
        self.reset(0)

    def reset(self, seed):
        if type(seed) is not int or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if self.writer:
            self.writer.close("interrupted", "user reset the simulation")
        self.episode += 1
        self.observation = self.world.reset(seed)
        self.policy.reset(seed)
        self.writer = EpisodeWriter(
            self.args.output / f"episode-{self.episode:04d}",
            {
                "schema_version": 1,
                "seed": seed,
                "backend": asdict(self.world.info),
                "clock": asdict(self.world.clock),
                "config": {
                    "world": asdict(self.config),
                    "sensors": asdict(self.sensor_config),
                    "policy_path": str(self.args.policy),
                    "policy_kwargs": self.policy_kwargs,
                },
                "source": source_identity(Path.cwd()),
                "environment": environment_info(),
                "mode": "live inspection; no physical validation claim",
            },
        )
        (self.writer.directory / "runtime-model.json").write_text(
            json.dumps(self.world.runtime_metadata(), indent=2)
        )
        return self.snapshot()

    def snapshot(self):
        state = self.world.inspection_state()
        return {
            "frame": {
                "observation": asdict(self.observation),
                "bodies": state["body_poses"].tolist(),
                "particles": state["particles"][::16].tolist(),
                "diagnostics": asdict(self.world.diagnostics()),
            },
            "shapes": state["shapes"],
            "episode": self.episode,
        }

    def step(self, commands):
        action = (
            self.policy.act(self.observation) if commands is None else JointCommand(tuple(commands))
        )
        try:
            after = self.world.step(action)
            diagnostics = self.world.diagnostics()
            self.writer.append(
                self.observation,
                action,
                after,
                diagnostics,
                raw_soil_force_n=self.world.evaluation_observation().soil_force_n,
            )
            if diagnostics.escaped_mass_kg > 0:
                raise RuntimeError("material left supported domain")
            self.observation = after
            return self.snapshot()
        except Exception as error:
            self.writer.close("failed", str(error))
            self.world.close()
            raise

    def close(self):
        if self.writer:
            self.writer.close("interrupted", "live session stopped")
        self.world.close()


def page(snapshot):
    import excavation_sim.inspection

    template = (
        Path(excavation_sim.inspection.__file__)
        .with_name("inspection.html")
        .read_text(encoding="utf-8")
    )
    data = {"frames": [snapshot["frame"]], "shapes": snapshot["shapes"], "particle_stride": 16}
    template = template.replace("__EPISODE_DATA__", json.dumps(data, allow_nan=False))
    template = template.replace("Excavation episode inspection", "Live excavator inspection")
    template = template.replace("Reset playback", "Reset simulation")
    template = template.replace(
        "Playback does not advance physics.",
        "Step advances physics; pause keeps the current state.",
    )
    script = (
        "<script>"
        + Path(excavation_sim.inspection.__file__).with_name("live.js").read_text(encoding="utf-8")
        + "</script>"
    )
    return template.replace("</html>", script + "</html>").encode()


def main(args):
    session = Session(args)

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, body, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                self.respond(200, page(session.snapshot()), "text/html; charset=utf-8")
            elif self.path == "/state":
                self.respond(200, json.dumps(session.snapshot(), allow_nan=False).encode())
            else:
                self.respond(404, b"{}")

        def do_POST(self):
            origin = self.headers.get("Origin")
            allowed = {f"http://127.0.0.1:{args.port}", f"http://localhost:{args.port}"}
            if origin and origin not in allowed:
                self.respond(403, b'{"error":"origin not allowed"}')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("invalid request size")
                body = json.loads(self.rfile.read(length))
                if self.path == "/shutdown":
                    self.respond(200, b'{"closed":true}')
                    Thread(target=self.server.shutdown, daemon=True).start()
                    return
                if self.path == "/step":
                    result = session.step(body.get("commands"))
                elif self.path == "/reset":
                    result = session.reset(body.get("seed", 0))
                else:
                    self.respond(404, b"{}")
                    return
                self.respond(200, json.dumps(result, allow_nan=False).encode())
            except Exception as error:
                self.respond(400, json.dumps({"error": str(error)}).encode())

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Live inspection: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--world-config", type=Path, default=Path("configs/machine-development.json")
    )
    parser.add_argument("--policy", type=Path, default=Path("experiments/excavator_edge_cut.py"))
    parser.add_argument("--policy-kwargs", type=Path, default=Path("configs/policy-repeat.json"))
    parser.add_argument("--sensor-config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8766)
    main(parser.parse_args())
