"""English output for the vendored mousepods code, without editing upstream/.

Upstream writes its terminal output, notifications and calibration window in French.
This module translates that text at runtime:

- log messages: a logging.Filter maps each French log template (and French words in its
  arguments) to English
- the --diag status line and notifications: module-level ``print`` and ``notify`` in the
  upstream module are replaced by translating wrappers
- calibration window: ``CALIB_TEXT`` and ``SOURCE_NAMES`` are replaced, and the tkinter
  widgets get their ``text`` translated while ``calibrate()`` runs

``tests/test_english.py`` checks that every log template in upstream has a translation,
so an upstream update that adds a message fails the tests instead of showing French.
The web UI is not covered (task T13).
"""

import builtins
import contextlib
import logging
import re

UPSTREAM_LOGGER = "airpods-mouse"

# Exact French log templates in upstream -> English, with the same %-placeholders in order.
LOG_TEMPLATES = {
    "Tentative de connexion : %s (%s)": "Trying to connect: %s (%s)",
    "options socket : %s": "socket options: %s",
    "Canal AAP ouvert avec %s (modèle %s)": "AAP channel open with %s (model %s)",
    "Envoi AAP impossible : %s": "AAP send failed: %s",
    "Capteur devmotion6 (RemoteHID id %d) %s — démarrage": "Sensor devmotion6 (RemoteHID id %d) %s — starting",
    "config.json illisible (%s)": "config.json unreadable (%s)",
    "Réglages rechargés": "Settings reloaded",
    "Profil %s non calibré : lance --calibrate dans cette position":
        "Profile %s is not calibrated: run --calibrate in this position",
    "Position détectée : %s -> source %s": "Detected position: %s -> source %s",
    "Clic %s": "Click %s",
    "Commande inconnue : %s": "Unknown command: %s",
    "Pression tige : %s": "Stem press: %s",
    "Inclinaison %s -> %s": "Tilt %s -> %s",
    "Clic par immobilité": "Dwell click",
    "Interface : http://127.0.0.1:%d": "Web UI: http://127.0.0.1:%d",
    "Interface web indisponible : %s": "Web UI unavailable: %s",
    "Démarrage — mode %s, source %s": "Starting — mode %s, source %s",
    "Connexion impossible (%s) — nouvel essai dans %ss": "Cannot connect (%s) — retrying in %ss",
    "Pas de données de mouvement — relance du flux": "No motion data — restarting the stream",
    "Capteurs non annoncés — reconnexion Bluetooth complète": "Sensors not announced — full Bluetooth reconnect",
    "Canal AAP perdu (%s), reconnexion…": "AAP channel lost (%s), reconnecting…",
    "Arrêté": "Stopped",
    "Lancement du contrôleur en arrière-plan…": "Starting the controller in the background…",
}

# Whole strings shown as notifications, status text, widget labels or log arguments.
PHRASES = {
    # notifications
    "Mode défilement": "Scroll mode",
    "Mode curseur": "Cursor mode",
    "Recentré": "Recentered",
    "Pause": "Paused",
    "Contrôle actif": "Control active",
    "AirPods 3 : capteurs coupés dans le boîtier — sors un écouteur":
        "AirPods 3: sensors are off in the case — take a bud out",
    # mode and source names used as values in messages
    "souris": "mouse",
    "pointeur": "pointer",
    "glisse": "glide",
    "droite": "right",
    "gauche": "left",
    "annoncé": "announced",
    "réannoncé": "re-announced",
    # calibration window
    "Source :": "Source:",
    "tête": "head",
    "boîtier": "case",
    "AirPod en main": "AirPod in hand",
    "Recommencer": "Restart",
    "Connexion aux AirPods…": "Connecting to the AirPods…",
    "Connecté — en attente des mesures…": "Connected — waiting for data…",
    "Mesures reçues": "Receiving data",
    "Aucune mesure (écouteurs portés / boîtier ouvert ?)": "No data (buds in ears / case open?)",
    "✔ Calibration réussie !\nTu peux fermer cette fenêtre.": "✔ Calibration done!\nYou can close this window.",
}

# French fragments inside exception messages and other free text.
FRAGMENTS = {
    "aucun AirPods connecté": "no AirPods connected",
    "canal fermé": "channel closed",
    "relance Bluetooth": "Bluetooth restart",
}

# Formatted strings: (pattern, replacement); groups are translated recursively.
PATTERNS = [
    (re.compile(r"^Mode (souris|pointeur|glisse)$"), lambda m: f"Mode {PHRASES[m[1]]}"),
    (re.compile(r"^Source : (.*)  —  étape (\d+)/(\d+)$"), lambda m: f"Source: {m[1]}  —  step {m[2]}/{m[3]}"),
    (re.compile(r"^Profil enregistré : (.*)$"), lambda m: f"Profile saved: {m[1]}"),
    (re.compile(r"^(.*)   \|   écouteurs : (.*)$", re.S), lambda m: f"{translate(m[1])}   |   buds: {m[2]}"),
    (re.compile(r"^Connexion perdue \((.*)\) — nouvel essai…$"), lambda m: f"Connection lost ({translate(m[1])}) — retrying…"),
]

SOURCE_NAMES_EN = {"head": "head", "case": "case", "hand": "hand"}

CALIB_TEXT_EN = {
    "head": {"still": "Look at the screen and keep still", "yaw": "Turn your head to the LEFT",
             "pitch": "Tilt your head UP", "roll": "Tilt your head towards your RIGHT shoulder",
             "back": "Face the screen again and keep still"},
    "case": {"still": "Lay the open case flat, pointing at the screen", "yaw": "Turn the case to the LEFT",
             "pitch": "Point the case UP", "roll": "Twist the case to the RIGHT (like turning a key)",
             "back": "Point at the screen again and keep still"},
    "hand": {"still": "Hold the AirPod still, pointing at the screen", "yaw": "Turn the AirPod to the LEFT",
             "pitch": "Point the AirPod UP", "roll": "Twist the AirPod to the RIGHT (like turning a key)",
             "back": "Point at the screen again and keep still"},
}

DIAG_WORDS = [(" lacet ", " yaw "), ("  tangage ", "  pitch "), ("  roulis ", "  roll "),
              ("  biais ", "  bias "), ("  éch. ", "  samples ")]


def translate(text):
    """Translate one upstream string to English; unknown text is returned unchanged."""
    if not isinstance(text, str):
        return text
    if text in PHRASES:
        return PHRASES[text]
    for pattern, repl in PATTERNS:
        m = pattern.match(text)
        if m:
            return repl(m)
    for fr, en in FRAGMENTS.items():
        text = text.replace(fr, en)
    return text


def _translate_arg(arg):
    if isinstance(arg, str):
        return translate(arg)
    if isinstance(arg, BaseException):
        s = str(arg)
        t = translate(s)
        return t if t != s else arg
    return arg


class LogTranslator(logging.Filter):
    """Rewrites upstream log records to English before they are formatted."""

    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = LOG_TEMPLATES.get(record.msg, translate(record.msg))
        if isinstance(record.args, tuple):
            record.args = tuple(_translate_arg(a) for a in record.args)
        return True


def english_print(*args, **kwargs):
    """Drop-in for print() inside upstream: translates the --diag status line."""
    if args and isinstance(args[0], str) and args[0].startswith("\r["):
        line = args[0]
        for fr, en in DIAG_WORDS:
            line = line.replace(fr, en)
        args = (line,) + args[1:]
    elif args and isinstance(args[0], str):
        args = (translate(args[0]),) + args[1:]
    builtins.print(*args, **kwargs)


def install(up):
    """Switch the upstream module's user-facing text to English. Safe to call more than once."""
    if getattr(up, "_podsmouse_english", False):
        return
    up._podsmouse_english = True
    up._podsmouse_fr_calib = getattr(up, "CALIB_TEXT", None)
    up.SOURCE_NAMES = dict(SOURCE_NAMES_EN)
    up.CALIB_TEXT = {src: dict(steps) for src, steps in CALIB_TEXT_EN.items()}
    up.print = english_print  # module globals shadow the builtin inside upstream functions
    original_notify = up.notify
    up.notify = lambda cfg, text: original_notify(cfg, translate(text))
    logging.getLogger(UPSTREAM_LOGGER).addFilter(LogTranslator())


@contextlib.contextmanager
def english_tk(tk_module):
    """Translate ``text=`` on tkinter Label/Button/Radiobutton while the block runs."""
    classes = [getattr(tk_module, n) for n in ("Label", "Button", "Radiobutton") if hasattr(tk_module, n)]
    saved_inits = {cls: cls.__init__ for cls in classes}
    misc = tk_module.Misc
    saved_configure = misc.configure

    def fix(kwargs):
        if "text" in kwargs:
            kwargs["text"] = translate(kwargs["text"])
        return kwargs

    def make_init(orig):
        def __init__(self, *args, **kwargs):
            orig(self, *args, **fix(kwargs))
        return __init__

    def configure(self, cnf=None, **kwargs):
        return saved_configure(self, cnf, **fix(kwargs))

    try:
        for cls, orig in saved_inits.items():
            cls.__init__ = make_init(orig)
        misc.configure = misc.config = configure
        yield
    finally:
        for cls, orig in saved_inits.items():
            cls.__init__ = orig
        misc.configure = misc.config = saved_configure
