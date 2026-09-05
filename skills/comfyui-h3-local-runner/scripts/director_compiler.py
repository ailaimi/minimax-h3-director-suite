#!/usr/bin/env python3
"""Compile H3 six-section prompts into compact MiniMaxH3DirectorCS segment specs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SECTIONS = ("subject_definitions", "summary", "retention_analysis", "detailed_description",
            "overall_soundscape", "non_diegetic_music")
HEADER_RE = re.compile(r"(?m)^(" + "|".join(SECTIONS) + r"): *$")
SHOT_RE = re.compile(r"\[Shot\s+(\d+)\](?:\s+At\s+(\d{2}):(\d{2})(?:\.(\d{3}))?,?)?", re.I)
SHOT_KIND_RE = re.compile(r"^\{(establish|dialogue|reaction|insert|action|mixed)\}\s*", re.I)
SUBJECT_RE = re.compile(r"(?m)^<Subject\s+(\d+)>\s+(.+)$")
RETENTION_RE = re.compile(r"(?m)^<Subject\s+(\d+)>[^:]*:\s*(fully_preserved|partially_preserved|attribute_transfer|weak_reference)\s*-\s*(.+)$")
DIALOGUE_TAG_RE = re.compile(r"<d>\[([^\]]+)\]\s*(.*?)</d>", re.I | re.S)
SPEAKER_PREFIX_RE = re.compile(r"^[\w\u3400-\u9fff ]{1,24}[：:]")

REFERENCE_ROLES = {
    "identity_subject": ("Subject", "person"),
    "location_subject": ("Subject", "scene"),
    "prop_subject": ("Subject", "prop"),
    "composition_picture": ("Picture", "composition"),
    "motion_video": ("Video", "motion"),
    "audio_reference": ("Audio", "audio"),
}
RUNTIME_REFERENCE_ROLES = {
    "identity_subject", "location_subject", "prop_subject", "composition_picture"
}
REFERENCE_LABEL_RE = re.compile(r"^(Subject|Picture|Video|Audio)\s+(\d+)$", re.I)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_sections(text):
    matches = list(HEADER_RE.finditer(text))
    found = [match.group(1) for match in matches]
    if found != list(SECTIONS):
        raise ValueError("six prompt sections are missing or out of order")
    result = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1)] = text[match.end():end].strip()
    constraints = ""
    music = result["non_diegetic_music"]
    constraint_match = re.search(r"(?im)^constraints:\s*(.*)$", music)
    if constraint_match:
        constraints = constraint_match.group(1).strip()
        result["non_diegetic_music"] = music[:constraint_match.start()].strip()
    else:
        any_constraint = re.search(r"(?im)^constraints:\s*(.*)$", text)
        if any_constraint:
            constraints = any_constraint.group(1).strip()
    result["constraints"] = constraints
    return result


def seconds(match):
    if match.group(2) is None:
        return 0.0
    return int(match.group(2)) * 60 + int(match.group(3)) + int(match.group(4) or 0) / 1000.0


def parse_shots(detail, duration, fps):
    matches = list(SHOT_RE.finditer(detail))
    if not matches:
        raise ValueError("detailed_description has no [Shot N] markers")
    numbers = [int(match.group(1)) for match in matches]
    if numbers != list(range(1, len(matches) + 1)):
        raise ValueError("shot numbers are not continuous from 1")
    starts = [seconds(match) for match in matches]
    if starts[0] != 0 or any(b <= a for a, b in zip(starts, starts[1:])) or starts[-1] >= duration:
        raise ValueError("shot timestamps are invalid or non-increasing")
    preamble = detail[:matches[0].start()].strip()
    result = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(detail)
        prompt = detail[match.end():end].strip().lstrip(",").strip()
        kind_match = SHOT_KIND_RE.match(prompt)
        kind = kind_match.group(1).lower() if kind_match else None
        if kind_match:
            prompt = prompt[kind_match.end():].strip()
        start_frame = int(round(starts[index] * fps))
        end_second = starts[index + 1] if index + 1 < len(starts) else duration
        end_frame = int(round(end_second * fps))
        if not prompt or end_frame <= start_frame:
            raise ValueError(f"shot {index + 1} has empty prompt or duration")
        result.append({"id": f"seg{index}", "start": start_frame, "length": end_frame - start_frame,
                       "prompt": prompt, "type": "text", "isEndFrame": False,
                       "directorKind": kind})
    stated = []
    for shot in result:
        range_match = re.search(r"(\d+(?:\.\d+)?)[-–](\d+(?:\.\d+)?)秒", shot["prompt"])
        stated.append((float(range_match.group(1)), float(range_match.group(2))) if range_match else None)
    if all(stated) and abs(stated[0][0]) < 0.01 \
            and all(abs(stated[i][1] - stated[i + 1][0]) < 0.01 for i in range(len(stated) - 1)):
        for index, (shot, (stated_start, _)) in enumerate(zip(result, stated)):
            stated_end = stated[index + 1][0] if index + 1 < len(stated) else duration
            shot["start"] = int(round(stated_start * fps))
            shot["length"] = int(round((stated_end - stated_start) * fps))
    if sum(item["length"] for item in result) != int(round(duration * fps)):
        raise ValueError("shot frame lengths do not equal segment duration")
    return preamble, result


SHOT_DURATION_RULES = {
    "dialogue": (2.0, 4.0),
    "mixed": (1.5, 3.0),
    "action": (0.4, 1.5),
    "establish": (2.0, 4.0),
    "insert": (0.5, 2.0),
    "reaction": (1.0, 2.0),
}


def validate_director_density(shots, duration, fps):
    """Validate authored shot timing without imposing an arbitrary cut count."""
    errors = []
    for index, shot in enumerate(shots, 1):
        kind = shot.get("directorKind")
        seconds_long = shot["length"] / fps
        if kind is None:
            errors.append(f"shot {index} has no director kind tag")
            continue
        low, high = SHOT_DURATION_RULES[kind]
        if seconds_long < low - 0.02 or seconds_long > high + 0.02:
            errors.append(
                f"shot {index} ({kind}) is {seconds_long:g}s; allowed range is {low:g}-{high:g}s"
            )
    if errors:
        raise ValueError("director density validation failed: " + "; ".join(errors))


def required_text(value, field, errors):
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} must be a non-empty string")


def validate_creative_intent(segment, shots, strict):
    """Validate story-state change, information-bearing cuts, and continuity handoff."""
    creative = segment.get("creative_intent")
    if not isinstance(creative, dict):
        if strict:
            raise ValueError("director schema v2 requires creative_intent")
        return None, ["creative intent is not structured; story meaning remains human-verified"]
    errors = []
    for field in ("state_before", "trigger", "state_after", "audience_takeaway"):
        required_text(creative.get(field), f"creative_intent.{field}", errors)
    intents = creative.get("shot_intents")
    if not isinstance(intents, list) or len(intents) != len(shots):
        errors.append(f"creative_intent.shot_intents must contain exactly {len(shots)} items")
        intents = []
    for index, item in enumerate(intents, 1):
        if not isinstance(item, dict):
            errors.append(f"shot_intents[{index}] must be an object")
            continue
        required_text(item.get("new_information"), f"shot_intents[{index}].new_information", errors)
        required_text(item.get("narrative_subject"), f"shot_intents[{index}].narrative_subject", errors)
    handoff = creative.get("continuity_handoff")
    if not isinstance(handoff, dict):
        errors.append("creative_intent.continuity_handoff must be an object")
    else:
        for field in ("positions", "emotion", "props", "audio"):
            required_text(handoff.get(field), f"continuity_handoff.{field}", errors)
    if segment.get("dialogue") and intents and not any(
            bool(item.get("contains_reaction")) for item in intents if isinstance(item, dict)):
        errors.append("dialogue beat has no shot_intent with contains_reaction=true")
    if errors:
        raise ValueError("creative intent validation failed: " + "; ".join(errors))
    return creative, []


def infer_legacy_role(path):
    stem = path.stem.lower()
    if any(x in stem for x in ("lobby", "room", "corridor", "hall", "scene", "location", "door")):
        return "location_subject"
    return "identity_subject"


def resolve_reference_assets(project, segment, strict):
    """Resolve explicit H3 reference jobs; legacy refs remain supported with warnings."""
    declared = segment.get("reference_assets")
    warnings = []
    if declared is None:
        refs = [(project / relative).resolve() for relative in segment.get("refs", [])]
        assets = [{"path": path, "role": infer_legacy_role(path),
                   "label": f"Subject {index}"} for index, path in enumerate(refs, 1)]
        if refs:
            warnings.append("reference roles were inferred from legacy refs; migrate to reference_assets")
        if strict:
            raise ValueError("director schema v2 requires reference_assets with explicit role and label")
        return assets, warnings
    if not isinstance(declared, list):
        raise ValueError("reference_assets must be a list")
    assets, errors, seen_labels, seen_paths = [], [], set(), set()
    for index, item in enumerate(declared, 1):
        if not isinstance(item, dict):
            errors.append(f"reference_assets[{index}] must be an object")
            continue
        role, relative, label = item.get("role"), item.get("path"), item.get("label")
        if role not in REFERENCE_ROLES:
            errors.append(f"reference_assets[{index}].role is unsupported: {role}")
            continue
        if role not in RUNTIME_REFERENCE_ROLES:
            errors.append(f"reference role {role} is defined but not yet supported by the local runner")
        if not isinstance(relative, str) or not relative.strip():
            errors.append(f"reference_assets[{index}].path is required")
            continue
        match = REFERENCE_LABEL_RE.match(str(label or ""))
        expected_label = REFERENCE_ROLES[role][0]
        if not match or match.group(1).lower() != expected_label.lower():
            errors.append(f"reference_assets[{index}].label must be '{expected_label} N' for role {role}")
            continue
        normalized_label = f"{expected_label} {int(match.group(2))}"
        path = (project / relative).resolve()
        if normalized_label.lower() in seen_labels:
            errors.append(f"duplicate reference label: {normalized_label}")
        if str(path).lower() in seen_paths:
            errors.append(f"duplicate reference path: {path}")
        seen_labels.add(normalized_label.lower())
        seen_paths.add(str(path).lower())
        assets.append({"path": path, "role": role, "label": normalized_label})
    if errors:
        raise ValueError("reference asset validation failed: " + "; ".join(errors))
    return assets, warnings


def character_ref_map(storyboard, project):
    result = {}
    for character in storyboard.get("characters", []):
        for relative in (character.get("refs") or {}).values():
            if relative:
                result[str((project / relative).resolve()).lower()] = character.get("name") or Path(relative).stem
    return result


def short_name(ref_path, character_map):
    resolved = str(ref_path.resolve()).lower()
    if resolved in character_map:
        return character_map[resolved]
    stem = ref_path.stem.lower()
    if "lobby" in stem:
        return "Foot Spa Lobby"
    if "room88" in stem:
        return "Room 88"
    return ref_path.stem


def normalized_dialogue(value):
    value = value.split("：", 1)[-1].split(":", 1)[-1]
    return re.sub(r"[\s。！？!?，,]", "", value)


def normalized_text(value):
    return re.sub(r"[\s。！？!?，,]", "", value)


def validate_dialogue_markup(detail, expected_dialogue):
    tags = list(DIALOGUE_TAG_RE.finditer(detail))
    payloads = [match.group(2).strip() for match in tags]
    errors = []
    for index, (match, payload) in enumerate(zip(tags, payloads), 1):
        if SPEAKER_PREFIX_RE.match(payload):
            errors.append(f"dialogue tag {index} contains a speaker-name prefix")
        before = detail[max(0, match.start() - 220):match.start()]
        if not re.search(r"\(S\d+\)", before):
            errors.append(f"dialogue tag {index} has no stable (Sx) speaker ID")
    compact_payloads = [normalized_text(payload) for payload in payloads]
    for dialogue in expected_dialogue or []:
        spoken = normalized_dialogue(dialogue)
        if spoken and spoken not in compact_payloads:
            errors.append(f"storyboard dialogue is not an exact <d> payload: {dialogue}")
    if errors:
        raise ValueError("dialogue markup validation failed: " + "; ".join(errors))


def resolve_segment_duration(segment):
    """Resolve duration from authored shot lengths; never silently default to 10s."""
    declared = segment.get("duration")
    raw_shot_durations = segment.get("shot_durations")
    shot_durations = None
    if raw_shot_durations is not None:
        if not isinstance(raw_shot_durations, list) or not raw_shot_durations:
            raise ValueError("shot_durations must be a non-empty list")
        shot_durations = [float(value) for value in raw_shot_durations]
        if any(value <= 0 for value in shot_durations):
            raise ValueError("shot_durations must contain only positive values")
        calculated = round(sum(shot_durations), 6)
        if declared in (None, "auto"):
            duration = calculated
        else:
            duration = float(declared)
            if abs(duration - calculated) > 0.001:
                raise ValueError(
                    f"segment duration {duration:g}s does not equal shot sum {calculated:g}s"
                )
    else:
        if declared in (None, "auto"):
            raise ValueError("duration must be numeric or derivable from shot_durations")
        duration = float(declared)
    if not 4 <= duration <= 15:
        raise ValueError("generation-unit duration must be 4-15 seconds")
    return duration, shot_durations


def compile_segment(project, storyboard, segment, width, height, fps):
    seg_id = int(segment["id"])
    duration, authored_shot_durations = resolve_segment_duration(segment)
    prompt_path = project / segment.get("prompt_file", f"prompts/seg_{seg_id:02d}.txt")
    if not prompt_path.is_file():
        raise ValueError(f"prompt file not found: {prompt_path}")
    text = prompt_path.read_text(encoding="utf-8-sig")
    sections = parse_sections(text)
    preamble, shots = parse_shots(sections["detailed_description"], duration, fps)
    if authored_shot_durations is not None:
        if len(authored_shot_durations) != len(shots):
            raise ValueError(
                f"shot_durations count {len(authored_shot_durations)} does not match {len(shots)} shots"
            )
        for index, (declared_seconds, shot) in enumerate(zip(authored_shot_durations, shots), 1):
            actual_seconds = shot["length"] / fps
            # Independent rounding of adjacent shot boundaries can move one
            # realized length by a full frame while the total remains exact.
            if abs(declared_seconds - actual_seconds) > (1.01 / fps + 0.001):
                raise ValueError(
                    f"shot {index} duration {actual_seconds:g}s does not match authored {declared_seconds:g}s"
                )
    schema_version = segment.get(
        "director_schema_version", storyboard.get("meta", {}).get("director_schema_version", 1)
    )
    strict_creative = int(schema_version) >= 2
    validate_director_density(shots, duration, fps)
    creative_intent, creative_warnings = validate_creative_intent(segment, shots, strict_creative)
    validate_dialogue_markup(sections["detailed_description"], segment.get("dialogue", []))
    definitions = {int(n): description.strip() for n, description in SUBJECT_RE.findall(sections["subject_definitions"])}
    retention = {int(n): (marker, note.strip()) for n, marker, note in RETENTION_RE.findall(sections["retention_analysis"])}
    reference_assets, reference_warnings = resolve_reference_assets(project, segment, strict_creative)
    refs = [asset["path"] for asset in reference_assets]
    missing_refs = [str(path) for path in refs if not path.is_file()]
    if missing_refs:
        raise ValueError("missing reference files: " + ", ".join(missing_refs))
    if any(asset["role"] == "composition_picture" for asset in reference_assets):
        raise ValueError("composition_picture parsing is defined by schema v2 but not yet wired to the current Director node")
    if len(definitions) != len(refs):
        raise ValueError(f"subject/reference count mismatch: {len(definitions)} subjects vs {len(refs)} refs")
    cmap = character_ref_map(storyboard, project)
    subjects = []
    definition_ids = sorted(definitions)
    for subject_id, ref_path, asset in zip(definition_ids, refs, reference_assets):
        marker, note = retention.get(subject_id, ("fully_preserved", "Preserve the defined reference role."))
        subjects.append({"images": [], "local_path": str(ref_path), "description": definitions[subject_id],
                         "shortName": short_name(ref_path, cmap),
                         "kind": REFERENCE_ROLES[asset["role"]][1], "referenceRole": asset["role"],
                         "referenceLabel": asset["label"],
                         "retention": marker, "retentionNote": note})
    warnings = creative_warnings + reference_warnings
    for number, shot in enumerate(shots, 1):
        range_match = re.search(r"(\d+(?:\.\d+)?)[-–](\d+(?:\.\d+)?)秒", shot["prompt"])
        if range_match:
            stated_start, stated_end = float(range_match.group(1)), float(range_match.group(2))
            actual_start, actual_end = shot["start"] / fps, (shot["start"] + shot["length"]) / fps
            if abs(stated_start - actual_start) > 0.01 or abs(stated_end - actual_end) > 0.01:
                warnings.append(f"shot {number} internal range {stated_start:g}-{stated_end:g}s conflicts with marker range {actual_start:g}-{actual_end:g}s")
    if storyboard.get("meta", {}).get("prompt_mode") == "hybrid" and not sections["constraints"]:
        warnings.append("hybrid prompt has no constraints block")
    global_parts = [part for part in (preamble, sections["subject_definitions"],
                    ("Constraints: " + sections["constraints"] if sections["constraints"] else "")) if part]
    frames = int(round(duration * fps))
    timeline = {"mainTrackEnabled": True, "audioTrackEnabled": True, "motionTrackEnabled": True,
        "propHeight": 90, "globalPropHeight": 126, "showFilenames": True, "showPromptZones": True,
        "overrideAudio": False, "inpaint_audio": True, "global_prompt": "\n\n".join(global_parts),
        "retake_global_prompt": "", "overall_soundscape": sections["overall_soundscape"],
        "non_diegetic_music": sections["non_diegetic_music"], "prompt_override": "",
        "prompt_override_on": False, "retakeMode": False, "retakeStart": 24, "retakeLength": 48,
        "retakePrompt": "", "retakeStrength": 1, "retakeVideo": None, "normalStartFrame": 0,
        "normalDurationFrames": frames, "reference_mode": "REF2VA", "prompt_format": "minimax",
        "analyzeProvider": "ollama", "analyzeBaseUrl": "", "analyzeModel": "",
        "summary": sections["summary"], "task_type_override": "", "subjectSlotCount": len(subjects),
        "subjects": [{k: v for k, v in subject.items() if k != "local_path"} for subject in subjects],
        "segments": shots, "motionSegments": [], "audioSegments": []}
    return {"schema": 2 if strict_creative else 1, "segment_id": seg_id, "title": segment.get("title", f"seg{seg_id:02d}"),
        "source_prompt": str(prompt_path),
        "director_layer": "creative-intent-validated" if creative_intent else "timing-grammar-validated",
        "creative_intent": creative_intent,
        "references": [{"shortName": x["shortName"], "local_path": x["local_path"],
                        "role": x["referenceRole"], "label": x["referenceLabel"]} for x in subjects],
        "director_inputs": {"start_second": 0, "end_second": duration, "duration_seconds": duration,
            "start_frame": 0, "end_frame": frames, "duration_frames": frames,
            "timeline_data": timeline, "local_prompts": " | ".join(x["prompt"] for x in shots),
            "segment_lengths": ",".join(str(x["length"]) for x in shots), "guide_strength": "",
            "use_custom_audio": True, "use_custom_motion": True, "inpaint_audio": True,
            "frame_rate": fps, "display_mode": "seconds", "custom_width": width,
            "custom_height": height, "resize_method": "crop", "divisible_by": 32,
            "img_compression": 0, "override_audio": False, "ref_image_size": "match",
            "shift_video": 12.0, "shift_audio": 3.0,
            "ref_image_notes": " ".join(f"@ref{i}= {x['shortName']}." for i, x in enumerate(subjects, 1)),
            "minimax_settings_ui": "", "timeline_ui": ""}, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--segments", help="comma-separated segment numbers")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=704)
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()
    project = args.project.resolve()
    storyboard = load_json(project / "storyboard.json")
    selected = {int(x) for x in args.segments.split(",")} if args.segments else None
    outputs, errors, warnings, total_duration = [], [], [], 0.0
    for segment in storyboard.get("segments", []):
        seg_id = int(segment["id"])
        if selected is not None and seg_id not in selected:
            continue
        try:
            spec = compile_segment(project, storyboard, segment, args.width, args.height, args.fps)
            output = project / "director" / f"seg_{seg_id:02d}.director.json"
            save_json(output, spec)
            outputs.append(str(output))
            total_duration += spec["director_inputs"]["duration_seconds"]
            warnings.extend({"segment": seg_id, "warning": item} for item in spec["warnings"])
        except Exception as exc:
            errors.append({"segment": seg_id, "error": str(exc)})
    report = {"schema": 1, "director_creative_layer_verified": not errors,
              "director_compiler_verified": not errors, "compiled": len(outputs),
              "compiled_duration_seconds": round(total_duration, 3),
              "outputs": outputs, "warnings": warnings, "errors": errors}
    save_json(project / "jobs/local-runner/director-report.json", report)
    print(json.dumps({"compiled": len(outputs), "compiled_duration_seconds": round(total_duration, 3),
                      "warnings": len(warnings), "errors": errors,
                      "director_creative_layer_verified": not errors}, ensure_ascii=False, separators=(",", ":")))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
