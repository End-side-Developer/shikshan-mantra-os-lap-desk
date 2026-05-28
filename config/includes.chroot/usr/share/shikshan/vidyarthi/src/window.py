# SPDX-License-Identifier: GPL-2.0-or-later
"""VidyarthiWindow — main application window (SMO-0550 skeleton)."""

import pathlib

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

# Runtime catalog location (installed path on the live OS).
_CATALOG_PATHS = [
    pathlib.Path("/usr/share/shikshan/catalogs/official.catalog.yml"),
    # Development fallback: repo root relative path.
    pathlib.Path(__file__).parents[6] / "modules/catalogs/official.catalog.yml",
]

_UI_RESOURCE = pathlib.Path(__file__).parent.parent / "data/ui/window.ui"


@Gtk.Template(filename=str(_UI_RESOURCE))
class VidyarthiWindow(Adw.ApplicationWindow):
    __gtype_name__ = "VidyarthiWindow"

    module_list: Gtk.ListView = Gtk.Template.Child()
    welcome_status: Adw.StatusPage = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_catalog()

    def _load_catalog(self):
        """Populate module_list from the official catalog YAML."""
        try:
            import yaml  # optional dep; only needed if PyYAML is installed
        except ImportError:
            yaml = None

        catalog_path = None
        for p in _CATALOG_PATHS:
            if p.exists():
                catalog_path = p
                break

        if catalog_path is None or yaml is None:
            self._show_no_modules()
            return

        try:
            with catalog_path.open(encoding="utf-8") as f:
                catalog = yaml.safe_load(f)
        except Exception:
            self._show_no_modules()
            return

        modules = catalog.get("modules", [])
        if not modules:
            self._show_no_modules()
            return

        store = Gio.ListStore(item_type=GLib.Variant)
        for mod in modules:
            title = mod.get("title", {})
            label = title.get("en", mod.get("id", "Unknown"))
            store.append(GLib.Variant("s", label))

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self.module_list.set_factory(factory)
        self.module_list.set_model(Gtk.NoSelection(model=store))

    def _on_factory_setup(self, factory, list_item):
        list_item.set_child(Gtk.Label(xalign=0))

    def _on_factory_bind(self, factory, list_item):
        label = list_item.get_child()
        variant = list_item.get_item()
        label.set_text(variant.get_string())

    def _show_no_modules(self):
        self.welcome_status.set_description("No modules installed.")
