from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PromptCase:
    suite: str
    prompt: str
    label: str
    id: str = ""


def load_prompt_file(path: str | Path) -> list[PromptCase]:
    cases: list[PromptCase] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            cases.append(
                PromptCase(
                    id=str(row.get("id", f"{Path(path).stem}-{line_no}")),
                    suite=str(row["suite"]),
                    prompt=str(row["prompt"]),
                    label=str(row.get("label", row["suite"])),
                )
            )
    return cases


def load_prompt_dir(path: str | Path = "prompts") -> list[PromptCase]:
    root = Path(path)
    cases: list[PromptCase] = []
    for file in sorted(root.glob("*.jsonl")):
        cases.extend(load_prompt_file(file))
    return cases
