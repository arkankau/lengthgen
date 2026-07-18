#!/usr/bin/env python3
"""Run the three preregistered reviewer-critical GPU studies with resume support."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


OUTPUT_FILES = {
    "qwen": "pretrained_causal_routing_results.json",
    "natural": "pretrained_natural_mcqa_results.json",
    "endogenous": "pretrained_endogenous_assignment_results.json",
}

DEFAULT_SEEDS = {
    "qwen": [1, 2, 3, 4, 5],
    "natural": [3, 4, 5],
    "endogenous": [0, 1, 2, 3, 4, 5],
}


def parse_seeds(value: str | None, phase: str) -> list[int]:
    if value is None:
        return DEFAULT_SEEDS[phase]
    return [int(item) for item in value.split(",") if item.strip()]


def command_for(phase: str, seed: int, repo: Path, outroot: Path) -> tuple[list[str], Path]:
    python = sys.executable
    if phase == "qwen":
        outdir = outroot / f"pretrained_causal_qwen_exact_s{seed}"
        command = [
            python, str(repo / "colab" / "pretrained_causal_routing.py"),
            "--model", "Qwen/Qwen2.5-1.5B",
            "--lengths", "5,20,80,160", "--selection-length", "5",
            "--n", "128", "--calibration-examples", "64", "--heads", "4",
            "--dtype", "bf16", "--format", "colon_newline", "--batch", "4",
            "--seed", str(seed), "--outdir", str(outdir),
        ]
    elif phase == "natural":
        outdir = outroot / "pretrained_natural_mcqa_full" / f"s{seed}"
        command = [
            python, str(repo / "colab" / "pretrained_natural_mcqa.py"),
            "--model", "Qwen/Qwen2.5-1.5B-Instruct",
            "--dataset", "rajpurkar/squad", "--split", "train",
            "--pilot", "64", "--calibration-examples", "64", "--n", "128",
            "--pool-multiplier", "16", "--generation-examples", "16",
            "--generation-tokens", "8", "--max-tokens", "384", "--heads", "4",
            "--batch", "4", "--eval-batch", "16", "--screening-batch", "16",
            "--dtype", "bf16", "--seed", str(seed), "--outdir", str(outdir),
        ]
    else:
        outdir = outroot / f"pretrained_endogenous_assignment_s{seed}"
        command = [
            python, str(repo / "colab" / "pretrained_endogenous_assignment.py"),
            "--model", "Qwen/Qwen2.5-1.5B", "--lengths", "20,80",
            "--bases", "128", "--variants", "8", "--minimum-source-gap", "0.01",
            "--calibration-length", "5", "--calibration-examples", "64",
            "--heads", "4", "--batch", "8", "--dtype", "bf16",
            "--seed", str(seed), "--outdir", str(outdir),
        ]
    return command, outdir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["qwen", "natural", "endogenous", "all"], default="all")
    parser.add_argument("--seeds", help="Comma-separated override, applied to every selected phase.")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--outroot", default="/content/drive/MyDrive/lengthgen_reviewer_critical")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    outroot = Path(os.path.expanduser(args.outroot))
    phases = ["qwen", "natural", "endogenous"] if args.phase == "all" else [args.phase]
    failures: list[tuple[str, int, int]] = []

    for phase in phases:
        for seed in parse_seeds(args.seeds, phase):
            command, outdir = command_for(phase, seed, repo, outroot)
            result_path = outdir / OUTPUT_FILES[phase]
            if result_path.exists() and not args.force:
                print(f"SKIP {phase} seed {seed}: {result_path} exists", flush=True)
                continue
            outdir.mkdir(parents=True, exist_ok=True)
            print("\n" + "=" * 96, flush=True)
            print(f"RUN {phase} seed {seed}", flush=True)
            print(" ".join(command), flush=True)
            completed = subprocess.run(command, cwd=repo, check=False)
            if completed.returncode:
                failures.append((phase, seed, completed.returncode))
                print(f"FAILED {phase} seed {seed}: exit {completed.returncode}", flush=True)

    if failures:
        detail = ", ".join(f"{phase}:s{seed}={code}" for phase, seed, code in failures)
        raise SystemExit(f"Suite completed with failures: {detail}")
    print("\nAll requested runs are complete.", flush=True)


if __name__ == "__main__":
    main()
