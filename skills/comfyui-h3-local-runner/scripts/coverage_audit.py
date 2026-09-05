#!/usr/bin/env python3
"""Audit exact screenplay dialogue coverage in storyboard and H3 prompt payloads."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LINE_RE = re.compile(r"^\s*([^：:\n]{1,24})[：:]\s*(.+?)\s*$")
TAG_RE = re.compile(r"<d>\[[^\]]+\]\s*(.*?)</d>", re.I | re.S)


def normalize(value: str) -> str:
    return re.sub(r"[\s。！？!?，,；;：“”‘’\"']", "", value)


def parse_script(path: Path):
    result = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        match = LINE_RE.match(line)
        if not match:
            continue
        speaker, text = match.group(1).strip(), match.group(2).strip()
        if speaker in {"周远", "赵凯", "林晚"}:
            result.append({"speaker": speaker, "text": text, "normalized": normalize(text),
                           "line": line_number})
    return result


def storyboard_dialogue(project: Path):
    data = json.loads((project / "storyboard.json").read_text(encoding="utf-8-sig"))
    result = []
    for segment in data.get("segments", []):
        for value in segment.get("dialogue", []) or []:
            match = LINE_RE.match(value)
            speaker = match.group(1).strip() if match else ""
            text = match.group(2).strip() if match else value.strip()
            result.append({"speaker": speaker, "text": text, "normalized": normalize(text),
                           "segment": int(segment["id"])})
    return result


def prompt_dialogue(project: Path):
    result = []
    for path in sorted((project / "prompts").glob("seg_*.txt")):
        match = re.search(r"(\d+)", path.stem)
        segment = int(match.group(1)) if match else None
        for payload in TAG_RE.findall(path.read_text(encoding="utf-8-sig")):
            result.append({"text": payload.strip(), "normalized": normalize(payload),
                           "segment": segment})
    return result


def missing_from(source, target):
    remaining = [item["normalized"] for item in target]
    missing = []
    for item in source:
        try:
            remaining.remove(item["normalized"])
        except ValueError:
            missing.append(item)
    return missing


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--script", required=True, type=Path)
    args = parser.parse_args()
    project, script = args.project.resolve(), args.script.resolve()
    source = parse_script(script)
    board = storyboard_dialogue(project)
    prompts = prompt_dialogue(project)
    missing_board = missing_from(source, board)
    missing_prompts = missing_from(source, prompts)
    total = len(source)
    report = {
        "schema": 1,
        "source_dialogue_count": total,
        "storyboard_dialogue_count": len(board),
        "prompt_dialogue_count": len(prompts),
        "storyboard_coverage": round((total - len(missing_board)) / total, 4) if total else 1.0,
        "prompt_coverage": round((total - len(missing_prompts)) / total, 4) if total else 1.0,
        "missing_from_storyboard": missing_board,
        "missing_from_prompts": missing_prompts,
        "passed": not missing_board and not missing_prompts,
    }
    output = project / "jobs" / "local-runner" / "coverage-report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    if not report["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
