"""Report and merge sharded length-generalization confirmation results."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def record_key(record):
    cfg = record["cfg"]
    return cfg["task"], cfg["pe"], int(cfg["seed"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="results/lengthgen/full_grid")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument(
        "--output", default="results/lengthgen/paired_head_count_full_grid.json"
    )
    args = parser.parse_args()
    root = Path(args.root)
    records = {}
    for path in sorted(root.glob("*/paired_head_count_results.json")):
        for record in json.loads(path.read_text()):
            key = record_key(record)
            if key in records:
                raise SystemExit(f"duplicate result for {key}: {path}")
            records[key] = record

    expected = {
        (task, pe, seed)
        for task in ("argmax", "flagret")
        for pe in ("nope", "rope")
        for seed in range(4)
    }
    print(f"completed={len(records)}/16 checkpoints={len(list((root.parent / 'checkpoints').glob('*.pt')))}")
    for shard in sorted(path for path in root.iterdir() if path.is_dir()):
        log = shard / "run.log"
        lines = [line for line in log.read_text().splitlines() if line.strip()] if log.exists() else []
        print(f"{shard.name}: {lines[-1] if lines else 'not started'}")
    missing = sorted(expected - set(records))
    if missing:
        print("missing=" + ",".join(f"{task}/{pe}/s{seed}" for task, pe, seed in missing))

    if args.merge:
        if missing:
            raise SystemExit("refusing to merge an incomplete grid")
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        ordered = [records[key] for key in sorted(records)]
        temporary.write_text(json.dumps(ordered, indent=2))
        os.replace(temporary, output)
        print(f"merged={output}")


if __name__ == "__main__":
    main()
