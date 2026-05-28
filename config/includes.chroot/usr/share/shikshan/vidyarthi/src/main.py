# SPDX-License-Identifier: GPL-2.0-or-later
"""Vidyarthi — Shikshan Mantra OS practice-engine launcher (SMO-0550 skeleton)."""

import importlib.util
import pathlib
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")

from gi.repository import Adw, Gio  # noqa: E402

# Load window module dynamically so this script can run as a top-level file.
_spec = importlib.util.spec_from_file_location(
    "window", pathlib.Path(__file__).parent / "window.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
VidyarthiWindow = _mod.VidyarthiWindow


class VidyarthiApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="in.shikshan.Vidyarthi",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = VidyarthiWindow(application=self)
        win.present()


def main():
    app = VidyarthiApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
