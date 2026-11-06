"""English output layer over the French upstream messages (podsmouse/english.py)."""

import ast
import contextlib
import io
import logging
import types
import unittest

from podsmouse import english
from podsmouse import main as pm

UPSTREAM_SRC = pm.UPSTREAM_DIR / "airpods_mouse_controller.py"
LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}


def upstream_log_templates():
    """Every constant first argument of log.<level>(...) in the upstream controller."""
    tree = ast.parse(UPSTREAM_SRC.read_text())
    found = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in LOG_METHODS and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "log" and node.args
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            found.add(node.args[0].value)
    return found


class CoverageTest(unittest.TestCase):
    """Guards against upstream updates that add French text we do not translate."""

    def test_every_upstream_log_template_is_translated(self):
        missing = sorted(upstream_log_templates() - set(english.LOG_TEMPLATES))
        self.assertEqual(missing, [], "add these to english.LOG_TEMPLATES")

    def test_templates_keep_their_placeholders(self):
        for fr, en in english.LOG_TEMPLATES.items():
            self.assertEqual(
                [p for p in ("%s", "%d") for _ in range(fr.count(p))],
                [p for p in ("%s", "%d") for _ in range(en.count(p))],
                fr,
            )

    def test_calibration_text_has_the_same_shape_as_upstream(self):
        up = pm.load_upstream()
        original = {src: set(steps) for src, steps in getattr(up, "_podsmouse_fr_calib", up.CALIB_TEXT).items()}
        self.assertEqual({src: set(steps) for src, steps in english.CALIB_TEXT_EN.items()}, original)
        for step in up.CALIB_STEPS:
            for src in english.CALIB_TEXT_EN:
                self.assertIn(step, english.CALIB_TEXT_EN[src])

    def test_source_names_have_the_same_keys(self):
        up = pm.load_upstream()
        self.assertEqual(set(english.SOURCE_NAMES_EN), {"head", "case", "hand"})
        self.assertTrue(set(english.SOURCE_NAMES_EN) >= set(getattr(up, "SOURCE_NAMES", {})))


class TranslateTest(unittest.TestCase):
    def test_phrases_and_patterns(self):
        t = english.translate
        self.assertEqual(t("Recentré"), "Recentered")
        self.assertEqual(t("Mode souris"), "Mode mouse")
        self.assertEqual(t("Source : HEAD  —  étape 2/7"), "Source: HEAD  —  step 2/7")
        self.assertEqual(t("Profil enregistré : 2024_head"), "Profile saved: 2024_head")
        self.assertEqual(t("Mesures reçues   |   écouteurs : ear"), "Receiving data   |   buds: ear")
        self.assertEqual(t("Connexion perdue ([Errno 112] aucun AirPods connecté) — nouvel essai…"),
                         "Connection lost ([Errno 112] no AirPods connected) — retrying…")

    def test_unknown_text_is_unchanged(self):
        self.assertEqual(english.translate("40:B3:FA:73:17:61"), "40:B3:FA:73:17:61")
        self.assertEqual(english.translate(42), 42)


class LogTranslatorTest(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test-english-%d" % id(self))
        self.logger.propagate = False
        self.stream = io.StringIO()
        handler = logging.StreamHandler(self.stream)
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)
        self.logger.addFilter(english.LogTranslator())
        self.logger.setLevel(logging.DEBUG)

    def test_template_and_exception_argument(self):
        self.logger.warning("Connexion impossible (%s) — nouvel essai dans %ss",
                            OSError(112, "aucun AirPods connecté"), 4)
        self.assertEqual(self.stream.getvalue().strip(),
                         "Cannot connect ([Errno 112] no AirPods connected) — retrying in 4s")

    def test_mode_argument(self):
        self.logger.info("Démarrage — mode %s, source %s", "souris", "auto")
        self.assertEqual(self.stream.getvalue().strip(), "Starting — mode mouse, source auto")


class InstallTest(unittest.TestCase):
    def fake_upstream(self):
        notes = []
        up = types.SimpleNamespace(
            SOURCE_NAMES={"head": "tête", "case": "boîtier", "hand": "main"},
            CALIB_TEXT={"head": {"still": "Regarde"}},
            notify=lambda cfg, text: notes.append(text),
        )
        return up, notes

    def test_install_switches_tables_print_and_notify(self):
        up, notes = self.fake_upstream()
        english.install(up)
        self.assertEqual(up.SOURCE_NAMES["head"], "head")
        self.assertEqual(up.CALIB_TEXT["head"]["yaw"], "Turn your head to the LEFT")
        up.notify({}, "Contrôle actif")
        self.assertEqual(notes, ["Control active"])
        self.assertIs(up.print, english.english_print)

    def test_install_twice_is_harmless(self):
        up, notes = self.fake_upstream()
        english.install(up)
        english.install(up)
        up.notify({}, "Recentré")
        self.assertEqual(notes, ["Recentered"])

    def test_diag_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            english.english_print("\r[head   ] lacet    +2.6°/s  tangage    +3.3°/s  roulis    -1.4°/s"
                                  "  biais ok  éch. 21311   ", end="")
        self.assertEqual(out.getvalue(), "\r[head   ] yaw    +2.6°/s  pitch    +3.3°/s  roll    -1.4°/s"
                                         "  bias ok  samples 21311   ")


class EnglishTkTest(unittest.TestCase):
    """english_tk against a stand-in for tkinter (no display needed)."""

    def fake_tk(self):
        class Misc:
            def configure(self, cnf=None, **kw):
                self.kw.update(kw)
            config = configure

        class Widget(Misc):
            def __init__(self, master=None, cnf=None, **kw):
                self.kw = dict(kw)

        return types.SimpleNamespace(
            Misc=Misc,
            Label=type("Label", (Widget,), {}),
            Button=type("Button", (Widget,), {}),
            Radiobutton=type("Radiobutton", (Widget,), {}),
        )

    def test_texts_are_translated_inside_and_restored_after(self):
        tk = self.fake_tk()
        orig_init, orig_conf = tk.Button.__init__, tk.Misc.configure
        with english.english_tk(tk):
            btn = tk.Button(None, text="Recommencer")
            lbl = tk.Label(None, text="")
            lbl.configure(text="✔ Calibration réussie !\nTu peux fermer cette fenêtre.")
            rb = tk.Radiobutton(None, text="AirPod en main")
        self.assertEqual(btn.kw["text"], "Restart")
        self.assertEqual(lbl.kw["text"], "✔ Calibration done!\nYou can close this window.")
        self.assertEqual(rb.kw["text"], "AirPod in hand")
        self.assertIs(tk.Button.__init__, orig_init)
        self.assertIs(tk.Misc.configure, orig_conf)


if __name__ == "__main__":
    unittest.main()
