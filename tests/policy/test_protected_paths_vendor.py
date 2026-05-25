"""SMO-0103 — verify vendor strategy policy additions.

Checks that:
- policies/protected-paths.yml denies vendor clone directories
- policies/agent-allowlist.yml permits the manifest + README
- policies/sensitive-change-labels.yml defines the vendor-pin-update label
- .gitignore excludes vendor clones but keeps tracked vendor files
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(rel: str) -> dict:
    return yaml.safe_load((REPO_ROOT / rel).read_text(encoding="utf-8"))


def test_protected_paths_denies_vendor_clone_directories():
    data = _load_yaml("policies/protected-paths.yml")
    assert "vendor/*/**" in data["deny"], (
        "Expected `vendor/*/**` in deny list to protect clone directories. "
        "Top-level files (MANIFEST.yml, README.md, .gitkeep) are intentionally "
        "NOT denied so agents can edit the manifest under the vendor-pin-update "
        "label."
    )


def test_agent_allowlist_permits_vendor_manifest_and_readme():
    data = _load_yaml("policies/agent-allowlist.yml")
    allow = data["allow"]
    assert "vendor/MANIFEST.yml" in allow
    assert "vendor/README.md" in allow


def test_sensitive_change_labels_defines_vendor_pin_update():
    data = _load_yaml("policies/sensitive-change-labels.yml")
    labels_by_name = {label["name"]: label for label in data["labels"]}

    assert "vendor-pin-update" in labels_by_name, (
        "Label `vendor-pin-update` must be defined per ADR-0003."
    )

    label = labels_by_name["vendor-pin-update"]
    assert "vendor/MANIFEST.yml" in label["paths"]
    assert "team:security" in label["requires"]


def test_gitignore_excludes_vendor_clones_but_keeps_tracked_files():
    text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "vendor/*" in text
    assert "!vendor/MANIFEST.yml" in text
    assert "!vendor/README.md" in text
    assert "!vendor/.gitkeep" in text
