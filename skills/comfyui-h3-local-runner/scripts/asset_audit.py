#!/usr/bin/env python3
"""Preflight reference assets for a compiled MiniMax H3 Director spec."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _collage_seams(path: Path):
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError as exc:
        raise RuntimeError("asset audit requires Pillow") from exc

    with Image.open(path) as source:
        image = source.convert("RGB")
        image.thumbnail((640, 640))
        width, height = image.size
        if width < 64 or height < 64:
            return []

        seams = []
        # A montage separator changes most pixels across one internal full-span
        # boundary. Ordinary doors and wall edges rarely span 80% of the frame.
        for axis, limit, other in (("vertical", width, height), ("horizontal", height, width)):
            candidates = []
            start, end = int(limit * 0.18), int(limit * 0.82)
            for pos in range(start, end):
                if axis == "vertical":
                    a = image.crop((pos - 1, 0, pos, height))
                    b = image.crop((pos, 0, pos + 1, height))
                else:
                    a = image.crop((0, pos - 1, width, pos))
                    b = image.crop((0, pos, width, pos + 1))
                diff = ImageChops.difference(a, b).convert("L")
                stat = ImageStat.Stat(diff)
                mean = stat.mean[0]
                changed = sum(1 for value in diff.getdata() if value >= 28) / other
                if mean >= 24 and changed >= 0.72:
                    candidates.append((pos, round(mean, 1), round(changed, 3)))
            if candidates:
                # Collapse adjacent separator pixels into one strongest boundary.
                best = max(candidates, key=lambda item: item[1])
                seams.append({"axis": axis, "position": best[0], "mean_delta": best[1],
                              "changed_fraction": best[2]})
        return seams


def audit_director_spec(spec_path):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    timeline = spec.get("director_inputs", {}).get("timeline_data", {})
    subjects = {item.get("shortName"): item for item in timeline.get("subjects", [])}
    errors, warnings, assets = [], [], []
    scene_count = 0

    for reference in spec.get("references", []):
        name = reference.get("shortName")
        path = Path(reference.get("local_path", "")).expanduser().resolve()
        subject = subjects.get(name, {})
        kind = subject.get("kind", "unknown")
        record = {"shortName": name, "kind": kind, "path": str(path), "exists": path.is_file()}
        if not path.is_file():
            errors.append(f"missing reference: {name} -> {path}")
            assets.append(record)
            continue
        if kind == "scene":
            scene_count += 1
            seams = _collage_seams(path)
            record["suspected_collage_seams"] = seams
            if len({item["axis"] for item in seams}) >= 2:
                errors.append(f"scene reference appears to be a multi-panel collage: {name}")
            elif seams:
                warnings.append(f"scene reference has a possible full-span separator: {name}")
        assets.append(record)

    if scene_count > 1:
        errors.append(f"beat binds {scene_count} scene references; use one single-space scene key")
    if scene_count == 0:
        warnings.append("beat has no scene reference; spatial continuity is prompt-only")

    return {
        "schema": 1,
        "segment_id": spec.get("segment_id"),
        "passed": not errors,
        "assets": assets,
        "warnings": warnings,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--director-spec", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = audit_director_spec(args.director_spec)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, separators=(",", ":")))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
