"""tests/integration/test_policy_files_parse.py

Every YAML file under policies/ must be syntactically valid and contain the
required top-level keys for its file. Catches typos before they break the
agent harness or CI.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load(name: str) -> dict:
    return yaml.safe_load((REPO_ROOT / "policies" / name).read_text(encoding="utf-8"))


def test_protected_paths_yml():
    d = _load("protected-paths.yml")
    assert d.get("version") == 1
    assert isinstance(d.get("deny"), list) and d["deny"]
    assert d.get("sensitive_review_required") == 2


def test_agent_allowlist_yml():
    d = _load("agent-allowlist.yml")
    assert d.get("version") == 1
    assert isinstance(d.get("allow"), list) and d["allow"]
    assert isinstance(d.get("append_only"), list)
    assert isinstance(d.get("bash_forbidden"), list)
    assert isinstance(d.get("bash_allowlist"), list)


def test_sensitive_change_labels_yml():
    d = _load("sensitive-change-labels.yml")
    assert isinstance(d.get("labels"), list) and d["labels"]
    for label in d["labels"]:
        assert "name" in label
        assert "paths" in label
        assert "requires" in label


def test_token_budgets_yml():
    d = _load("token-budgets.yml")
    assert "defaults" in d
    assert "types" in d
    assert "absolute_ceiling" in d
    for k in ("max_tokens", "max_wall_minutes", "max_files_changed", "max_diff_lines"):
        assert k in d["absolute_ceiling"]
    # Every per-type budget MUST be <= absolute ceiling
    for t, cap in d["types"].items():
        for k in ("max_tokens", "max_wall_minutes", "max_files_changed", "max_diff_lines"):
            assert cap[k] <= d["absolute_ceiling"][k], f"type {t} field {k} exceeds ceiling"


def test_escalation_matrix_yml():
    d = _load("escalation-matrix.yml")
    assert "contacts" in d and "default" in d["contacts"]
    assert "triggers" in d
    for trigger in ["budget_exceeded", "protected_path_hit", "audit_chain_break"]:
        assert trigger in d["triggers"]
