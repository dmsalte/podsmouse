"""English web UI for the vendored mousepods code, without editing upstream/.

Upstream's web UI (``upstream/ui/index.html`` served by ``upstream/mousepods_web.py``) is in
French. This module translates it at runtime:

- the page: ``HTML_REPLACEMENTS`` turns the upstream HTML into English. The result is written to
  ``ui-en.html`` next to the config file and ``mousepods_web.UI_FILE`` points at it. Because the page is built from
  upstream's current file, an upstream update keeps working; ``tests/test_web_english.py`` fails
  if a replacement no longer matches or new French text appears.
- server data: the label tables in ``mousepods_web`` (models, battery, ear state, controls, HID
  usages, sensor services, calibration steps) are replaced with English ones, and a ``WebUI``
  subclass translates the free text it sends (status line, calibration messages).

The page's JavaScript compares some server values (battery state, the "Name" info label), so
the English page and the English tables must change together. The tests check both.

The English text translates upstream's UI (Copyright 2026 Matteo Gaudioso, Apache-2.0; see NOTICE).
"""

import os

from . import english

# (French, English) substrings of upstream/ui/index.html. Every French string is replaced
# everywhere it occurs. Order matters only where one French string contains another; longer
# strings come first.
HTML_REPLACEMENTS = [
    ('<html lang="fr">', '<html lang="en">'),
    # sidebar
    ('</span>Aperçu</a>', '</span>Overview</a>'),
    ('</span>Mouvement</a>', '</span>Motion</a>'),
    ('</span>Réglages</a>', '</span>Settings</a>'),
    ('</span>Capteurs</a>', '</span>Sensors</a>'),
    ('</span>Journal</a>', '</span>Log</a>'),
    ('</span>Découvertes</a>', '</span>Findings</a>'),
    # overview
    ('<div class="sub" id="ov-sub">Connexion…</div>', '<div class="sub" id="ov-sub">Connecting…</div>'),
    ('<h2>Contrôle</h2>', '<h2>Control</h2>'),
    ('<h3>Curseur</h3>', '<h3>Cursor</h3>'),
    ('data-cmd="recenter">Recentrer</button>', 'data-cmd="recenter">Recenter</button>'),
    ('id="ov-scroll">Mode défilement</button>', 'id="ov-scroll">Scroll mode</button>'),
    ('<button data-v="souris">Souris</button><button data-v="pointeur">Pointeur</button>'
     '<button data-v="glisse">Glisse</button>',
     '<button data-v="souris">Mouse</button><button data-v="pointeur">Pointer</button>'
     '<button data-v="glisse">Glide</button>'),
    ('<button data-v="head">Tête</button><button data-v="case">Boîtier</button>'
     '<button data-v="hand">En main</button>',
     '<button data-v="head">Head</button><button data-v="case">Case</button>'
     '<button data-v="hand">In hand</button>'),
    ("<b>Souris</b> : tourner/incliner (tête, boîtier, AirPod) · <b>Pointeur</b> : viser l'écran comme un laser"
     " · <b>Glisse</b> : boîtier à plat poussé sur la table",
     "<b>Mouse</b>: turn/tilt (head, case, AirPod) · <b>Pointer</b>: aim at the screen like a laser"
     " · <b>Glide</b>: case lying flat, pushed across the table"),
    ('<h2>Liaison</h2>', '<h2>Link</h2>'),
    ('<div class="hint">Mesures / seconde</div>', '<div class="hint">Samples / second</div>'),
    ('<div class="hint">Coupures (&gt;50 ms, 2 s)</div>', '<div class="hint">Gaps (&gt;50 ms, 2 s)</div>'),
    ('<div class="hint">Protocole</div>', '<div class="hint">Protocol</div>'),
    ("<div class=\"hint\">Profil d'axes</div>", '<div class="hint">Axis profile</div>'),
    # motion
    ('<h1>Mouvement</h1><div class="sub">Données brutes et calculées, en direct.</div>',
     '<h1>Motion</h1><div class="sub">Raw and computed data, live.</div>'),
    ("<h3>Orientation (quaternion de l'écouteur) ", "<h3>Orientation (bud quaternion) "),
    ('style="margin-left:auto">Zéro</button>', 'style="margin-left:auto">Zero</button>'),
    ('<span>Vitesse curseur</span>', '<span>Cursor speed</span>'),
    ('<h3>Vitesses angulaires (°/s)</h3>', '<h3>Angular rates (°/s)</h3>'),
    ('</i>Lacet (horizontal)</span>', '</i>Yaw (horizontal)</span>'),
    ('</i>Tangage (vertical)</span>', '</i>Pitch (vertical)</span>'),
    ('</i>Roulis (inclinaison)</span>', '</i>Roll (tilt)</span>'),
    ('<h3>Gyroscope (°/s, repère écouteur)</h3>', '<h3>Gyroscope (°/s, bud frame)</h3>'),
    ('<h3>Gravité (g, repère écouteur)</h3>', '<h3>Gravity (g, bud frame)</h3>'),
    ('<h3>Biais gyroscope</h3>', '<h3>Gyroscope bias</h3>'),
    ('<h3>Accélération (m/s², sans gravité)</h3>', '<h3>Acceleration (m/s², gravity removed)</h3>'),
    ('<h3>Glisse : vitesse estimée (cm/s)</h3>', '<h3>Glide: estimated speed (cm/s)</h3>'),
    # settings
    ("<h1>Réglages</h1><div class=\"sub\">Tout s'applique instantanément.</div>",
     '<h1>Settings</h1><div class="sub">Changes apply immediately.</div>'),
    ('<h3>Sensibilité</h3>', '<h3>Sensitivity</h3>'),
    ('<label>Horizontale</label>', '<label>Horizontal</label>'),
    ('<label>Verticale</label>', '<label>Vertical</label>'),
    ("<label>Inverser l'horizontale</label>", '<label>Invert horizontal</label>'),
    ('<label>Inverser la verticale</label>', '<label>Invert vertical</label>'),
    ('<h2>Mode souris</h2>', '<h2>Mouse mode</h2>'),
    ('<label>Vitesse<small>pixels par degré de rotation</small>', '<label>Speed<small>pixels per degree of rotation</small>'),
    ('<label>Accélération<small>les gestes rapides vont plus loin</small>',
     '<label>Acceleration<small>fast movements go further</small>'),
    ('<label>Zone morte<small>°/s ignorés (stabilité)</small>', '<label>Dead zone<small>°/s ignored (stability)</small>'),
    ('<h2>Mode pointeur</h2>', '<h2>Pointer mode</h2>'),
    ("<label>Amplitude<small>% de l'écran par degré</small>", '<label>Range<small>% of the screen per degree</small>'),
    ('<h2>Mode glisse (boîtier à plat sur la table)</h2>', '<h2>Glide mode (case lying flat on the table)</h2>'),
    ('<label>Vitesse<small>pixels par centimètre glissé</small>', '<label>Speed<small>pixels per centimetre moved</small>'),
    ('<label>Seuil de mouvement<small>m/s² ignorés (bruit)</small>',
     '<label>Motion threshold<small>m/s² ignored (noise)</small>'),
    ("<label>Détection d'arrêt<small>m/s² sous lesquels le boîtier est considéré immobile</small>",
     '<label>Stop detection<small>m/s² below which the case counts as still</small>'),
    ('<label>Inertie<small>secondes ; plus grand = glisse plus longtemps</small>',
     '<label>Inertia<small>seconds; higher = glides for longer</small>'),
    ('<h2>Fluidité</h2>', '<h2>Smoothness</h2>'),
    ('<label>Lissage<small>0 = brut, 1 = très lisse</small>', '<label>Smoothing<small>0 = raw, 1 = very smooth</small>'),
    ("<label>Retard d'affichage<small>secondes ; plus petit = plus réactif</small>",
     '<label>Render delay<small>seconds; lower = more responsive</small>'),
    ('<label>Fréquence capteur<small>µs entre mesures (5000 = 200 Hz)</small>',
     '<label>Sensor rate<small>µs between samples (5000 = 200 Hz)</small>'),
    ('<label>Rafraîchissement curseur<small>images par seconde</small>',
     '<label>Cursor refresh<small>frames per second</small>'),
    ('<h2>Clics</h2>', '<h2>Clicks</h2>'),
    ('<label>Pression sur la tige<small>simple = clic gauche · double = clic droit · triple = défilement'
     ' · long = pause</small>',
     '<label>Stem press<small>single = left click · double = right click · triple = scroll'
     ' · long = pause</small>'),
    ('<label>Inclinaison rapide<small>épaule droite = clic gauche · épaule gauche = clic droit</small>',
     '<label>Quick tilt<small>right shoulder = left click · left shoulder = right click</small>'),
    ("<label>Seuil d'inclinaison<small>degrés</small>", '<label>Tilt threshold<small>degrees</small>'),
    ("<label>Clic par immobilité<small>le curseur clique s'il reste immobile</small>",
     '<label>Dwell click<small>the cursor clicks when it stays still</small>'),
    ("<label>Durée d'immobilité<small>secondes</small>", '<label>Dwell time<small>seconds</small>'),
    ('<label>Vitesse de défilement</label>', '<label>Scroll speed</label>'),
    ('<h2>Système</h2>', '<h2>System</h2>'),
    ("<label>Gyroscope<small>°/s par unité (étalonnage d'échelle)</small>",
     '<label>Gyroscope<small>°/s per unit (scale calibration)</small>'),
    # calibration
    ('<div class="sub">Un profil par modèle et par source (tête, boîtier, en main). Environ 15 secondes.</div>',
     '<div class="sub">One profile per model and source (head, case, in hand). About 15 seconds.</div>'),
    ('<button data-v="souris">Rotation (souris)</button><button data-v="pointeur">Pointeur + coins</button>'
     '<button data-v="glisse">Glisse sur table</button>',
     '<button data-v="souris">Rotation (mouse)</button><button data-v="pointeur">Pointer + corners</button>'
     '<button data-v="glisse">Glide on table</button>'),
    ('id="cal-instr">Prêt à calibrer</div>', 'id="cal-instr">Ready to calibrate</div>'),
    ('id="cal-hint">Le curseur est mis en pause pendant la calibration.</div>',
     'id="cal-hint">The cursor is paused during calibration.</div>'),
    ('id="cal-start">Commencer</button>', 'id="cal-start">Start</button>'),
    ('id="cal-cancel">Annuler</button>', 'id="cal-cancel">Cancel</button>'),
    ('<h2>Profils enregistrés</h2>', '<h2>Saved profiles</h2>'),
    ('<th>Profil</th><th>Contenu</th>', '<th>Profile</th><th>Contents</th>'),
    # sensors
    ('<h1>Capteurs</h1><div class="sub">Services capteurs publiés par les AirPods via Apple RemoteHID'
     ' (HID sur AACP). Interrogez-les et démarrez-les individuellement.</div>',
     '<h1>Sensors</h1><div class="sub">Sensor services published by the AirPods over Apple RemoteHID'
     ' (HID over AACP). Query and start each one individually.</div>'),
    ('<h2>Réponses Get/SetReport</h2>', '<h2>Get/SetReport replies</h2>'),
    ('<th>Il y a</th><th>Type</th><th>Device</th><th>Données</th>', '<th>Age</th><th>Type</th><th>Device</th><th>Data</th>'),
    # AirPods page
    ('<div class="sub">Informations remontées par les écouteurs.</div>',
     '<div class="sub">Information reported by the buds.</div>'),
    ('<h3>Identité</h3>', '<h3>Identity</h3>'),
    ('<h3>État</h3>', '<h3>State</h3>'),
    ('<h2>Réglages internes (opcode 0x09)</h2>', '<h2>Internal settings (opcode 0x09)</h2>'),
    ('<th>ID</th><th>Nom</th><th>Valeur</th>', '<th>ID</th><th>Name</th><th>Value</th>'),
    ('Avancé : envoyer une commande de contrôle. Ces réglages sont stockés dans les AirPods.',
     'Advanced: send a control command. These settings are stored in the AirPods.'),
    ('placeholder="ID (ex. 0x17)"', 'placeholder="ID (e.g. 0x17)"'),
    ('placeholder="valeurs (ex. 0 0 0 0)"', 'placeholder="values (e.g. 0 0 0 0)"'),
    ('>Envoyer</button>', '>Send</button>'),
    ('<h2>Avancé</h2>', '<h2>Advanced</h2>'),
    ('Envoyer un paquet AAP brut (hex). À vos risques.', 'Send a raw AAP packet (hex). At your own risk.'),
    ('id="reconnect">Reconnecter</button>', 'id="reconnect">Reconnect</button>'),
    # log
    ('<h1>Journal</h1><div class="sub">Paquets AAP échangés (1 paquet de mouvement sur 100 affiché).</div>',
     '<h1>Log</h1><div class="sub">AAP packets exchanged (1 in 100 motion packets shown).</div>'),
    ('<h3>Compteurs par opcode</h3>', '<h3>Counts per opcode</h3>'),
    ('<th>Heure</th><th>Sens</th><th>Op</th><th>Long.</th><th>Données</th>',
     '<th>Time</th><th>Direction</th><th>Op</th><th>Length</th><th>Data</th>'),
    # findings
    ("<h1>Découvertes</h1><div class=\"sub\">Ce qu'on a appris en rétro-ingénierie — détails dans"
     " REVERSE_ENGINEERING.md.</div>",
     '<h1>Findings</h1><div class="sub">What reverse engineering taught us — details in'
     ' REVERSE_ENGINEERING.md.</div>'),
    ('<li><b>Accélération utilisateur</b> [38:44] (gravité retirée, ~1000 = 1 g) : bruit ≈ 0,02 g au repos'
     ' — assez propre pour le mode Glisse avec remise à zéro à chaque arrêt.</li>',
     '<li><b>User acceleration</b> [38:44] (gravity removed, ~1000 = 1 g): noise ≈ 0.02 g at rest'
     ' — clean enough for Glide mode with a reset at every stop.</li>'),
    ('<li><b>MTU L2CAP</b> : avec 672 octets (défaut Linux), les AirPods 3 cachent leurs capteurs ;'
     ' à <code>2582</code> (comme iOS) ils publient <i>devmotion6, accel, gyro, cma, kadabra</i>.</li>',
     '<li><b>L2CAP MTU</b>: with 672 bytes (Linux default) AirPods 3 hide their sensors;'
     ' at <code>2582</code> (like iOS) they publish <i>devmotion6, accel, gyro, cma, kadabra</i>.</li>'),
    ('<li><b>Apple RemoteHID</b> (canal RTBuddy <code>0x800</code>) : chaque capteur est un périphérique HID'
     ' virtuel. En-tête de sous-paquet u32 : deviceID (7 bits), longueur (10 bits), type (3 bits).</li>',
     '<li><b>Apple RemoteHID</b> (RTBuddy channel <code>0x800</code>): every sensor is a virtual HID'
     ' device. Sub-packet header u32: deviceID (7 bits), length (10 bits), type (3 bits).</li>'),
    ('<li><b>HostConnect</b> <code>00 gg 00 00 | 00 02 00 00</code> → les AirPods publient leurs capteurs'
     ' (DeviceConnect + plist + descripteur HID).</li>',
     '<li><b>HostConnect</b> <code>00 gg 00 00 | 00 02 00 00</code> → the AirPods publish their sensors'
     ' (DeviceConnect + plist + HID descriptor).</li>'),
    ('<li><b>SetReport feature 1 = Report Interval (µs)</b> sur devmotion6 → flux de mouvement jusqu\'à'
     ' ~200 Hz.</li>',
     '<li><b>SetReport feature 1 = Report Interval (µs)</b> on devmotion6 → motion stream up to'
     ' ~200 Hz.</li>'),
    ('<li>Bloc de 58 octets commun aux AirPods 3 et Pro : quaternion Q15 [20:26], gyroscope [26:32]'
     ' (~0,122 °/s par unité), accélération [38:44], gravité [44:50] (~1000 = 1 g).</li>',
     '<li>58-byte block shared by AirPods 3 and Pro: Q15 quaternion [20:26], gyroscope [26:32]'
     ' (~0.122 °/s per unit), acceleration [38:44], gravity [44:50] (~1000 = 1 g).</li>'),
    ('<li>AirPods Pro 2 : protocole <i>SensorDataWX</i> (protobuf, <code>0x100000</code>) — ACTIVITY(14)'
     ' puis DEVMOTION6(16).</li>',
     '<li>AirPods Pro 2: <i>SensorDataWX</i> protocol (protobuf, <code>0x100000</code>) — ACTIVITY(14)'
     ' then DEVMOTION6(16).</li>'),
    # script: labels and toasts
    ('const SRC={head:"Tête",case:"Boîtier",hand:"En main",auto:"Auto"};',
     'const SRC={head:"Head",case:"Case",hand:"In hand",auto:"Auto"};'),
    ('inp.onchange=()=>setCfg(mkObj(k,inp.checked),"Enregistré");', 'inp.onchange=()=>setCfg(mkObj(k,inp.checked),"Saved");'),
    ('toast("Calibration lancée")', 'toast("Calibration started")'),
    ('toast("Calibration annulée")', 'toast("Calibration cancelled")'),
    ('toast("ID invalide")', 'toast("Invalid ID")'),
    ('toast("Commande envoyée")', 'toast("Command sent")'),
    ('toast("Paquet envoyé")', 'toast("Packet sent")'),
    ('toast("Reconnexion…")', 'toast("Reconnecting…")'),
    ('ok?"Mesures en direct":', 'ok?"Live data":'),
    ('t.paused?"En pause":(t.calib&&t.calib.active?"Calibration":"Actif")',
     't.paused?"Paused":(t.calib&&t.calib.active?"Calibration":"Active")'),
    ('({souris:"Mode souris",pointeur:"Mode pointeur",glisse:"Mode glisse"})[t.mode]} · source ${SRC[t.source]}'
     '${t.scroll?" · défilement":""}',
     '({souris:"Mouse mode",pointeur:"Pointer mode",glisse:"Glide mode"})[t.mode]} · source ${SRC[t.source]}'
     '${t.scroll?" · scrolling":""}'),
    ('t.paused?"Reprendre":"Pause"', 't.paused?"Resume":"Pause"'),
    ("`Détecté : ${({ear:\"écouteurs portés\",case:\"écouteurs dans le boîtier\",out:\"écouteur hors de"
     " l'oreille\"})[t.place]||\"—\"} → source ${SRC[t.source]}`",
     '`Detected: ${({ear:"buds in ears",case:"buds in the case",out:"bud out of the ear"})[t.place]||"—"}'
     ' → source ${SRC[t.source]}`'),
    ('b.state==="en charge"', 'b.state==="charging"'),
    ('b.state==="déconnecté"', 'b.state==="disconnected"'),
    ('<b>Oreilles</b>', '<b>Ears</b>'),
    ("'<div class=\"card empty\">En attente des AirPods…</div>'", "'<div class=\"card empty\">Waiting for the AirPods…</div>'"),
    ('"Corrigé automatiquement (appareil immobile détecté)":"En attente d\'un moment d\'immobilité…"',
     '"Corrected automatically (device held still)":"Waiting for a moment of stillness…"'),
    ('const FL={souris:"Rotation",pointeur:"Pointeur + coins",glisse:"Glisse sur table"};',
     'const FL={souris:"Rotation",pointeur:"Pointer + corners",glisse:"Glide on table"};'),
    ('`Profil « ${c.key} » enregistré et appliqué.`:`${FL[c.flow]} · source ${SRC[c.source]} — étape'
     ' ${Math.min(c.index+1,c.total)}/${c.total}`',
     '`Profile "${c.key}" saved and applied.`:`${FL[c.flow]} · source ${SRC[c.source]} — step'
     ' ${Math.min(c.index+1,c.total)}/${c.total}`'),
    ('/Nom/.test(i.label)?"AirPods":/série|Serial/i.test(i.label)',
     '/^Name$/.test(i.label)?"AirPods":/serial/i.test(i.label)'),
    ('(s.info||[]).find(i=>i.label==="Nom")', '(s.info||[]).find(i=>i.label==="Name")'),
    (':"Recherche des AirPods…";', ':"Looking for the AirPods…";'),
    ('`<span class="pill o">À calibrer</span>`', '`<span class="pill o">Needs calibration</span>`'),
    ('`glisse · droite [${f(p.right)}] · avant [${f(p.fwd)}]`:`axe latéral [${f(p.lat)}] · lacet ${p.yaw_sign}'
     ' · roulis ${p.roll_sign}${p.range?` · coins ',
     '`glide · right [${f(p.right)}] · forward [${f(p.fwd)}]`:`lateral axis [${f(p.lat)}] · yaw ${p.yaw_sign}'
     ' · roll ${p.roll_sign}${p.range?` · corners '),
    ('class="empty">Aucun profil</td>', 'class="empty">No profiles</td>'),
    ('[["Adresse",s.addr],["Modèle",s.model],["Product ID","0x"+(s.pid||"")],["Protocole capteurs",s.protocol],'
     '["Intervalle capteur",(s.interval_us||"—")+" µs"],',
     '[["Address",s.addr],["Model",s.model],["Product ID","0x"+(s.pid||"")],["Sensor protocol",s.protocol],'
     '["Sensor interval",(s.interval_us||"—")+" µs"],'),
    ('["Écouteurs",(s.ear||[]).join(" · ")],...(s.battery||[]).map(b=>["Batterie "+b.part.toLowerCase(),'
     'b.level+" % · "+b.state]),["Contrôleur actif depuis",Math.round((s.uptime||0)/60)+" min"]]',
     '["Buds",(s.ear||[]).join(" · ")],...(s.battery||[]).map(b=>["Battery "+b.part.toLowerCase(),'
     'b.level+" % · "+b.state]),["Controller uptime",Math.round((s.uptime||0)/60)+" min"]]'),
    ("'<div class=\"card empty\">Aucun service RemoteHID (AirPods Pro : protocole SensorDataWX, sans services"
     " HID).</div>'",
     "'<div class=\"card empty\">No RemoteHID services (AirPods Pro: SensorDataWX protocol, no HID"
     " services).</div>'"),
    ('\'<span class="pill g">utilisé pour la souris</span>\'', '\'<span class="pill g">used for the mouse</span>\''),
    ('` · rapport max ${sv.max_report} o`', '` · max report ${sv.max_report} B`'),
    ('<th>Rapport</th><th>ID</th><th>Bits</th><th>Usages</th>', '<th>Report</th><th>ID</th><th>Bits</th><th>Usages</th>'),
    ('<span>Rapports reçus</span>', '<span>Reports received</span>'),
    ('` · dernier il y a ${sv.last_age} s`', '` · last ${sv.last_age} s ago`'),
    ('\'start\')">Démarrer</button>', '\'start\')">Start</button>'),
    ('\'stop\')">Arrêter</button>', '\'stop\')">Stop</button>'),
    ('>Lire F${r.id}</button>', '>Read F${r.id}</button>'),
    ('action==="get"?"Lecture demandée":action==="start"?"Flux démarré":"Flux arrêté"',
     'action==="get"?"Read requested":action==="start"?"Stream started":"Stream stopped"'),
    ('textContent="Contrôleur arrêté"', 'textContent="Controller stopped"'),
]

# Server-side label tables in mousepods_web, by attribute name.
MODELS_EN = {"2013": "AirPods (3rd generation)", "2014": "AirPods Pro (2nd generation)",
             "200e": "AirPods Pro", "200f": "AirPods (2nd generation)", "2002": "AirPods (1st generation)",
             "200a": "AirPods Max", "2019": "AirPods 4", "201b": "AirPods 4 (ANC)",
             "2024": "AirPods Pro 2 (USB-C)", "2027": "AirPods Pro 3", "202d": "AirPods Max (USB-C)"}
INFO_LABELS_EN = ["Name", "Model", "Manufacturer", "Serial number", "Firmware", "Firmware (2)", "Hardware",
                  "Updater", "Left serial number", "Right serial number", "Marketing version"]
CONTROL_NAMES_EN = {0x01: "Microphone mode", 0x05: "Button send mode", 0x0A: "Ear detection",
                    0x0C: "Single click mode", 0x0D: "Noise control", 0x0E: "One-bud ANC",
                    0x14: "Listening mode configs", 0x16: "Press and hold (action)",
                    0x17: "Double-click interval", 0x18: "Press and hold interval", 0x1A: "Listening modes",
                    0x1B: "One-bud ANC (mode)", 0x1C: "Tone volume", 0x1D: "Volume swipe interval",
                    0x1F: "Call management", 0x20: "Volume swipe", 0x23: "Adaptive volume",
                    0x24: "Software mute", 0x25: "Conversation awareness", 0x28: "Hearing aid",
                    0x39: "Raw gestures (reported to host)"}
BATTERY_PART_EN = {0x01: "Single", 0x02: "Right", 0x04: "Left", 0x08: "Case"}
BATTERY_STATE_EN = {0x00: "unknown", 0x01: "charging", 0x02: "on battery", 0x04: "disconnected"}
EAR_STATE_EN = {0: "in ear", 1: "out of ear", 2: "in case", 3: "absent"}
USAGE_NAMES_EN = {(0x20, 0x30E): "Report Interval", (0x20, 0x31B): "Report Latency",
                  (0x20, 0x31A): "Max FIFO Events", (0x20, 0x73): "3D accelerometer", (0x20, 0x7A): "3D gyroscope",
                  (0x20, 0x453): "Accel. X", (0x20, 0x454): "Accel. Y", (0x20, 0x455): "Accel. Z",
                  (0x20, 0x457): "Angular rate X", (0x20, 0x458): "Angular rate Y", (0x20, 0x459): "Angular rate Z",
                  (0x20, 0x434): "Timestamp", (0x20, 0x316): "Reporting State", (0x20, 0x319): "Power State"}
SERVICE_DESC_EN = {"devmotion6": "Fused motion (attitude, gyro, gravity, acceleration)",
                   "accel": "Accelerometer (standard HID sensor)", "gyro": "Gyroscope (standard HID sensor)",
                   "cma": "CoreMotion Activity", "kadabra": "\"Kadabra\" sensor (unknown)",
                   "iedrelay": "IED relay (unknown)", "neorelay": "NEO relay (unknown)",
                   "mando": "Mando (unknown)"}
AIM_TEXT_EN = {"aim_center": "Aim at the CENTRE of the screen and keep still",
               "aim_tl": "Aim at the TOP-LEFT corner of the screen and keep still",
               "aim_br": "Aim at the BOTTOM-RIGHT corner of the screen and keep still"}
GLIDE_TEXT_EN = {"flat": "Lay the case FLAT on the table and keep it still",
                 "slide_right": "SLIDE it to the RIGHT (≈ 10 cm), then stop",
                 "slide_fwd": "SLIDE it FORWARD, away from you (≈ 10 cm), then stop",
                 "flat_back": "Keep still"}

TABLES = {
    "MODELS": MODELS_EN, "INFO_LABELS": INFO_LABELS_EN, "CONTROL_NAMES": CONTROL_NAMES_EN,
    "BATTERY_PART": BATTERY_PART_EN, "BATTERY_STATE": BATTERY_STATE_EN, "EAR_STATE": EAR_STATE_EN,
    "USAGE_NAMES": USAGE_NAMES_EN, "SERVICE_DESC": SERVICE_DESC_EN, "AIM_TEXT": AIM_TEXT_EN,
    "GLIDE_TEXT": GLIDE_TEXT_EN,
}

# Free text the web server sends (status line, calibration messages, report kinds, labels).
PHRASES = {
    "Démarrage…": "Starting…",
    "Connecté": "Connected",
    "Connexion perdue — reconnexion…": "Connection lost — reconnecting…",
    "Calibration réussie": "Calibration done",
    "Les coins ne correspondent pas aux directions calibrées : recommence la visée (centre, haut-gauche, bas-droit).":
        "The corners do not match the calibrated directions: aim again (centre, top-left, bottom-right).",
    "entrée": "input",
    "sortie": "output",
    "inconnu": "unknown",
    "autre": "other",
}

STATUS_PREFIXES = [("Recherche des AirPods… (", "Looking for the AirPods… (")]


def translate(text):
    """Translate one string sent by the web server; unknown text is returned unchanged."""
    if not isinstance(text, str):
        return text
    if text in PHRASES:
        return PHRASES[text]
    for fr, en in STATUS_PREFIXES:
        if text.startswith(fr):
            return en + english.translate(text[len(fr):])
    if text.startswith("Champ "):
        return "Field " + text[len("Champ "):]
    return english.translate(text)


def translate_html(html):
    """Return upstream's UI page in English. Replacements that do not match are skipped."""
    for fr, en in HTML_REPLACEMENTS:
        html = html.replace(fr, en)
    return html


def english_webui_class(base):
    """Subclass of upstream WebUI that sends English free text to the page."""

    class EnglishWebUI(base):
        def telemetry(self):
            data = super().telemetry()
            data["status"] = translate(data.get("status"))
            calib = data.get("calib")
            if calib:
                calib["text"] = translate(calib.get("text"))
                calib["message"] = translate(calib.get("message"))
            return data

        def state(self):
            data = super().state()
            for item in data.get("info") or []:
                item["label"] = translate(item.get("label"))
            for svc in data.get("services") or []:
                for report in svc.get("reports") or []:
                    report["kind"] = translate(report.get("kind"))
            data["counts"] = {translate(k): v for k, v in (data.get("counts") or {}).items()}
            return data

    EnglishWebUI.__name__ = EnglishWebUI.__qualname__ = base.__name__
    return EnglishWebUI


UI_FILENAME = "ui-en.html"


def install(web, out_dir):
    """Switch the upstream web UI module to English. Safe to call more than once.

    The English page is written to ``out_dir/ui-en.html`` (the config directory in
    ``podsmouse.main``) and rewritten on every start, so nothing is left behind.
    """
    if getattr(web, "_podsmouse_english", False):
        return
    with open(web.UI_FILE, encoding="utf-8") as f:
        html = translate_html(f.read())
    path = os.path.join(os.fspath(out_dir), UI_FILENAME)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, path)
    for name, table in TABLES.items():
        setattr(web, name, type(table)(table))
    web.UI_FILE = path
    web.WebUI = english_webui_class(web.WebUI)
    web._podsmouse_english = True
