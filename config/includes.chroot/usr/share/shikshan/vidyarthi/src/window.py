# SPDX-License-Identifier: GPL-2.0-or-later
"""VidyarthiWindow — exercise UI wired to the engine (SMO-0613).

Thin GTK view over the GTK-free core (catalog + session + engine_client + xapi).
All grading logic lives in those modules; this file only renders and dispatches,
which is why the whole pipeline is testable headlessly without GTK.
"""

import gettext
import pathlib
import threading

import gi

# No .po files ship yet (i18n is out of scope for the MVP); gettext.gettext
# returns the source string unchanged until catalogs are installed.
_ = gettext.gettext

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
try:
    gi.require_version("GtkSource", "5")
except ValueError:
    pass

from gi.repository import Adw, GLib, Gtk, GtkSource  # noqa: E402

import catalog  # noqa: E402
from session import EngineError, ExerciseSession  # noqa: E402

_UI_RESOURCE = pathlib.Path(__file__).parent.parent / "data/ui/window.ui"


def _text(value, fallback: str = "") -> str:
    """Locale helper: pick 'en' from a {lang: str} dict, else the value/fallback."""
    if isinstance(value, dict):
        return value.get("en", fallback)
    return value or fallback


@Gtk.Template(filename=str(_UI_RESOURCE))
class VidyarthiWindow(Adw.ApplicationWindow):
    __gtype_name__ = "VidyarthiWindow"

    sidebar_box: Gtk.Box = Gtk.Template.Child()
    content_box: Gtk.Box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session: ExerciseSession | None = None
        self._buffer: GtkSource.Buffer | None = None
        self._results_box: Gtk.Box | None = None
        self._run_btn: Gtk.Button | None = None
        self._submit_btn: Gtk.Button | None = None
        self._module_rows: dict = {}
        self._exercise_rows: dict = {}
        self._exercise_listbox: Gtk.ListBox | None = None
        self.connect("close-request", self._on_close)
        self._build_sidebar()
        self._show_placeholder(_("Select an exercise to begin."))

    # ── sidebar ──────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        modules = catalog.list_modules()
        if not modules:
            self.sidebar_box.append(Gtk.Label(label=_("No modules installed."), xalign=0))
            return

        self.sidebar_box.append(_heading(_("Modules")))
        module_list = Gtk.ListBox()
        module_list.add_css_class("navigation-sidebar")
        module_list.connect("row-activated", self._on_module_activated)
        for mod in modules:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=_text(mod["title"], mod["id"]), xalign=0))
            self._module_rows[row] = mod["id"]
            module_list.append(row)
        self.sidebar_box.append(module_list)

        self.sidebar_box.append(_heading(_("Exercises")))
        self._exercise_listbox = Gtk.ListBox()
        self._exercise_listbox.add_css_class("navigation-sidebar")
        self._exercise_listbox.connect("row-activated", self._on_exercise_activated)
        self.sidebar_box.append(self._exercise_listbox)

    def _on_module_activated(self, _listbox, row):
        module_id = self._module_rows.get(row)
        if module_id:
            self._populate_exercises(module_id)

    def _populate_exercises(self, module_id):
        listbox = self._exercise_listbox
        _clear(listbox)
        self._exercise_rows.clear()
        for ex in catalog.list_exercises(module_id):
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=ex["title"], xalign=0, wrap=True))
            self._exercise_rows[row] = (module_id, ex["exercise_id"])
            listbox.append(row)

    def _on_exercise_activated(self, _listbox, row):
        target = self._exercise_rows.get(row)
        if target:
            self._open_exercise(*target)

    # ── exercise view ────────────────────────────────────────────────────────
    def _open_exercise(self, module_id, exercise_id):
        self._close_session()
        try:
            session = ExerciseSession(module_id, exercise_id, sandbox="auto").open()
        except EngineError as exc:
            self._show_placeholder(_("Could not open exercise: %s") % exc)
            return
        self._session = session

        view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        view.set_margin_top(16)
        view.set_margin_bottom(16)
        view.set_margin_start(16)
        view.set_margin_end(16)

        prompt = Gtk.Label(label=_text(session.prompt), xalign=0, wrap=True)
        prompt.add_css_class("title-4")
        view.append(prompt)

        self._buffer = GtkSource.Buffer()
        sub_engine = getattr(session, "sub_engine", None) or (
            catalog.load_manifest(module_id) or {}
        ).get("sub_engine", "sql")
        _LANG_MAP = {"code": "python3", "sql": "sql"}
        lang_id = _LANG_MAP.get(sub_engine, "sql")
        lang = GtkSource.LanguageManager.get_default().get_language(lang_id)
        if lang is not None:
            self._buffer.set_language(lang)
        self._buffer.set_text(session.starter or "")
        editor = GtkSource.View(buffer=self._buffer)
        editor.set_show_line_numbers(True)
        editor.set_monospace(True)
        editor.set_auto_indent(True)
        scroller = Gtk.ScrolledWindow(vexpand=True)
        scroller.set_child(editor)
        scroller.add_css_class("card")
        view.append(scroller)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_row.set_halign(Gtk.Align.END)
        self._run_btn = Gtk.Button(label=_("Run"))
        self._run_btn.connect("clicked", lambda _b: self._grade(submit=False))
        self._submit_btn = Gtk.Button(label=_("Submit"))
        self._submit_btn.add_css_class("suggested-action")
        self._submit_btn.connect("clicked", lambda _b: self._grade(submit=True))
        button_row.append(self._run_btn)
        button_row.append(self._submit_btn)
        view.append(button_row)

        self._results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        view.append(self._results_box)

        self._set_content(view)

    # ── grading ──────────────────────────────────────────────────────────────
    def _grade(self, submit: bool):
        if self._session is None or self._buffer is None:
            return
        start, end = self._buffer.get_bounds()
        sql = self._buffer.get_text(start, end, False)
        self._set_buttons_sensitive(False)
        self._render_status(_("Grading…"))

        def worker():
            try:
                result = self._session.submit(sql) if submit else self._session.run(sql)
                err = None
            except EngineError as exc:
                result, err = None, str(exc)
            GLib.idle_add(self._on_graded, result, err, submit)

        threading.Thread(target=worker, daemon=True).start()

    def _on_graded(self, result, err, submitted):
        self._set_buttons_sensitive(True)
        if err is not None:
            self._render_status(_("Engine error: %s") % err)
            return False
        self._render_results(result, submitted)
        return False  # don't reschedule the idle callback

    def _render_results(self, result, submitted):
        box = self._results_box
        _clear(box)
        score = result.get("score", 0)
        success = result.get("success", False)
        header = Gtk.Label(xalign=0)
        verdict = _("Correct!") if success else _("Not quite — score %d/100") % score
        header.set_markup(f"<b>{GLib.markup_escape_text(verdict)}</b>")
        header.add_css_class("success" if success else "warning")
        box.append(header)

        for fb in result.get("feedback", []):
            passed = fb.get("passed")
            line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            icon = Gtk.Image.new_from_icon_name(
                "emblem-ok-symbolic" if passed else "window-close-symbolic"
            )
            icon.add_css_class("success" if passed else "error")
            line.append(icon)
            line.append(Gtk.Label(label=_text(fb.get("message", {})), xalign=0, wrap=True))
            box.append(line)

        if not success and self._session and self._session.hints:
            box.append(_heading(_("Hints")))
            for hint in self._session.hints:
                box.append(Gtk.Label(label="• " + _text(hint), xalign=0, wrap=True))

        if submitted and "xapi_id" in result:
            note = Gtk.Label(xalign=0)
            note.add_css_class("dim-label")
            note.set_label(_("Progress recorded."))
            box.append(note)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _render_status(self, text):
        box = self._results_box
        if box is None:
            return
        _clear(box)
        box.append(Gtk.Label(label=text, xalign=0))

    def _set_buttons_sensitive(self, sensitive):
        for btn in (self._run_btn, self._submit_btn):
            if btn is not None:
                btn.set_sensitive(sensitive)

    def _show_placeholder(self, text):
        status = Adw.StatusPage(
            icon_name="accessories-text-editor-symbolic",
            title="Vidyarthi",
            description=text,
        )
        status.set_hexpand(True)
        status.set_vexpand(True)
        self._set_content(status)

    def _set_content(self, widget):
        _clear(self.content_box)
        self.content_box.append(widget)

    def _close_session(self):
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None

    def _on_close(self, *_args):
        self._close_session()
        return False


def _heading(text):
    label = Gtk.Label(label=text, xalign=0)
    label.add_css_class("heading")
    label.set_margin_top(6)
    return label


def _clear(container):
    if container is None:
        return
    child = container.get_first_child()
    while child is not None:
        nxt = child.get_next_sibling()
        container.remove(child)
        child = nxt
