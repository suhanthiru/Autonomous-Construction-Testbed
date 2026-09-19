"""Export one completed recording to portable checksummed transition shards."""

import argparse
from pathlib import Path

from excavation_sim.packed import export_episode

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("episode", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
index = export_episode(args.episode, args.output)
print(f"Exported {index['transitions']} transitions in {len(index['shards'])} shards")
