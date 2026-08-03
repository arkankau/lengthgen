"""Verify integrity and anonymity of the supplementary reproduction package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.sha256"
REQUIRED = (
    "README.md",
    "ARTIFACT_INDEX.md",
    "DATA_DICTIONARY.md",
    "REPRODUCE.md",
    "requirements.txt",
    "colab",
    "scripts",
    "tests",
    "results/lengthgen",
)
TEXT_SUFFIXES = {".py", ".md", ".tex", ".txt", ".csv", ".json", ".yaml", ".yml", ".toml", ".sh"}
FORBIDDEN_DIRS = {".git", "__pycache__", ".pytest_cache"}
ARCHIVE_FORBIDDEN_SUFFIXES = {".pdf", ".aux", ".bbl", ".blg", ".log", ".err", ".out", ".toc"}
SENSITIVE_PATTERNS = {
    "local user path": re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+", re.IGNORECASE),
    "Hugging Face token": re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    "generic API secret": re.compile(
        r"\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*['\"][^'\"]{12,}",
        re.IGNORECASE,
    ),
}


def package_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and path != MANIFEST and not any(part in FORBIDDEN_DIRS for part in path.parts)
    )


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def manifest_rows() -> list[tuple[str, int, str]]:
    rows = []
    for path in package_files():
        rows.append((digest(path), path.stat().st_size, path.relative_to(ROOT).as_posix()))
    return rows


def write_manifest() -> None:
    lines = [f"{sha256}\t{size}\t{relative}" for sha256, size, relative in manifest_rows()]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_manifest(errors: list[str]) -> None:
    if not MANIFEST.exists():
        errors.append("missing MANIFEST.sha256")
        return
    expected = {}
    for line_number, line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            sha256, size, relative = line.split("\t", 2)
            expected[relative] = (sha256, int(size))
        except ValueError:
            errors.append(f"malformed manifest line {line_number}")
    actual = {relative: (sha256, size) for sha256, size, relative in manifest_rows()}
    if expected.keys() != actual.keys():
        errors.append("manifest path set differs from package contents")
    for relative in sorted(expected.keys() & actual.keys()):
        if expected[relative] != actual[relative]:
            errors.append(f"manifest mismatch: {relative}")


def verify_contents(errors: list[str]) -> None:
    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            errors.append(f"missing required asset: {relative}")
    for path in package_files():
        if any(part in FORBIDDEN_DIRS for part in path.relative_to(ROOT).parts):
            errors.append(f"forbidden generated directory: {path.relative_to(ROOT)}")
        if path.suffix.lower() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON: {path.relative_to(ROOT)} ({exc})")
        if path.suffix.lower() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in SENSITIVE_PATTERNS.items():
                if pattern.search(text):
                    errors.append(f"{label} found in {path.relative_to(ROOT)}")


def verify_archive(path: Path, errors: list[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            errors.append("archive contains duplicate paths")
        for name in names:
            parts = Path(name).parts
            if name.startswith(("/", "\\")) or ".." in parts:
                errors.append(f"unsafe archive path: {name}")
            if any(part in FORBIDDEN_DIRS for part in parts):
                errors.append(f"forbidden archive directory: {name}")
            if Path(name).suffix.lower() in ARCHIVE_FORBIDDEN_SUFFIXES:
                errors.append(f"forbidden archive build product: {name}")
        bad_member = archive.testzip()
        if bad_member:
            errors.append(f"archive CRC failure: {bad_member}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()

    if args.write_manifest:
        write_manifest()

    errors: list[str] = []
    verify_contents(errors)
    verify_manifest(errors)
    if args.archive:
        verify_archive(args.archive.resolve(), errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"verified {len(package_files())} files")
    if args.archive:
        print(f"verified archive {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
