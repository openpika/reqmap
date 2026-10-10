#!/usr/bin/env python3
"""reqmap: Git-versioned, requirement-only product memory for coding agents.

Python 3.9+, standard library only. No code topology or execution plans are stored.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import sys
import tempfile
from collections import deque
from pathlib import Path
from typing import Any

VERSION = "0.1.0"
SCHEMA = 1
STATUSES = ("defined", "in_progress", "pending_acceptance", "done", "deprecated")
REL_TYPES = ("depends_on", "overlaps", "conflicts_with", "related_to")
REVIEW_STATES = ("proposed", "confirmed", "rejected")
CONFIDENCES = ("low", "medium", "high")
START = "<!-- reqmap:start -->"
END = "<!-- reqmap:end -->"
INSTRUCTIONS = """<!-- reqmap:start -->
## Project requirement memory (reqmap)
- At the beginning of a task involving product functionality, read `.reqmap/INDEX.md` if it exists; open only relevant requirement files and `.reqmap/product.md` when needed.
- Treat `.reqmap/catalog.json` as the source of truth. Use the reqmap CLI for changes; never treat an inferred relationship or unverified progress as fact.
- Before adding or changing a requirement, compare existing requirements and examine potential overlaps, dependencies and conflicts. Report plausible impacts with supporting reasons, distinguishing proposed links from confirmed dependencies.
- When development concerning a requirement finishes, **ask the user what its status is** (in progress / pending acceptance / completed / deprecated). Do NOT update status until the user expressly confirms, and quote that confirmation in the status command.
- Record changed product decisions and their reasons with `revise`. Do not save "what to do next" unless the user explicitly asks.
- This memory is for product requirements only; do not store technical architecture, code maps, arbitrary session logs, or secrets.
<!-- reqmap:end -->"""

class ReqmapError(Exception):
    pass


def stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def nonblank(value: str, label: str) -> str:
    v = value.strip()
    if not v:
        raise ReqmapError(f"{label} cannot be blank")
    return v


def folder(root: Path) -> Path:
    return root / ".reqmap"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tempname = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fp:
            fp.write(content)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(tempname, path)
    finally:
        if os.path.exists(tempname):
            os.unlink(tempname)


def save_json(path: Path, data: Any) -> None:
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def load(root: Path) -> dict[str, Any]:
    path = folder(root) / "catalog.json"
    if not path.is_file():
        raise ReqmapError(f"No project memory at {path}. Run `init` first.")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ReqmapError(f"Cannot parse catalog: {exc}") from exc
    if result.get("schema_version") != SCHEMA:
        raise ReqmapError(f"Unsupported schema version {result.get('schema_version')}; expected {SCHEMA}")
    return result


def save(root: Path, data: dict[str, Any], event: dict[str, Any] | None = None) -> None:
    """Persist canonical catalog first; history is an audit trail, not authoritative state."""
    data["updated_at"] = stamp()
    save_json(folder(root) / "catalog.json", data)
    render(root, data)
    if event is not None:
        history = folder(root) / "history.jsonl"
        with history.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps({"at": stamp(), **event}, ensure_ascii=False) + "\n")
            fp.flush()
            os.fsync(fp.fileno())


def feature(data: dict[str, Any], id_: str) -> dict[str, Any]:
    for item in data["features"]:
        if item["id"] == id_.upper():
            return item
    raise ReqmapError(f"Unknown requirement: {id_}")


def escape_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render(root: Path, data: dict[str, Any]) -> None:
    base = folder(root)
    req_dir = base / "features"
    req_dir.mkdir(parents=True, exist_ok=True)
    total = {status: sum(x["status"] == status for x in data["features"]) for status in STATUSES}
    rows = ["# Requirement map", "", f"**Product:** {data['product']['name']}", "", "Source of truth: `catalog.json`. This index and feature pages are generated; edit with the reqmap CLI.", "", "## Status counts", "", " | ".join(f"{s}: {total[s]}" for s in STATUSES), "", "## Features", "", "| ID | Feature | Status | Revision |", "| --- | --- | --- | ---: |"]
    for f in sorted(data["features"], key=lambda x: x["id"]):
        rows.append(f"| [{f['id']}](features/{f['id']}.md) | {escape_md(f['title'])} | {f['status']} | {f['revision']} |")
    rows.extend(["", "## Relationships", "", "Only **confirmed** `depends_on` links represent hard dependencies. Proposed or associative links signal possible impacts.", "", "| From | Relation | To | Review | Confidence | Reason |", "| --- | --- | --- | --- | --- | --- |"])
    for rel in sorted(data["relations"], key=lambda x: (x["from"], x["to"], x["type"])):
        if rel["review"] == "rejected":
            continue
        rows.append(f"| {rel['from']} | {rel['type']} | {rel['to']} | {rel['review']} | {rel['confidence']} | {escape_md(rel['reason'])} |")
    rows.extend(["", "## Product context", "", "See [`product.md`](product.md) for positioning and product-level business principles.", ""])
    atomic_write(base / "INDEX.md", "\n".join(rows))
    existing = set(req_dir.glob("REQ-*.md"))
    expected = set()
    for f in data["features"]:
        path = req_dir / f"{f['id']}.md"
        expected.add(path)
        lines = [f"# {f['id']} · {f['title']}", "", f"**Status:** {f['status']}  ", f"**Revision:** {f['revision']}  ", f"**Updated:** {f['updated_at']}", "", "## Function", "", f["summary"], "", "## Why this exists", "", f["rationale"], "", "## Business rules", ""]
        lines.extend(f"- {rule}" for rule in f["rules"])
        if not f["rules"]:
            lines.append("_No business rules recorded yet._")
        lines.extend(["", "## Acceptance / status confirmation", ""])
        if f.get("acceptance"):
            a = f["acceptance"]
            lines.append(f"- Confirmed at: {a['at']}")
            lines.append(f"- User confirmation: {a['confirmation']}")
        else:
            lines.append("_Not confirmed by the user._")
        lines.extend(["", "Generated from `../catalog.json`; make changes via CLI.", ""])
        atomic_write(path, "\n".join(lines))
    for obsolete in existing - expected:
        obsolete.unlink()


def install_agents(root: Path) -> None:
    path = root / "AGENTS.md"
    if path.exists():
        content = path.read_text(encoding="utf-8")
        if START in content and END in content:
            content = content[:content.index(START)] + INSTRUCTIONS + content[content.index(END) + len(END):]
        else:
            content = content.rstrip() + "\n\n" + INSTRUCTIONS + "\n"
    else:
        content = "# Codex project instructions\n\n" + INSTRUCTIONS + "\n"
    atomic_write(path, content)


def init(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root
    if (folder(root) / "catalog.json").exists():
        raise ReqmapError("Already initialized. Refusing to overwrite requirements.")
    now = stamp()
    data = {"schema_version": SCHEMA, "product": {"name": nonblank(args.name, "name"), "description": args.description.strip()}, "created_at": now, "updated_at": now, "next_id": 1, "features": [], "relations": []}
    base = folder(root)
    base.mkdir(parents=True, exist_ok=True)
    atomic_write(base / "product.md", f"# {args.name.strip()}\n\n{args.description.strip() or '_Describe product positioning and shared business principles here._'}\n\n## Shared business principles\n\n_Add product-level rules and decision rationale, not technical architecture or future task lists._\n")
    save(root, data, {"action": "init", "actor": "user", "description": data["product"]["name"]})
    if not args.no_agents:
        install_agents(root)
    return {"project": data["product"]["name"], "path": str(base), "agents_installed": not args.no_agents}


def add(args: argparse.Namespace) -> dict[str, Any]:
    data = load(args.root)
    title = nonblank(args.title, "title")
    if any(x["title"].casefold() == title.casefold() for x in data["features"]):
        raise ReqmapError("A feature with the same title exists. Review duplicates before adding.")
    id_ = f"REQ-{data['next_id']:04d}"
    now = stamp()
    new = {"id": id_, "title": title, "summary": nonblank(args.summary, "summary"), "rationale": nonblank(args.why, "why"), "rules": args.rule or [], "status": "defined", "revision": 1, "created_at": now, "updated_at": now, "acceptance": None}
    data["features"].append(new)
    data["next_id"] += 1
    save(args.root, data, {"action": "feature_added", "actor": args.actor, "feature": id_, "after": new})
    return new


def revise(args: argparse.Namespace) -> dict[str, Any]:
    data = load(args.root)
    f = feature(data, args.id)
    before = copy.deepcopy(f)
    patch = {key: getattr(args, key) for key in ("title", "summary", "why") if getattr(args, key) is not None}
    if "why" in patch:
        patch["rationale"] = patch.pop("why")
    for key, value in patch.items():
        f[key] = nonblank(value, key)
    if args.rule is not None:
        f["rules"] = args.rule
    if before == f:
        raise ReqmapError("No requirement changes specified")
    f["revision"] += 1
    f["updated_at"] = stamp()
    save(args.root, data, {"action": "feature_revised", "actor": args.actor, "feature": f["id"], "reason": nonblank(args.reason, "change reason"), "before": before, "after": f})
    return f


def status(args: argparse.Namespace) -> dict[str, Any]:
    data = load(args.root)
    f = feature(data, args.id)
    if f["status"] == args.to:
        raise ReqmapError("Status is unchanged")
    confirmation = nonblank(args.user_confirmation, "user confirmation")
    prev = f["status"]
    f["status"] = args.to
    f["acceptance"] = {"at": stamp(), "confirmation": confirmation} if args.to == "done" else None
    f["updated_at"] = stamp()
    save(args.root, data, {"action": "status_confirmed", "feature": f["id"], "from": prev, "to": args.to, "user_confirmation": confirmation})
    return {"id": f["id"], "previous": prev, "status": f["status"], "user_confirmation": confirmation}


def link_key(rel: dict[str, Any]) -> tuple[str, str, str]:
    a, b, kind = rel["from"], rel["to"], rel["type"]
    if kind != "depends_on" and a > b:
        a, b = b, a
    return (a, b, kind)


def link(args: argparse.Namespace) -> dict[str, Any]:
    data = load(args.root)
    left, right = feature(data, args.from_id)["id"], feature(data, args.to_id)["id"]
    if left == right:
        raise ReqmapError("Cannot create a self-link")
    if args.review == "confirmed" and not args.user_confirmation:
        raise ReqmapError("Confirmed relation requires --user-confirmation")
    candidate = {"from": left, "to": right, "type": args.type, "reason": nonblank(args.reason, "relation reason"), "confidence": args.confidence, "review": args.review, "user_confirmation": args.user_confirmation, "updated_at": stamp()}
    for rel in data["relations"]:
        if link_key(candidate) == link_key(rel):
            raise ReqmapError("Relationship already exists; use `review-link` to confirm or reject")
    data["relations"].append(candidate)
    save(args.root, data, {"action": "relation_added", "actor": "agent" if args.review == "proposed" else "user", "relation": candidate})
    return candidate


def review_link(args: argparse.Namespace) -> dict[str, Any]:
    data = load(args.root)
    left, right = feature(data, args.from_id)["id"], feature(data, args.to_id)["id"]
    key = link_key({"from": left, "to": right, "type": args.type})
    matches = [x for x in data["relations"] if link_key(x) == key]
    if not matches:
        raise ReqmapError("No such relationship")
    relation = matches[0]
    before = copy.deepcopy(relation)
    relation["review"] = args.to
    relation["user_confirmation"] = nonblank(args.user_confirmation, "user confirmation")
    relation["updated_at"] = stamp()
    save(args.root, data, {"action": "relation_reviewed", "before": before, "after": relation, "user_confirmation": args.user_confirmation})
    return relation


def relationship_impact(data: dict[str, Any], target: str, depth: int) -> dict[str, Any]:
    confirmed_adj: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    advisory: list[dict[str, Any]] = []
    for rel in data["relations"]:
        if rel["review"] == "rejected":
            continue
        if rel["type"] == "depends_on" and rel["review"] == "confirmed":
            confirmed_adj.setdefault(rel["to"], []).append((rel["from"], rel))
        elif target in (rel["from"], rel["to"]):
            advisory.append({"other": rel["to"] if target == rel["from"] else rel["from"], "type": rel["type"], "review": rel["review"], "reason": rel["reason"], "confidence": rel["confidence"]})
    reached = {target}
    queue = deque([(target, [], 0)])
    affected = []
    while queue:
        node, path, distance = queue.popleft()
        if distance >= depth:
            continue
        for other, rel in sorted(confirmed_adj.get(node, []), key=lambda pair: pair[0]):
            if other in reached:
                continue
            reached.add(other)
            link_info = {"from": rel["from"], "to": rel["to"], "reason": rel["reason"]}
            chain = path + [link_info]
            affected.append({"id": other, "title": feature(data, other)["title"], "distance": distance + 1, "path": chain})
            queue.append((other, chain, distance + 1))
    return {"feature": target, "hard_dependents": affected, "possible_impacts": advisory, "note": "Hard dependents use confirmed depends_on links only; possible impacts are advisory, not proven."}


def tokens(value: str) -> set[str]:
    # English words + CJK bigrams give a transparent heuristic without external services.
    english = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", value.lower())
    cjk_sequences = re.findall(r"[\u3400-\u9fff]+", value)
    cjk = [part[i:i+2] for part in cjk_sequences for i in range(len(part) - 1)]
    return set(english + cjk)


def suggest(data: dict[str, Any], title: str, summary: str, exclude: str = "", limit: int = 8) -> list[dict[str, Any]]:
    needle = tokens(title + " " + summary)
    result = []
    for f in data["features"]:
        if f["id"] == exclude or f["status"] == "deprecated":
            continue
        target = tokens(f["title"] + " " + f["summary"] + " " + " ".join(f["rules"]))
        overlap = sorted(needle & target)
        if not overlap:
            continue
        score = len(overlap) / max(1, len(needle | target))
        result.append({"id": f["id"], "title": f["title"], "similarity": round(score, 3), "shared_terms": overlap[:12], "note": "Heuristic candidates only; ask Codex to check product semantics."})
    return sorted(result, key=lambda x: (-x["similarity"], x["id"]))[:limit]


def validate(data: dict[str, Any]) -> list[str]:
    problems = []
    features = data.get("features", [])
    ids = [f.get("id", "") for f in features]
    if len(ids) != len(set(ids)):
        problems.append("Duplicate requirement IDs")
    for f in features:
        if not re.fullmatch(r"REQ-\d{4,}", f.get("id", "")):
            problems.append(f"Invalid ID: {f.get('id')}")
        if f.get("status") not in STATUSES:
            problems.append(f"Invalid status: {f.get('id')}")
        if not f.get("title") or not f.get("summary") or not f.get("rationale"):
            problems.append(f"Missing title, summary or rationale: {f.get('id')}")
        if f.get("status") == "done" and not (f.get("acceptance") or {}).get("confirmation"):
            problems.append(f"Done without user confirmation: {f.get('id')}")
    seen = set()
    graph = {id_: [] for id_ in ids}
    for rel in data.get("relations", []):
        if rel["from"] not in ids or rel["to"] not in ids:
            problems.append(f"Orphan relation: {rel['from']} -> {rel['to']}")
        if rel["type"] not in REL_TYPES or rel["review"] not in REVIEW_STATES:
            problems.append(f"Invalid relation: {rel['from']} -> {rel['to']}")
        key = link_key(rel)
        if key in seen:
            problems.append(f"Duplicate relation: {key}")
        seen.add(key)
        if rel["type"] == "depends_on" and rel["review"] == "confirmed" and rel["from"] in graph:
            graph[rel["from"]].append(rel["to"])
    active, completed = set(), set()
    def visit(v: str) -> None:
        if v in active:
            problems.append(f"Confirmed dependency cycle through {v}")
            return
        if v in completed:
            return
        active.add(v)
        for dst in graph.get(v, []):
            visit(dst)
        active.remove(v)
        completed.add(v)
    for id_ in ids:
        visit(id_)
    return problems


def read_history(root: Path, id_: str | None = None) -> list[dict[str, Any]]:
    path = folder(root) / "history.jsonl"
    if not path.exists():
        return []
    result = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except ValueError as exc:
            raise ReqmapError(f"Broken history at line {n}: {exc}") from exc
        if id_ is None or item.get("feature") == id_ or item.get("relation", {}).get("from") == id_ or item.get("relation", {}).get("to") == id_:
            result.append(item)
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="reqmap — product-level requirements memory for Codex")
    p.add_argument("--root", type=lambda value: Path(value).expanduser().resolve(), default=Path.cwd(), help="Project root (default: current directory)")
    p.add_argument("--json", action="store_true", help="Print structured JSON")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="command", required=True)
    def command(name: str, help_: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, help=help_)
    s = command("init", "Create project memory and AGENTS.md instructions")
    s.add_argument("--name", required=True)
    s.add_argument("--description", default="")
    s.add_argument("--no-agents", action="store_true")
    s = command("add", "Record a requirement (initial status is defined)")
    s.add_argument("--title", required=True)
    s.add_argument("--summary", required=True)
    s.add_argument("--why", required=True)
    s.add_argument("--rule", action="append")
    s.add_argument("--actor", default="codex")
    s = command("revise", "Record requirement evolution with rationale")
    s.add_argument("id")
    s.add_argument("--title")
    s.add_argument("--summary")
    s.add_argument("--why")
    s.add_argument("--rule", action="append", default=None, help="Replace all business rules (repeatable)")
    s.add_argument("--reason", required=True, help="Why requirement is changing")
    s.add_argument("--actor", default="codex")
    s = command("status", "Change status ONLY after explicit user confirmation")
    s.add_argument("id")
    s.add_argument("--to", required=True, choices=STATUSES)
    s.add_argument("--user-confirmation", required=True, help="Verbatim user statement approving this status")
    s = command("link", "Propose a relation (or add user-confirmed one)")
    s.add_argument("--from", dest="from_id", required=True)
    s.add_argument("--to", dest="to_id", required=True)
    s.add_argument("--type", required=True, choices=REL_TYPES)
    s.add_argument("--reason", required=True)
    s.add_argument("--confidence", choices=CONFIDENCES, default="medium")
    s.add_argument("--review", choices=("proposed", "confirmed"), default="proposed")
    s.add_argument("--user-confirmation")
    s = command("review-link", "Confirm or reject a proposed relation")
    s.add_argument("--from", dest="from_id", required=True)
    s.add_argument("--to", dest="to_id", required=True)
    s.add_argument("--type", required=True, choices=REL_TYPES)
    s.add_argument("--to-state", dest="to", required=True, choices=("confirmed", "rejected"))
    s.add_argument("--user-confirmation", required=True)
    s = command("list", "Show all requirements")
    s.add_argument("--status", choices=STATUSES)
    s = command("show", "Show full requirement and related edges")
    s.add_argument("id")
    s = command("impact", "Report downstream confirmed dependencies and possible impacts")
    s.add_argument("id")
    s.add_argument("--depth", type=int, default=3)
    s = command("suggest", "Find lexical candidates for AI relation assessment")
    s.add_argument("--title", required=True)
    s.add_argument("--summary", default="")
    s.add_argument("--exclude", default="")
    s = command("history", "Display product requirement change history")
    s.add_argument("id", nargs="?")
    s = command("check", "Validate catalog and relation consistency")
    s = command("sync", "Regenerate readable index and pages from catalog")
    return p


def run(args: argparse.Namespace) -> Any:
    if args.command == "init":
        return init(args)
    if args.command == "add":
        return add(args)
    if args.command == "revise":
        return revise(args)
    if args.command == "status":
        return status(args)
    if args.command == "link":
        return link(args)
    if args.command == "review-link":
        return review_link(args)
    data = load(args.root)
    if args.command == "list":
        return [{"id": x["id"], "title": x["title"], "status": x["status"], "revision": x["revision"]} for x in data["features"] if not args.status or x["status"] == args.status]
    if args.command == "show":
        f = feature(data, args.id)
        return {"feature": f, "relations": [r for r in data["relations"] if f["id"] in (r["from"], r["to"]) and r["review"] != "rejected"]}
    if args.command == "impact":
        if args.depth < 1 or args.depth > 10:
            raise ReqmapError("depth must be between 1 and 10")
        return relationship_impact(data, feature(data, args.id)["id"], args.depth)
    if args.command == "suggest":
        return suggest(data, args.title, args.summary, args.exclude)
    if args.command == "history":
        if args.id:
            feature(data, args.id)
        return read_history(args.root, args.id.upper() if args.id else None)
    if args.command == "check":
        problems = validate(data)
        return {"valid": not problems, "problems": problems, "feature_count": len(data["features"]), "relation_count": len(data["relations"])}
    if args.command == "sync":
        render(args.root, data)
        return {"synced": True}
    raise ReqmapError(f"Unsupported command: {args.command}")


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    try:
        result = run(args)
        if args.json or isinstance(result, (dict, list)):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)
        if args.command == "check" and not result["valid"]:
            return 2
        return 0
    except (ReqmapError, OSError) as exc:
        print(f"reqmap: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
