#!/usr/bin/env python3
"""Deterministic low-context runner for a verified MiniMax H3 ComfyUI graph."""

from __future__ import annotations

import argparse
import copy
import json
import secrets
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from asset_audit import audit_director_spec

DEFAULT_URL = "http://127.0.0.1:8188"
STATE_REL = Path("jobs/local-runner/state.json")
TEMPLATE_REL = Path("jobs/local-runner/verified-template.api.json")


def request_json(url, path, method="GET", payload=None):
    data, headers = None, {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url.rstrip("/") + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def compact(**kwargs):
    print(json.dumps(kwargs, ensure_ascii=False, separators=(",", ":")))


def align32(value):
    return max(32, int(round(value / 32.0)) * 32)


def find_one(graph, class_type):
    matches = [(node_id, node) for node_id, node in graph.items() if node.get("class_type") == class_type]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {class_type} node, found {len(matches)}")
    return matches[0]


def parse_references(items):
    result = {}
    for item in items or []:
        if "=" not in item:
            raise RuntimeError("reference must use Subject Name=ComfyUI input filename")
        name, filename = item.split("=", 1)
        if not name.strip() or not filename.strip():
            raise RuntimeError("reference name and filename must be non-empty")
        result[name.strip()] = filename.strip()
    return result


def upload_image(url, local_path):
    path = Path(local_path).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"reference image not found: {path}")
    boundary = "----codex-h3-" + uuid.uuid4().hex
    chunks = []
    def field(name, value):
        chunks.extend([f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()])
    field("overwrite", "true")
    field("type", "input")
    field("subfolder", "local-h3")
    chunks.extend([f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'.encode(),
        b"Content-Type: image/png\r\n\r\n", path.read_bytes(), b"\r\n",
        f"--{boundary}--\r\n".encode()])
    req = urllib.request.Request(url.rstrip("/") + "/upload/image", data=b"".join(chunks), method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    name = result.get("name")
    if not name:
        raise RuntimeError("ComfyUI image upload did not return a filename")
    subfolder = result.get("subfolder", "")
    return f"{subfolder}/{name}" if subfolder else name


def import_director_ui(path, director, references, url):
    ui = load_json(path)
    nodes = [node for node in ui.get("nodes", []) if node.get("type") == "MiniMaxH3DirectorCS"]
    if len(nodes) != 1:
        raise RuntimeError(f"expected one MiniMaxH3DirectorCS UI node, found {len(nodes)}")
    named = nodes[0].get("widgets_values_named")
    if not isinstance(named, dict) or not named.get("timeline_data"):
        raise RuntimeError("Director UI node has no named timeline data")
    for key, value in named.items():
        if key in director["inputs"]:
            director["inputs"][key] = value
    timeline = json.loads(named["timeline_data"])
    local_by_name = parse_references(references)
    subject_names = {x.get("shortName", "") for x in timeline.get("subjects", [])}
    unknown = sorted(set(local_by_name) - subject_names)
    if unknown:
        raise RuntimeError("reference names not found in Director UI: " + ", ".join(unknown))
    for local_path in local_by_name.values():
        if not Path(local_path).expanduser().is_file():
            raise RuntimeError(f"reference image not found: {local_path}")
    by_name = {name: upload_image(url, local_path) for name, local_path in local_by_name.items()}
    missing = []
    for subject in timeline.get("subjects", []):
        short_name = subject.get("shortName", "")
        if short_name in by_name:
            subject["images"] = [{"name": by_name[short_name]}]
        if not subject.get("images"):
            missing.append(short_name or "unnamed subject")
    if missing:
        raise RuntimeError("Director UI subjects need reference images: " + ", ".join(missing))
    director["inputs"]["timeline_data"] = json.dumps(timeline, ensure_ascii=False, separators=(",", ":"))
    return len(timeline.get("subjects", []))


def import_director_spec(path, director, url):
    spec = load_json(path)
    if spec.get("schema") not in {1, 2} or not isinstance(spec.get("director_inputs"), dict):
        raise RuntimeError("unsupported Director spec")
    inputs = copy.deepcopy(spec["director_inputs"])
    timeline = inputs.get("timeline_data")
    if not isinstance(timeline, dict):
        raise RuntimeError("Director spec timeline_data must be an object")
    references = {item["shortName"]: item["local_path"] for item in spec.get("references", [])}
    subject_names = {item.get("shortName") for item in timeline.get("subjects", [])}
    if set(references) != subject_names:
        raise RuntimeError("Director spec reference names do not match subjects")
    uploaded = {name: upload_image(url, local_path) for name, local_path in references.items()}
    for subject in timeline.get("subjects", []):
        subject["images"] = [{"name": uploaded[subject["shortName"]]}]
    inputs["timeline_data"] = json.dumps(timeline, ensure_ascii=False, separators=(",", ":"))
    for key, value in inputs.items():
        if key in director["inputs"]:
            director["inputs"][key] = value
    return len(timeline.get("subjects", [])), spec


def paths(project):
    return project / STATE_REL, project / TEMPLATE_REL


def inspect(args):
    queue = request_json(args.url, "/queue")
    state, template = paths(args.project)
    compact(reachable=True, template=template.exists(), state=state.exists(),
            running=len(queue.get("queue_running", [])), pending=len(queue.get("queue_pending", [])))


def capture(args):
    history = request_json(args.url, "/history/" + urllib.parse.quote(args.prompt_id))
    entry = history.get(args.prompt_id)
    status = (entry or {}).get("status", {})
    if not entry or not status.get("completed") or status.get("status_str") != "success":
        raise RuntimeError("prompt id is not a confirmed successful history entry")
    graph = entry["prompt"][2]
    director_id, director = find_one(graph, "MiniMaxH3DirectorCS")
    save_id, _ = find_one(graph, "SaveVideo")
    timeline = json.loads(director["inputs"]["timeline_data"])
    state_path, template_path = paths(args.project)
    save_json(template_path, graph)
    save_json(state_path, {"schema": 1, "source_prompt_id": args.prompt_id, "verified": True,
        "director_layer_verified": False, "source_width": int(director["inputs"]["custom_width"]),
        "source_height": int(director["inputs"]["custom_height"]),
        "duration_seconds": director["inputs"].get("duration_seconds"), "director_node": director_id,
        "save_node": save_id, "subject_count": len(timeline.get("subjects", [])), "jobs": []})
    compact(captured=True, prompt_id=args.prompt_id, width=director["inputs"]["custom_width"],
            height=director["inputs"]["custom_height"], director_layer_verified=False)


def get_job_status(url, prompt_id):
    entry = request_json(url, "/history/" + urllib.parse.quote(prompt_id)).get(prompt_id)
    if entry:
        status = entry.get("status", {})
        return status.get("status_str", "unknown"), bool(status.get("completed")), entry
    queue = request_json(url, "/queue")
    for name in ("queue_running", "queue_pending"):
        for item in queue.get(name, []):
            if len(item) > 1 and item[1] == prompt_id:
                return ("running" if name == "queue_running" else "pending"), False, None
    return "unknown", False, None


def submit(args):
    state_path, template_path = paths(args.project)
    state = load_json(state_path)
    if state.get("jobs") and not args.force:
        prior = state["jobs"][-1]
        prior_status, completed, _ = get_job_status(args.url, prior["prompt_id"])
        if not completed and prior_status in {"running", "pending"}:
            raise RuntimeError(f"existing job is {prior_status}: {prior['prompt_id']}")
    graph = copy.deepcopy(load_json(template_path))
    _, director = find_one(graph, "MiniMaxH3DirectorCS")
    _, save_node = find_one(graph, "SaveVideo")
    if args.director_ui and args.director_spec:
        raise RuntimeError("use only one of --director-ui or --director-spec")
    subject_count, director_spec = None, None
    if args.director_spec:
        resolved_spec = args.director_spec.resolve()
        audit = audit_director_spec(resolved_spec)
        audit_path = args.project / "jobs" / "local-runner" / f"asset-audit-seg{int(audit.get('segment_id') or 0):02d}.json"
        save_json(audit_path, audit)
        if not audit["passed"]:
            raise RuntimeError("reference asset audit failed: " + "; ".join(audit["errors"]))
        subject_count, director_spec = import_director_spec(resolved_spec, director, args.url)
    elif args.director_ui:
        subject_count = import_director_ui(args.director_ui.resolve(), director, args.reference, args.url)
    width, height = align32(state["source_width"] * args.scale), align32(state["source_height"] * args.scale)
    director["inputs"]["custom_width"], director["inputs"]["custom_height"] = width, height
    seed = args.seed if args.seed is not None else secrets.randbelow(2**63 - 1)
    for node in graph.values():
        if node.get("class_type") == "RandomNoise" and "noise_seed" in node.get("inputs", {}):
            node["inputs"]["noise_seed"] = seed
    label = args.label or (f"seg{int(director_spec['segment_id']):02d}-low" if director_spec else time.strftime("run-%Y%m%d-%H%M%S"))
    label = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label)
    prefix = f"video/local-h3/{label}"
    save_node["inputs"]["filename_prefix"] = prefix
    result = request_json(args.url, "/prompt", "POST", {"prompt": graph, "client_id": "codex-local-h3-runner"})
    if result.get("node_errors"):
        raise RuntimeError("ComfyUI validation failed: " + json.dumps(result["node_errors"], ensure_ascii=False))
    prompt_id = result.get("prompt_id")
    if not prompt_id:
        raise RuntimeError("ComfyUI did not return prompt_id")
    state.setdefault("jobs", []).append({"label": label, "prompt_id": prompt_id, "status": "submitted",
        "width": width, "height": height, "scale": args.scale, "seed": seed, "prefix": prefix,
        "director_ui": str(args.director_ui.resolve()) if args.director_ui else None,
        "director_spec": str(args.director_spec.resolve()) if args.director_spec else None,
        "segment_id": director_spec.get("segment_id") if director_spec else None, "subject_count": subject_count})
    save_json(state_path, state)
    compact(submitted=True, prompt_id=prompt_id, label=label, width=width, height=height,
            scale=args.scale, seed=seed, director_ui=str(args.director_ui) if args.director_ui else None,
            director_spec=str(args.director_spec) if args.director_spec else None,
            subject_count=subject_count)


def extract_outputs(entry):
    found = []
    for value in (entry or {}).get("outputs", {}).values():
        for key in ("images", "gifs", "audio"):
            found.extend(item for item in (value.get(key, []) or []) if item.get("filename"))
    return found


def status(args):
    state_path, _ = paths(args.project)
    state = load_json(state_path)
    if not state.get("jobs"):
        compact(status="no-jobs")
        return
    job = state["jobs"][-1]
    status_name, completed, entry = get_job_status(args.url, job["prompt_id"])
    job["status"] = status_name
    files, downloaded = extract_outputs(entry), []
    if args.download and completed and status_name == "success":
        out_dir = args.project / "clips" / "raw" / "local-runner"
        out_dir.mkdir(parents=True, exist_ok=True)
        for item in files:
            query = urllib.parse.urlencode({"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": item.get("type", "output")})
            target = out_dir / Path(item["filename"]).name
            urllib.request.urlretrieve(args.url.rstrip("/") + "/view?" + query, target)
            downloaded.append(str(target))
        job["downloaded"] = downloaded
    save_json(state_path, state)
    compact(status=status_name, completed=completed, prompt_id=job["prompt_id"],
            outputs=[x.get("filename") for x in files], downloaded=downloaded)


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "capture", "submit", "status"):
        command = sub.add_parser(name)
        command.add_argument("--project", required=True, type=Path)
        command.set_defaults(func=globals()[name])
    sub.choices["capture"].add_argument("--prompt-id", required=True)
    sub.choices["submit"].add_argument("--scale", type=float, default=0.4)
    sub.choices["submit"].add_argument("--seed", type=int)
    sub.choices["submit"].add_argument("--label")
    sub.choices["submit"].add_argument("--director-ui", type=Path)
    sub.choices["submit"].add_argument("--director-spec", type=Path)
    sub.choices["submit"].add_argument("--reference", action="append", default=[])
    sub.choices["submit"].add_argument("--force", action="store_true")
    sub.choices["status"].add_argument("--download", action="store_true")
    return parser


def main():
    args = build_parser().parse_args()
    args.project = args.project.resolve()
    if not args.project.is_dir():
        raise RuntimeError(f"project not found: {args.project}")
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        compact(error=str(exc))
        sys.exit(1)
