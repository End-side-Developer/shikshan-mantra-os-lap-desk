# SPDX-License-Identifier: GPL-2.0-or-later
"""Catalog + module + exercise resolution (SMO-0611).

GTK-free. Pure stdlib + PyYAML so it is unit-testable on any host (Windows
dev box included) with no GObject/GTK introspection present.

Two layouts are supported transparently:

  * Installed (live OS):  catalog at /usr/share/shikshan/catalogs/official.catalog.yml
                          bundles at /usr/share/shikshan/modules/<id>/
  * Dev (repo checkout):  catalog at <repo>/modules/catalogs/official.catalog.yml
                          bundles at <repo>/modules/core/<id>/

The engine resolves an exercise by *file stem* (e.g. ``01-select`` ->
``content/exercises/01-select.yml``), which is distinct from the YAML ``id:``
field inside the file (e.g. ``select-all``).  ``list_exercises`` therefore keys
on the stem.
"""

from __future__ import annotations

import pathlib

import yaml

# ── Installed paths (live OS) ────────────────────────────────────────────────
_INSTALLED_CATALOG = pathlib.Path("/usr/share/shikshan/catalogs/official.catalog.yml")
_INSTALLED_MODULES = pathlib.Path("/usr/share/shikshan/modules")


def _repo_root() -> pathlib.Path | None:
    """Walk upward from this file looking for the in-repo catalog.

    Robust against the exact directory depth (the SMO-0550 skeleton hard-coded
    ``parents[6]`` which was off by one); we search instead of counting.
    """
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "modules" / "catalogs" / "official.catalog.yml").exists():
            return parent
    return None


def catalog_path() -> pathlib.Path | None:
    """Return the catalog file to read, preferring the installed location."""
    if _INSTALLED_CATALOG.exists():
        return _INSTALLED_CATALOG
    root = _repo_root()
    if root is not None:
        return root / "modules" / "catalogs" / "official.catalog.yml"
    return None


def load_catalog() -> dict:
    """Parse the official catalog YAML; ``{}`` if absent/unreadable."""
    path = catalog_path()
    if path is None or not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return {}


def list_modules() -> list[dict]:
    """Return catalog module entries enriched with their manifest title.

    Each item: ``{"id", "version", "title": {lang: str}}``.  Entries whose
    bundle/manifest cannot be resolved are skipped so a broken module never
    blanks the whole launcher.
    """
    out: list[dict] = []
    for entry in load_catalog().get("modules", []):
        mod_id = entry.get("id")
        if not mod_id:
            continue
        manifest = load_manifest(mod_id) or {}
        out.append(
            {
                "id": mod_id,
                "version": entry.get("version", manifest.get("version", "")),
                "title": manifest.get("title", {"en": mod_id}),
            }
        )
    return out


def resolve_bundle_path(module_id: str) -> pathlib.Path | None:
    """Locate a module bundle directory (installed first, then repo)."""
    installed = _INSTALLED_MODULES / module_id
    if installed.is_dir():
        return installed
    root = _repo_root()
    if root is not None:
        dev = root / "modules" / "core" / module_id
        if dev.is_dir():
            return dev
    return None


def load_manifest(module_id: str) -> dict | None:
    """Parse ``manifest.yml`` for a module; ``None`` if unresolved."""
    bundle = resolve_bundle_path(module_id)
    if bundle is None:
        return None
    manifest = bundle / "manifest.yml"
    if not manifest.exists():
        return None
    try:
        with manifest.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        return None


def load_exercise_spec(module_id: str, exercise_id: str) -> dict | None:
    """Parse a single exercise YAML by file stem; ``None`` if unresolved.

    ``exercise_id`` is the filename stem (``01-select``), matching what the
    engine's ``load_exercise`` expects — not the YAML ``id:`` field.
    """
    bundle = resolve_bundle_path(module_id)
    if bundle is None:
        return None
    path = bundle / "content" / "exercises" / f"{exercise_id}.yml"
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        return None


def list_exercises(module_id: str) -> list[dict]:
    """Ordered exercises for a module.

    Returns ``[{"exercise_id": <stem>, "title": <str>, "prompt": {lang: str}}]``.

    ``exercise_id`` is the filename stem the engine expects.  Order follows the
    manifest's ``exercise_spec.exercises`` list when present, else a sorted
    directory listing of ``content/exercises/*.yml``.
    """
    bundle = resolve_bundle_path(module_id)
    if bundle is None:
        return []

    manifest = load_manifest(module_id) or {}
    spec = manifest.get("exercise_spec", {}) or {}
    rel_paths = spec.get("exercises")

    if rel_paths:
        files = [bundle / rel for rel in rel_paths]
    else:
        ex_dir = bundle / "content" / "exercises"
        files = sorted(ex_dir.glob("*.yml")) if ex_dir.is_dir() else []

    out: list[dict] = []
    for path in files:
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8") as fh:
                ex = yaml.safe_load(fh) or {}
        except (OSError, yaml.YAMLError):
            continue
        prompt = ex.get("prompt", {}) or {}
        out.append(
            {
                "exercise_id": path.stem,
                "title": prompt.get("en", path.stem),
                "prompt": prompt,
            }
        )
    return out
