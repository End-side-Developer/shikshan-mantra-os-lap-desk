# SPDX-License-Identifier: GPL-2.0-or-later
"""Put the Vidyarthi src/ dir on sys.path so the GTK-free modules import by name.

These tests exercise the real pipeline (engine subprocess included) with no GTK,
so they run on the Windows dev box with only python3 + sqlite3 + PyYAML.
"""

import pathlib
import sys

_REPO = pathlib.Path(__file__).resolve().parents[3]
_SRC = _REPO / "config/includes.chroot/usr/share/shikshan/vidyarthi/src"
sys.path.insert(0, str(_SRC))
