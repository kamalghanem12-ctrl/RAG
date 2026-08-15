"""The enforcement layer is itself under test.

A hookify rule that does not parse, or whose regex does not compile, is silently
inert — it fails open, and nothing reports it. These tests fail loudly instead.

The false-positive sweep matters as much as the rest: an over-broad blocking rule
is worse than no rule. It trains people to work around the hook, and then the hook
protects nothing. This caught two real cases during authoring — rules that would
have blocked edits to the very documentation describing them.

See .claude/README.md
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RULES_DIR = REPO / ".claude"

SCANNABLE = {".py", ".sql", ".toml", ".json", ".md", ".yml", ".yaml", ".conf", ".ini"}


def _scalar(frontmatter: str, key: str) -> str | None:
    m = re.search(rf"^{key}:\s*(.+)$", frontmatter, re.M)
    return m.group(1).strip() if m else None


def _parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path.name}: no YAML frontmatter"
    fm = m.group(1)

    patterns: list[tuple[str, str]] = []
    top = re.search(r"^pattern:\s*(.+)$", fm, re.M)
    conds = re.findall(
        r"^\s+-\s+field:\s*(\S+)\s*\n\s+operator:\s*(\S+)\s*\n\s+pattern:\s*(.+)$",
        fm,
        re.M,
    )
    if top and not conds:
        patterns.append(("<any>", top.group(1).strip()))
    for field, _operator, pattern in conds:
        patterns.append((field, pattern.strip()))

    return {
        "path": path,
        "name": _scalar(fm, "name"),
        "event": _scalar(fm, "event"),
        "action": _scalar(fm, "action") or "warn",
        "enabled": _scalar(fm, "enabled"),
        "patterns": patterns,
        "body": text[m.end() :],
    }


RULE_FILES = sorted(RULES_DIR.glob("hookify.*.local.md"))
RULES = [_parse(p) for p in RULE_FILES]


def test_rules_exist():
    assert RULE_FILES, "no hookify rules found — the enforcement layer is missing"


@pytest.mark.parametrize("rule", RULES, ids=lambda r: r["path"].name)
def test_rule_is_well_formed(rule):
    assert rule["name"], "missing name"
    assert rule["enabled"] == "true", "rule is not enabled"
    assert rule["event"] in {"bash", "file", "stop", "prompt", "all"}, rule["event"]
    assert rule["action"] in {"warn", "block"}, rule["action"]
    assert rule["patterns"], "no pattern"
    assert rule["body"].strip(), "no message body — the rule would fire with no explanation"


@pytest.mark.parametrize("rule", RULES, ids=lambda r: r["path"].name)
def test_rule_regexes_compile(rule):
    for field, pattern in rule["patterns"]:
        try:
            re.compile(pattern)
        except re.error as exc:  # pragma: no cover
            pytest.fail(f"{field}: {exc}\n  {pattern}")


@pytest.mark.parametrize(
    "rule",
    [r for r in RULES if r["event"] == "file" and r["action"] == "block"],
    ids=lambda r: r["path"].name,
)
def test_blocking_rule_scopes_to_file_type(rule):
    """A blocking file rule without a file_path condition will eventually fire on
    documentation that merely describes the forbidden pattern — including its own
    rule file and its own ADR."""
    fields = {field for field, _ in rule["patterns"]}
    assert "file_path" in fields, (
        "blocking file rule has no file_path condition; scope it to code files"
    )


@pytest.mark.parametrize(
    "rule",
    [r for r in RULES if r["event"] == "file"],
    ids=lambda r: r["path"].name,
)
def test_no_blocking_false_positives_in_repo(rule):
    """Sweep every tracked file. Nothing already committed should trip a block."""
    if rule["action"] != "block":
        pytest.skip("warn-level rule")

    by_field = dict(rule["patterns"])
    path_rx = re.compile(by_field["file_path"]) if "file_path" in by_field else None
    text_pat = by_field.get("new_text") or by_field.get("<any>")
    if text_pat is None:
        pytest.skip("path-only rule")
    text_rx = re.compile(text_pat)

    offenders = []
    for target in REPO.rglob("*"):
        if not target.is_file() or ".git" in target.parts:
            continue
        if target.suffix not in SCANNABLE:
            continue
        rel = target.relative_to(REPO).as_posix()
        if path_rx and not path_rx.search(rel):
            continue
        match = text_rx.search(target.read_text(encoding="utf-8", errors="replace"))
        if match:
            line = target.read_text(encoding="utf-8", errors="replace")[: match.start()].count("\n") + 1
            offenders.append(f"{rel}:{line} -> {match.group(0)[:70]!r}")

    assert not offenders, "rule fires on committed files:\n  " + "\n  ".join(offenders)
