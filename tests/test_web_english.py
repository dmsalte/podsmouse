"""English web UI over the French upstream page and server (podsmouse/web_english.py)."""

import ast
import os
import re
import tempfile
import types
import unittest

from podsmouse import english, web_english
from podsmouse import main as pm

WEB_SRC = pm.UPSTREAM_DIR / "mousepods_web.py"
UI_SRC = pm.UPSTREAM_DIR / "ui" / "index.html"
ACCENTS = re.compile(r"[àâçéèêëîïôûùüœ«»]", re.I)
# Strings the server sends that never reach the page (HTTP API error bodies).
API_ONLY = {"introuvable", "JSON invalide"}


def upstream_html():
    return UI_SRC.read_text(encoding="utf-8")


def visible_html(html):
    """The page without HTML, CSS and JS comments (upstream keeps French comments)."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    html = re.sub(r"/\*.*?\*/", "", html, flags=re.S)
    return re.sub(r"^\s*//.*$", "", html, flags=re.M)


def upstream_web_tables():
    """The label tables as literals from the upstream source, without importing the module."""
    tree = ast.parse(WEB_SRC.read_text())
    tables = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in web_english.TABLES:
                tables[name] = ast.literal_eval(node.value)
    return tables


def french_server_strings():
    """String constants in mousepods_web with accents, except docstrings and the label tables."""
    tree = ast.parse(WEB_SRC.read_text())
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in web_english.TABLES
                                                for t in node.targets):
            skip.update(id(c) for c in ast.walk(node.value))
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
            skip.add(id(node.body[0].value))
    return {n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip
            and ACCENTS.search(n.value)}


class PageTest(unittest.TestCase):
    def test_every_replacement_matches_upstream(self):
        html = upstream_html()
        missing = [fr[:70] for fr, _ in web_english.HTML_REPLACEMENTS if fr not in html]
        self.assertEqual(missing, [], "upstream/ui/index.html changed; update HTML_REPLACEMENTS")

    def test_no_french_left_on_the_page(self):
        page = visible_html(web_english.translate_html(upstream_html()))
        left = [line.strip()[:100] for line in page.splitlines() if ACCENTS.search(line)]
        self.assertEqual(left, [], "translate these in HTML_REPLACEMENTS")
        self.assertIn('<html lang="en">', page)

    def test_keys_sent_to_the_server_are_unchanged(self):
        """Mode and source values are config keys, not labels; they must stay as upstream has them."""
        before = re.findall(r'data-(?:v|k|key|cmd|p)="([^"]*)"', upstream_html())
        after = re.findall(r'data-(?:v|k|key|cmd|p)="([^"]*)"', web_english.translate_html(upstream_html()))
        self.assertEqual(before, after)
        for fr, en in web_english.HTML_REPLACEMENTS:
            self.assertEqual(fr.count("${"), en.count("${"), fr[:70])

    def test_page_matches_the_english_server_values(self):
        page = web_english.translate_html(upstream_html())
        self.assertIn('b.state==="charging"', page)
        self.assertIn('b.state==="disconnected"', page)
        self.assertIn(web_english.BATTERY_STATE_EN[0x01], page)
        self.assertIn(web_english.BATTERY_STATE_EN[0x04], page)
        self.assertIn('i.label==="Name"', page)
        self.assertEqual(web_english.INFO_LABELS_EN[0], "Name")
        self.assertIn('r.kind==="feature"', page)
        self.assertEqual(web_english.translate("feature"), "feature")


class ServerTest(unittest.TestCase):
    def test_tables_have_the_same_keys_as_upstream(self):
        upstream = upstream_web_tables()
        self.assertEqual(set(upstream), set(web_english.TABLES))
        for name, table in upstream.items():
            en = web_english.TABLES[name]
            if isinstance(table, dict):
                self.assertEqual(set(en), set(table), name)
            else:
                self.assertEqual(len(en), len(table), name)

    def test_every_french_server_string_is_translated(self):
        known = set(web_english.PHRASES) | set(english.LOG_TEMPLATES) | API_ONLY
        self.assertEqual(sorted(french_server_strings() - known), [], "add these to web_english.PHRASES")

    def test_translate(self):
        self.assertEqual(web_english.translate("Démarrage…"), "Starting…")
        self.assertEqual(web_english.translate("Recherche des AirPods… (aucun AirPods connecté)"),
                         "Looking for the AirPods… (no AirPods connected)")
        self.assertEqual(web_english.translate("Champ 12"), "Field 12")
        self.assertEqual(web_english.translate("Look at the screen"), "Look at the screen")
        self.assertIsNone(web_english.translate(None))


class FakeWebUI:
    def telemetry(self):
        return {"status": "Connexion perdue — reconnexion…", "rate": 96,
                "calib": {"text": "Calibration réussie", "message": None}}

    def state(self):
        return {"info": [{"label": "Name", "value": "x"}, {"label": "Champ 13", "value": "y"}],
                "services": [{"reports": [{"kind": "entrée"}, {"kind": "feature"}]}],
                "counts": {"0x04": 3, "autre": 1}}


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.web = types.SimpleNamespace(UI_FILE=str(UI_SRC), WebUI=FakeWebUI,
                                         **{name: None for name in web_english.TABLES})

    def test_install_serves_an_english_page_and_tables(self):
        web_english.install(self.web, self.tmp.name)
        self.assertEqual(self.web.UI_FILE, os.path.join(self.tmp.name, "ui-en.html"))
        self.assertEqual(os.listdir(self.tmp.name), ["ui-en.html"])
        with open(self.web.UI_FILE, encoding="utf-8") as f:
            self.assertIn('<html lang="en">', f.read())
        self.assertEqual(self.web.BATTERY_STATE, web_english.BATTERY_STATE_EN)
        self.assertIsNot(self.web.BATTERY_STATE, web_english.BATTERY_STATE_EN)
        self.assertEqual(self.web.AIM_TEXT, web_english.AIM_TEXT_EN)
        path = self.web.UI_FILE
        web_english.install(self.web, self.tmp.name)
        self.assertEqual(self.web.UI_FILE, path, "second install must be a no-op")

    def test_webui_sends_english_text(self):
        web_english.install(self.web, self.tmp.name)
        ui = self.web.WebUI()
        self.assertIsInstance(ui, FakeWebUI)
        t = ui.telemetry()
        self.assertEqual(t["status"], "Connection lost — reconnecting…")
        self.assertEqual(t["calib"]["text"], "Calibration done")
        self.assertIsNone(t["calib"]["message"])
        s = ui.state()
        self.assertEqual([i["label"] for i in s["info"]], ["Name", "Field 13"])
        self.assertEqual([r["kind"] for r in s["services"][0]["reports"]], ["input", "feature"])
        self.assertEqual(s["counts"], {"0x04": 3, "other": 1})


class LogCoverageTest(unittest.TestCase):
    def test_web_log_templates_are_translated(self):
        tree = ast.parse(WEB_SRC.read_text())
        found = {n.args[0].value for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr in {"debug", "info", "warning", "error", "exception"}
                 and isinstance(n.func.value, ast.Attribute) and n.func.value.attr == "log"
                 and n.args and isinstance(n.args[0], ast.Constant)}
        self.assertTrue(found)
        self.assertEqual(sorted(found - set(english.LOG_TEMPLATES)), [])


if __name__ == "__main__":
    unittest.main()
