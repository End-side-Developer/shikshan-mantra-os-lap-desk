# SPDX-License-Identifier: GPL-2.0-or-later
"""install — install / list / remove local modules (SMO-0580)."""

import pathlib
import shutil

_USER_MODULES = pathlib.Path.home() / ".local/share/shikshan/modules"


def install(bundle_path: pathlib.Path, force: bool = False) -> None:
    """Copy bundle_path into the user modules directory."""
    _USER_MODULES.mkdir(parents=True, exist_ok=True)
    dest = _USER_MODULES / bundle_path.name
    if dest.exists():
        if force:
            shutil.rmtree(dest)
        else:
            raise FileExistsError(f"{dest} already exists. Use --force to overwrite.")
    shutil.copytree(bundle_path, dest)


def list_modules() -> list[pathlib.Path]:
    """Return list of installed module bundle directories."""
    if not _USER_MODULES.exists():
        return []
    return sorted(p for p in _USER_MODULES.iterdir() if p.is_dir())


def remove(module_id: str) -> None:
    """Remove a module bundle by id."""
    target = _USER_MODULES / module_id
    if not target.exists():
        raise FileNotFoundError(f"Module '{module_id}' not installed at {target}")
    shutil.rmtree(target)
