"""
Survey Sentence Generator — PySide6 native Windows edition
Tap phrase buttons to build a description, then GO types it automatically.

Dependencies: pip install pyside6 pyautogui pyperclip openai qrcode
"""
import http.server
import json
import logging
import os
import socket
import socketserver as _sserver
import sys
import threading

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QLabel, QPushButton, QTextEdit, QLineEdit,
    QScrollArea, QGridLayout, QVBoxLayout, QHBoxLayout, QFrame,
    QSizePolicy, QMessageBox, QInputDialog,
    QDoubleSpinBox, QSpinBox, QCheckBox, QStackedWidget,
)

try:
    import pyautogui
    import pyperclip
    DEPS_OK = True
except ImportError:
    DEPS_OK = False

try:
    from api_keys import GROQ_API_KEY
except ImportError:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

try:
    from openai import OpenAI as _OpenAI
    AI_OK = True
except ImportError:
    AI_OK = False

try:
    import qrcode as _qrcode_lib
    QR_OK = True
except ImportError:
    QR_OK = False

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "SurveySentenceGenerator",
)
os.makedirs(BASE_DIR, exist_ok=True)

LOG_FILE      = os.path.join(BASE_DIR, "survey_tool.log")
PHRASES_FILE  = os.path.join(BASE_DIR, "phrases.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
USAGE_FILE    = os.path.join(BASE_DIR, "usage.json")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("survey")

DEFAULT_SETTINGS = {
    "delay": 1.0,
    "clear_after_go": True,
    "font_size": 15,
    "geometry": "1920x1200",
    "dark_mode": False,
}

DEFAULT_PHRASES = {
    "categories": [
        {
            "name": "Numbers",
            "cols": 5,
            "phrases": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
        },
        {
            "name": "Observations",
            "phrases": [
                "No significant features have been observed.",
                "Vegetation obscuring observations of the stem and base.",
                "Vegetation obscuring observations of the stems and bases.",
                "Dimensions recorded are the largest represented within the group.",
                "Ivy concealing observations of the stem and base.",
                "Further investigation required to confirm structural integrity.",
                "Observations of the base limited by dense ground vegetation.",
            ],
        },
        {
            "name": "Crown",
            "phrases": [
                "Crown height has been raised to its current dimensions.",
                "Crown height has been pruned to its current dimensions.",
                "Historically pruned to raise the crown height to its current dimensions.",
                "Pruned to raise the crown height to its current dimensions.",
                "Dead wood in the crown up to 100mm diameter x 5m length.",
                "Dead wood in the crown up to 150mm diameter x 5m length.",
                "Dead wood in the crown up to 400mm diameter x 10m length.",
                "Die back of the crown density by approximately 20%.",
                "Up to 2m length die back centrally to the upper crown.",
                "Crown height over the track has been raised to 5m from ground level.",
                "Crown presents approximately 30% of expected crown density.",
                "Asymmetrical crown shape due to presence of partner trees.",
            ],
        },
        {
            "name": "Condition",
            "phrases": [
                "Dead tree.",
                "Tree in decline.",
                "Single tree densely clad with ivy.",
                "Ivy clad dead monolith stem.",
                "Approximately 10% of the crown has been colonised with mistletoe.",
                "Diminished leaf size and foliage density. Tree in decline.",
                "Multiple stem bleeds from the base up to 2m from ground level.",
                "Multiple ganoderma sp fungal fruit bodies at the base.",
                "Low foliage density by approximately 50%.",
                "Group of approximately twelve trees in varying stages of death and decline.",
                "Areas of dysfunctional bark at the base.",
                "1m area of exposed sap wood to the stem at 2m from ground level.",
            ],
        },
        {
            "name": "Groups",
            "phrases": [
                "Group comprising of",
                "Mature orchard comprising of approximately",
                "Mixed scrub and broadleaf.",
                "Mixed woodland group comprising of",
                "Understory shrub group comprising of",
                "Historically pruned to maintain crown shape and form.",
                "Scaffold bar providing support for low stem.",
                "Fork brace fitted at 6m from ground level.",
                "Low branch in contact with adjacent built structure.",
                "Crown height raised over roadside.",
                "Grape vine is colonising the crown.",
            ],
        },
        {
            "name": "Species",
            "phrases": [
                "Sycamore", "Ash", "Field maple", "Hazel", "Hawthorn",
                "Silver birch", "Wild cherry", "Hornbeam", "Yew", "Elm",
                "Common walnut", "Goat willow", "Aspen", "Magnolia sp",
                "Malus sp", "Prunus sp", "Norway maple", "Leyland cypress",
                "Common pear", "Judas tree", "Snake bark maple", "Japanese maple",
                "Indian bean tree", "Cockspur hawthorn", "Himalayan birch",
                "Sweet bay", "Turkey oak", "Pink hawthorn", "Mountain ash",
                "Dog wood", "Cherry laurel", "Viburnum sp", "Red hazel",
                "Lilac", "Hebe sp", "Loquat",
            ],
        },
    ]
}

# ── Light palette ──────────────────────────────────────────────────────────────
LT = dict(
    bg="#FFFFFF", surface="#F1F5F9",
    hdr="#1E3A5F", hdr_h="#2D4E7A",
    text="#0F172A", text2="#1E293B", text3="#334155",
    border="#CBD5E1", hover="#E2E8F0",
    btn_bg="#FFFFFF", btn_hov="#E8EDF3",
    green="#059669", green_d="#047857", green_l="#ECFDF5", green_m="#A7F3D0",
    danger_bg="#FEF2F2", danger_fg="#DC2626", danger_hd="#FEE2E2",
    info_bg="#EFF6FF", info_fg="#2563EB", info_hd="#DBEAFE", info_dk="#1D4ED8",
    edit_bg="#FFFBEB", edit_bd="#D97706", edit_act="#F59E0B",
    weight="normal",
)

# ── Dark / Field palette ───────────────────────────────────────────────────────
DK = dict(
    bg="#0D1117", surface="#161B22",
    hdr="#010409", hdr_h="#21262D",
    text="#FFFFFF", text2="#FFFFFF", text3="#E6EDF3",
    border="#30363D", hover="#21262D",
    btn_bg="#161B22", btn_hov="#21262D",
    green="#238636", green_d="#2EA043", green_l="#0D2119", green_m="#0F2D1F",
    danger_bg="#2D1318", danger_fg="#F85149", danger_hd="#3D1F24",
    info_bg="#0D2137", info_fg="#58A6FF", info_hd="#1A3155", info_dk="#388BFD",
    edit_bg="#2D1C00", edit_bd="#BB8009", edit_act="#BB8009",
    weight="bold",
)

CAT_COLORS = [
    ("#E0F2FE", "#0369A1", "#0C4A6E", "#38BDF8"),
    ("#D1FAE5", "#065F46", "#022C22", "#34D399"),
    ("#FEF3C7", "#92400E", "#451A03", "#FCD34D"),
    ("#FEE2E2", "#991B1B", "#450A0A", "#F87171"),
    ("#EDE9FE", "#4C1D95", "#2E1065", "#A78BFA"),
    ("#FCE7F3", "#831843", "#500724", "#F472B6"),
    ("#CCFBF1", "#134E4A", "#042F2E", "#5EEAD4"),
    ("#FFEDD5", "#7C2D12", "#431407", "#FB923C"),
]

GROK_BASE_URL = "https://api.groq.com/openai/v1"
GROK_MODEL    = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

APP_VERSION  = "2.0.0"
GITHUB_OWNER = "011-sam-110"
GITHUB_REPO  = "Treez"

# ── Mobile web UI served to the phone ─────────────────────────────────────────
_MOBILE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Survey Input</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden}
body{display:flex;flex-direction:column;background:#0D1117;color:#E6EDF3;
     font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
#hdr{background:#161B22;border-bottom:1px solid #30363D;padding:12px 16px;
     display:flex;align-items:center;gap:10px;flex-shrink:0}
#dot{width:9px;height:9px;border-radius:50%;background:#f85149;transition:background .3s;flex-shrink:0}
#dot.on{background:#3fb950}
#hdr h1{font-size:16px;font-weight:600;flex:1}
#sync{font-size:12px;color:#8B949E;white-space:nowrap}
#ta{flex:1;background:#0D1117;color:#E6EDF3;border:none;outline:none;
    resize:none;padding:16px;font-size:19px;line-height:1.6;width:100%;
    -webkit-appearance:none}
#ftr{background:#161B22;border-top:1px solid #30363D;padding:10px 14px;
     display:flex;gap:10px;flex-shrink:0}
.btn{flex:1;padding:15px;font-size:17px;font-weight:700;border:none;
     border-radius:8px;cursor:pointer;-webkit-tap-highlight-color:transparent}
#bGo{background:#238636;color:#fff}
#bGo:active{background:#2ea043}
#bClear{background:#21262D;color:#E6EDF3;flex:0 0 90px}
#bClear:active{background:#30363D}
</style>
</head>
<body>
<div id="hdr">
  <div id="dot"></div>
  <h1>Survey Input</h1>
  <span id="sync">connecting…</span>
</div>
<textarea id="ta" autocomplete="off" autocorrect="off"
  autocapitalize="off" spellcheck="false"
  placeholder="Tap to type…"></textarea>
<div id="ftr">
  <button class="btn" id="bClear" onclick="doClear()">Clear</button>
  <button class="btn" id="bGo"    onclick="doGo()">GO ›</button>
</div>
<script>
var ta=document.getElementById('ta'),dot=document.getElementById('dot'),sync=document.getElementById('sync');
var ver=0,typing=false,timer,ptimer;
ta.addEventListener('input',function(){
  typing=true;clearTimeout(timer);
  timer=setTimeout(function(){typing=false;push();},700);
});
function push(){
  fetch('/update',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({text:ta.value})})
  .then(r=>r.json()).then(d=>{ver=d.version;dot.className='on';sync.textContent='synced';})
  .catch(()=>{dot.className='';sync.textContent='offline';});
}
function poll(){
  if(typing){ptimer=setTimeout(poll,600);return;}
  fetch('/state?v='+ver)
  .then(r=>r.json()).then(d=>{
    dot.className='on';
    if(d.version!==ver){ver=d.version;ta.value=d.text;sync.textContent='updated';}
    else{sync.textContent='live';}
    ptimer=setTimeout(poll,600);
  })
  .catch(()=>{dot.className='';sync.textContent='reconnecting…';ptimer=setTimeout(poll,2000);});
}
function doClear(){ta.value='';push();}
function doGo(){push();fetch('/go',{method:'POST'});}
poll();
</script>
</body>
</html>"""


# ── Auto-updater ───────────────────────────────────────────────────────────────

def _fetch_latest_release():
    import urllib.request
    import json as _json
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "SurveySentenceGenerator"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = _json.loads(r.read())
    tag     = data.get("tag_name", "").lstrip("v")
    assets  = data.get("assets", [])
    exe_url = next((a["browser_download_url"] for a in assets if a["name"].endswith(".exe")), None)
    return tag, exe_url


def _version_newer(remote: str, local: str) -> bool:
    def t(v):
        return tuple(int(x) for x in v.split(".") if x.isdigit())
    try:
        return t(remote) > t(local)
    except Exception:
        return False


def _perform_update(exe_url: str):
    import urllib.request
    import subprocess
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "Treez_update.exe")
    log.info("Downloading update to %s", tmp)
    with urllib.request.urlopen(exe_url, timeout=120) as r, open(tmp, "wb") as f:
        f.write(r.read())
    current_exe = sys.executable
    bat_path = os.path.join(tempfile.gettempdir(), "treez_update.bat")
    bat = (
        "@echo off\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        f'move /y "{tmp}" "{current_exe}"\r\n'
        f'start "" "{current_exe}"\r\n'
        'del "%~f0"\r\n'
    )
    with open(bat_path, "w") as f:
        f.write(bat)
    subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
    sys.exit(0)


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return json.loads(json.dumps(default))


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _is_online() -> bool:
    for host, port in [("8.8.8.8", 53), ("1.1.1.1", 53), ("8.8.8.8", 80)]:
        try:
            s = socket.create_connection((host, port), timeout=3)
            s.close()
            return True
        except OSError:
            continue
    return False


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _draw_qr_pixmap(url: str, size: int) -> "QPixmap | None":
    if not QR_OK:
        return None
    qr = _qrcode_lib.QRCode(
        error_correction=_qrcode_lib.constants.ERROR_CORRECT_M,
        box_size=1, border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n   = len(matrix)
    cell = max(1, size // n)
    px  = QPixmap(n * cell, n * cell)
    px.fill(QColor("#FFFFFF"))
    painter = QPainter(px)
    painter.setPen(Qt.NoPen)
    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if val:
                painter.fillRect(c * cell, r * cell, cell, cell, QColor("#000000"))
    painter.end()
    return px


_CF_EXE = os.path.join(BASE_DIR, "cloudflared.exe")
_CF_DL  = ("https://github.com/cloudflare/cloudflared/releases/latest"
           "/download/cloudflared-windows-amd64.exe")
_CF_URL_RE = __import__("re").compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


def _find_cloudflared() -> "str | None":
    import shutil
    if os.path.exists(_CF_EXE):
        return _CF_EXE
    return shutil.which("cloudflared") or shutil.which("cloudflared.exe")


def _download_cloudflared(on_progress) -> str:
    import urllib.request
    on_progress(0)
    with urllib.request.urlopen(_CF_DL, timeout=60) as resp:
        total    = int(resp.headers.get("Content-Length") or 0)
        received = 0
        chunk    = 65536
        with open(_CF_EXE, "wb") as f:
            while True:
                data = resp.read(chunk)
                if not data:
                    break
                f.write(data)
                received += len(data)
                if total:
                    on_progress(int(received / total * 100))
    on_progress(100)
    return _CF_EXE


_CF_TIMEOUT = 90  # seconds to wait for tunnel URL before giving up


def _launch_cf_tunnel(port: int, on_url, on_error) -> "subprocess.Popen":
    import subprocess, time
    cf = _find_cloudflared()
    log.info("Launching cloudflared tunnel on port %d  (exe: %s)", port, cf)
    proc = subprocess.Popen(
        [cf, "--no-autoupdate", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    log.info("cloudflared PID %d started", proc.pid)

    def _read():
        deadline = time.monotonic() + _CF_TIMEOUT
        try:
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    log.info("[cloudflared] %s", line)
                m = _CF_URL_RE.search(line)
                if m:
                    log.info("Tunnel URL obtained: %s", m.group())
                    on_url(m.group())
                    return
                if time.monotonic() > deadline:
                    log.error("Tunnel timed out after %ds without a URL", _CF_TIMEOUT)
                    proc.kill()
                    on_error(f"Timed out after {_CF_TIMEOUT}s — no URL received")
                    return
            log.warning("cloudflared stdout closed without a URL")
            on_error("Tunnel closed without providing a URL")
        except Exception as exc:
            log.error("Tunnel read error: %s", exc)
            on_error(str(exc))

    threading.Thread(target=_read, daemon=True).start()
    return proc


# ── Mobile HTTP server ─────────────────────────────────────────────────────────

class _MobileHTTPServer(_sserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

    def __init__(self, addr, handler, ms):
        super().__init__(addr, handler)
        self.ms = ms


class _MobileHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = _MOBILE_HTML.encode("utf-8")
            self._respond(200, "text/html; charset=utf-8", body)
        elif self.path.startswith("/state"):
            text, version = self.server.ms.get_state()
            body = json.dumps({"text": text, "version": version}).encode()
            self._respond(200, "application/json", body)
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length)
        if self.path == "/update":
            try:
                data    = json.loads(raw)
                version = self.server.ms.phone_update(data.get("text", ""))
                self._respond(200, "application/json",
                              json.dumps({"version": version}).encode())
            except Exception:
                self.send_error(400)
        elif self.path == "/go":
            self.server.ms.phone_go()
            self._respond(200, "application/json", b"{}")
        else:
            self.send_error(404)

    def _respond(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


class MobileServer:
    def __init__(self, win: "MainWindow"):
        self.win       = win
        self._text     = win.sentence_text.toPlainText()
        self._version  = 0
        self._lock     = threading.Lock()
        self._cf_proc  = None
        self._httpd    = _MobileHTTPServer(("", 0), _MobileHandler, self)
        self.port      = self._httpd.server_address[1]
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
        log.info("Mobile server started on port %d", self.port)

    def stop(self):
        if self._cf_proc and self._cf_proc.poll() is None:
            self._cf_proc.terminate()
            self._cf_proc = None
        self._httpd.shutdown()
        log.info("Mobile server stopped")

    def get_state(self):
        with self._lock:
            return self._text, self._version

    def set_text(self, text: str):
        with self._lock:
            if self._text == text:
                return
            self._text    = text
            self._version += 1

    def phone_update(self, text: str) -> int:
        with self._lock:
            self._text    = text
            self._version += 1
            v = self._version
        QTimer.singleShot(0, self.win, lambda t=text: self.win._apply_mobile_text(t))
        return v

    def phone_go(self):
        QTimer.singleShot(0, self.win, self.win._go)


# ── Qt stylesheet builder ──────────────────────────────────────────────────────

def _qss(p: dict) -> str:
    return f"""
    QMainWindow, QDialog {{ background: {p['bg']}; }}
    QWidget {{ background: {p['bg']}; color: {p['text']}; font-family: "Segoe UI"; }}

    /* scrollbars */
    QScrollBar:vertical {{
        background: {p['surface']}; width: 8px; border-radius: 4px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p['border']}; border-radius: 4px; min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p['text3']}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

    /* sentence text box */
    QTextEdit#sentence {{
        background: {p['btn_bg']}; color: {p['text']};
        border: 1px solid {p['border']};
        padding: 10px 14px;
        font-size: 16px;
        font-weight: {'bold' if p['weight'] == 'bold' else 'normal'};
    }}

    /* status bar */
    QStatusBar {{ background: {p['surface']}; color: {p['text3']}; font-size: 10px; }}
    QStatusBar::item {{ border: none; }}

    /* generic plain frames used as separators */
    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        color: {p['border']};
    }}
    """


# ── Word-wrapping clickable label used for phrase buttons ──────────────────────

class PhraseButton(QLabel):
    clicked = Signal()

    def __init__(self, text: str, bg: str, fg: str, hover_bg: str, hover_fg: str,
                 font_size: int = 14, bold: bool = False, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setCursor(Qt.PointingHandCursor)
        weight = "bold" if bold else "normal"
        pad    = "16px 20px"
        self._ss_normal  = (f"background:{bg};color:{fg};padding:{pad};"
                            f"border:1px solid {bg};font-size:{font_size}px;"
                            f"font-weight:{weight};font-family:'Segoe UI';")
        self._ss_hover   = (f"background:{hover_bg};color:{hover_fg};padding:{pad};"
                            f"border:1px solid {bg};font-size:{font_size}px;"
                            f"font-weight:{weight};font-family:'Segoe UI';")
        self._ss_pressed = (f"background:{hover_fg};color:{hover_bg};padding:{pad};"
                            f"border:1px solid {bg};font-size:{font_size}px;"
                            f"font-weight:{weight};font-family:'Segoe UI';")
        self.setStyleSheet(self._ss_normal)
        self.setMinimumHeight(72)

    def enterEvent(self, _e):
        self.setStyleSheet(self._ss_hover)

    def leaveEvent(self, _e):
        self.setStyleSheet(self._ss_normal)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.setStyleSheet(self._ss_pressed)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.rect().contains(e.position().toPoint()):
                self.setStyleSheet(self._ss_hover)
                self.clicked.emit()
            else:
                self.setStyleSheet(self._ss_normal)


# ── Separator helper ───────────────────────────────────────────────────────────

def _hline(parent=None) -> QFrame:
    line = QFrame(parent)
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Plain)
    line.setFixedHeight(1)
    return line


# ── Main window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    PHRASE_COLS = 3

    def __init__(self):
        super().__init__()
        self.settings     = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self.phrases_data = load_json(PHRASES_FILE, DEFAULT_PHRASES)
        self.usage        = load_json(USAGE_FILE, {})
        self.phrase_history: list[str] = []
        self.edit_mode    = False
        self._tab_widgets: dict = {}
        self._active_tab: str | None = None
        self._mobile_server: "MobileServer | None" = None
        self._mobile_win: "MobileWindow | None"    = None
        self._mobile_updating = False
        self._wifi_online: bool | None = None

        self.setWindowTitle("Survey Sentence Generator")
        self.showMaximized()
        self.setMinimumSize(900, 580)

        _bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        _icon = os.path.join(_bundle_dir, "treez.ico")
        if os.path.exists(_icon):
            self.setWindowIcon(QIcon(_icon))

        # debounce timers
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(400)
        self._resize_timer.timeout.connect(self._save_geometry)

        self._mobile_sync_timer = QTimer(self)
        self._mobile_sync_timer.setSingleShot(True)
        self._mobile_sync_timer.setInterval(300)
        self._mobile_sync_timer.timeout.connect(self._do_sync_to_mobile)

        self._wifi_timer = QTimer(self)
        self._wifi_timer.setInterval(10_000)
        self._wifi_timer.timeout.connect(self._poll_wifi)

        if not DEPS_OK:
            QMessageBox.warning(
                self, "Missing packages",
                "pyautogui or pyperclip not found.\n\n"
                "Run:  pip install pyautogui pyperclip\n\n"
                "The GO button will not work until installed.",
            )

        self._build_ui()

    # ── Palette ────────────────────────────────────────────────────────────────

    def _p(self):
        return DK if self.settings.get("dark_mode", False) else LT

    def _cat_color(self, cat_idx: int):
        cats   = self.phrases_data.get("categories", [])
        stored = cats[cat_idx].get("color_idx") if cat_idx < len(cats) else None
        key    = (stored if stored is not None else cat_idx) % len(CAT_COLORS)
        cc     = CAT_COLORS[key]
        if self.settings.get("dark_mode", False):
            return cc[2], cc[3]
        return cc[0], cc[1]

    # ── Full rebuild (theme toggle) ─────────────────────────────────────────────

    def _full_rebuild(self):
        saved = ""
        if hasattr(self, "sentence_text"):
            saved = self.sentence_text.toPlainText()
        self._tab_widgets   = {}
        self._active_tab    = None
        self.sugg_container = None
        self._sugg_expanded = False
        old = self.centralWidget()
        self._build_ui()
        if old:
            old.deleteLater()
        if saved:
            self.sentence_text.setPlainText(saved)

    # ── Build UI ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        p    = self._p()
        dark = self.settings.get("dark_mode", False)

        self.setStyleSheet(_qss(p))

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        header = QWidget()
        header.setStyleSheet(f"background:{p['hdr']};")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(20, 12, 20, 12)
        hdr_layout.setSpacing(0)

        title = QLabel("Survey Sentence Generator")
        title.setStyleSheet(f"color:#FFFFFF;font-size:15px;font-weight:bold;"
                            f"background:{p['hdr']};")
        hdr_layout.addWidget(title)

        ver_lbl = QLabel(f"  v{APP_VERSION}")
        ver_lbl.setStyleSheet(f"color:#6B8BB5;font-size:10px;background:{p['hdr']};")
        hdr_layout.addWidget(ver_lbl)
        hdr_layout.addStretch()

        self._update_btn_ref = None

        settings_btn = self._header_btn("Settings", self._open_settings, p)
        mobile_btn   = self._header_btn("Mobile",   self._open_mobile,   p)

        self.edit_btn = self._header_btn("Edit Phrases", self._toggle_edit, p)

        self.dark_btn = self._header_btn(
            "Field Mode ON" if dark else "Field Mode",
            self._toggle_dark, p,
        )
        if dark:
            self.dark_btn.setStyleSheet(
                f"background:{p['edit_act']};color:#000000;"
                f"border:1px solid {p['edit_bd']};padding:6px 14px;"
                f"font-family:'Segoe UI';font-size:10px;"
            )

        for btn in [settings_btn, mobile_btn, self.edit_btn, self.dark_btn]:
            hdr_layout.addWidget(btn)
            hdr_layout.setSpacing(8)

        self.header_layout = hdr_layout
        root_layout.addWidget(header)
        root_layout.addWidget(_hline())

        # ── Sentence panel ─────────────────────────────────────────────────
        sent_panel = QWidget()
        sent_panel.setStyleSheet(f"background:{p['bg']};")
        sp_layout = QVBoxLayout(sent_panel)
        sp_layout.setContentsMargins(20, 10, 20, 10)
        sp_layout.setSpacing(6)

        lbl = QLabel("GENERATED SENTENCE")
        lbl.setStyleSheet(f"color:{p['text3']};font-size:9px;font-weight:bold;"
                          f"font-family:'Segoe UI';background:{p['bg']};")
        sp_layout.addWidget(lbl)

        self.sentence_text = QTextEdit()
        self.sentence_text.setObjectName("sentence")
        self.sentence_text.setMaximumHeight(90)
        self.sentence_text.setMinimumHeight(70)
        font = QFont("Segoe UI", 16)
        font.setBold(dark)
        self.sentence_text.setFont(font)
        self.sentence_text.textChanged.connect(
            lambda: self._sync_to_mobile(debounce=True))
        sp_layout.addWidget(self.sentence_text)

        root_layout.addWidget(sent_panel)

        # ── Suggestion strip ────────────────────────────────────────────────
        self._sugg_expanded = False

        self.sugg_header = QPushButton()
        self.sugg_header.setCursor(Qt.PointingHandCursor)
        self.sugg_header.setStyleSheet(
            f"QPushButton {{ background:{p['surface']}; color:{p['text3']}; "
            f"border:none; border-bottom:1px solid {p['border']}; "
            f"padding:4px 12px; font-family:'Segoe UI'; font-size:9px; "
            f"text-align:left; }}"
            f"QPushButton:hover {{ background:{p['hover']}; }}"
        )
        self.sugg_header.clicked.connect(self._toggle_suggestions)
        self.sugg_header.hide()
        root_layout.addWidget(self.sugg_header)

        self.sugg_container = QWidget()
        self.sugg_container.setStyleSheet(f"background:{p['surface']};")
        self.sugg_layout = QHBoxLayout(self.sugg_container)
        self.sugg_layout.setContentsMargins(12, 6, 12, 6)
        self.sugg_layout.setSpacing(6)
        self.sugg_container.hide()
        root_layout.addWidget(self.sugg_container)

        root_layout.addWidget(_hline())

        # ── Tab strip ───────────────────────────────────────────────────────
        self.tab_strip = QWidget()
        self.tab_strip.setStyleSheet(f"background:{p['surface']};")
        self.tab_strip_layout = QHBoxLayout(self.tab_strip)
        self.tab_strip_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_strip_layout.setSpacing(0)
        self.tab_strip_layout.addStretch()
        root_layout.addWidget(self.tab_strip)
        root_layout.addWidget(_hline())

        # ── Content area (stacked) ──────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background:{p['surface']};")
        root_layout.addWidget(self.stack, 1)

        # ── Action dock ─────────────────────────────────────────────────────
        root_layout.addWidget(_hline())
        dock = QWidget()
        dock.setStyleSheet(f"background:{p['surface']};")
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(20, 12, 20, 12)
        dock_layout.setSpacing(10)

        fs = self.settings.get("font_size", 14)
        btn_font_size = fs + 8

        for label, cmd in [("Clear", self._clear), ("Undo", self._undo)]:
            b = self._action_btn(label, cmd, p["btn_bg"], p["text2"],
                                 p["hover"], p["text"], p["border"], btn_font_size)
            dock_layout.addWidget(b)

        dock_layout.addStretch()

        self.clean_btn = self._action_btn(
            "Clean", self._clean,
            p["info_fg"], "#FFFFFF", p["info_dk"], "#FFFFFF",
            p["info_fg"], btn_font_size,
        )
        dock_layout.addWidget(self.clean_btn)

        go_btn = self._action_btn(
            "GO", self._go,
            p["green"], "#FFFFFF", p["green_d"], "#FFFFFF",
            p["green"], btn_font_size,
        )
        go_btn.setMinimumWidth(140)
        dock_layout.addWidget(go_btn)

        root_layout.addWidget(dock)

        # ── Status bar ──────────────────────────────────────────────────────
        sb = self.statusBar()
        sb.setStyleSheet(f"background:{p['surface']};color:{p['text3']};font-size:10px;")

        # Remove stale widgets from previous builds (statusBar() persists across rebuilds)
        for attr in ("_wifi_label", "_status_label"):
            old_w = getattr(self, attr, None)
            if old_w is not None:
                sb.removeWidget(old_w)
                old_w.deleteLater()

        self._wifi_label = QLabel("  ")
        self._wifi_label.setStyleSheet(f"background:{p['surface']};font-size:14px;")
        sb.addWidget(self._wifi_label)

        self._status_label = QLabel(f"Ready  |  v{APP_VERSION}")
        self._status_label.setStyleSheet(f"background:{p['surface']};color:{p['text3']};")
        sb.addWidget(self._status_label)

        self._rebuild_tabs()
        self._poll_wifi()
        self._wifi_timer.start()

    # ── Button factories ───────────────────────────────────────────────────────

    def _header_btn(self, text: str, slot, p: dict) -> QPushButton:
        btn = QPushButton(f"  {text}  ")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background:{p['hdr']}; color:#FFFFFF; "
            f"border:1px solid #4A6FA5; padding:6px 14px; "
            f"font-family:'Segoe UI'; font-size:10px; }}"
            f"QPushButton:hover {{ background:{p['hdr_h']}; }}"
        )
        btn.clicked.connect(slot)
        return btn

    def _action_btn(self, text, slot, bg, fg, hbg, hfg, border, fsize) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background:{bg}; color:{fg}; border:1px solid {border}; "
            f"padding:14px 24px; font-family:'Segoe UI'; font-size:{fsize}px; "
            f"font-weight:bold; }}"
            f"QPushButton:hover {{ background:{hbg}; color:{hfg}; }}"
            f"QPushButton:pressed {{ background:{hfg}; color:{hbg}; }}"
        )
        btn.clicked.connect(slot)
        return btn

    # ── WiFi indicator ─────────────────────────────────────────────────────────

    def _poll_wifi(self):
        def check():
            online = _is_online()
            QTimer.singleShot(0, self, lambda o=online: self._apply_wifi(o))
        threading.Thread(target=check, daemon=True).start()

    def _apply_wifi(self, online: bool):
        if online == self._wifi_online:
            return
        self._wifi_online = online
        if online:
            self._wifi_label.setText("▲")
            self._wifi_label.setStyleSheet(
                f"color:#22C55E;font-size:14px;background:{self._p()['surface']};")
        else:
            self._wifi_label.setText("✕")
            self._wifi_label.setStyleSheet(
                f"color:#EF4444;font-size:14px;background:{self._p()['surface']};")
        self._update_clean_btn_state()

    def _update_clean_btn_state(self):
        p = self._p()
        if self._wifi_online:
            self.clean_btn.setEnabled(True)
            self.clean_btn.setCursor(Qt.PointingHandCursor)
            self.clean_btn.setStyleSheet(
                f"QPushButton {{ background:{p['info_fg']}; color:#FFFFFF; "
                f"border:1px solid {p['info_fg']}; padding:14px 24px; "
                f"font-family:'Segoe UI'; font-size:{self.settings.get('font_size',14)+8}px; "
                f"font-weight:bold; }}"
                f"QPushButton:hover {{ background:{p['info_dk']}; }}"
            )
        else:
            self.clean_btn.setEnabled(False)
            self.clean_btn.setCursor(Qt.ArrowCursor)
            self.clean_btn.setStyleSheet(
                f"QPushButton {{ background:{p['hover']}; color:{p['text3']}; "
                f"border:1px solid {p['border']}; padding:14px 24px; "
                f"font-family:'Segoe UI'; font-size:{self.settings.get('font_size',14)+8}px; "
                f"font-weight:bold; }}"
            )

    # ── Dark mode toggle ───────────────────────────────────────────────────────

    def _toggle_dark(self):
        self.settings["dark_mode"] = not self.settings.get("dark_mode", False)
        save_json(SETTINGS_FILE, self.settings)
        self._full_rebuild()

    # ── Tab building ───────────────────────────────────────────────────────────

    def _rebuild_tabs(self):
        # clear tab strip (keep stretch at end)
        while self.tab_strip_layout.count() > 1:
            item = self.tab_strip_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # clear stack
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        self._tab_widgets = {}
        self._active_tab  = None
        p  = self._p()
        fs = self.settings.get("font_size", 14) + 4

        for cat_idx, cat in enumerate(self.phrases_data.get("categories", [])):
            name           = cat["name"]
            cat_bg, cat_fg = self._cat_color(cat_idx)

            # ── tab button wrapper (button + indicator bar) ─────────────────
            tab_wrap = QWidget()
            tab_wrap.setStyleSheet(f"background:{p['surface']};")
            tw_layout = QVBoxLayout(tab_wrap)
            tw_layout.setContentsMargins(0, 0, 0, 0)
            tw_layout.setSpacing(0)

            btn_row = QWidget()
            btn_row.setStyleSheet(f"background:{p['surface']};")
            br_layout = QHBoxLayout(btn_row)
            br_layout.setContentsMargins(0, 0, 0, 0)
            br_layout.setSpacing(0)

            tab_btn = QPushButton(f"  {name}  ")
            tab_btn.setCursor(Qt.PointingHandCursor)
            tab_btn.setStyleSheet(
                f"QPushButton {{ background:{cat_bg}; color:{cat_fg}; "
                f"border:none; padding:11px 0; font-family:'Segoe UI'; font-size:14px; }}"
                f"QPushButton:hover {{ background:{cat_fg}; color:#FFFFFF; font-weight:bold; }}"
            )
            tab_btn.clicked.connect(lambda checked=False, n=name: self._select_tab(n))
            br_layout.addWidget(tab_btn)

            if self.edit_mode:
                gear = QPushButton(" ⚙ ")
                gear.setCursor(Qt.PointingHandCursor)
                gear.setStyleSheet(
                    f"QPushButton {{ background:{p['edit_act']}; color:#1C1400; "
                    f"border:none; padding:11px 4px; font-family:'Segoe UI'; font-size:9px; }}"
                    f"QPushButton:hover {{ background:#E88E00; }}"
                )
                gear.clicked.connect(lambda checked=False, ci=cat_idx: self._edit_category_direct(ci))
                br_layout.addWidget(gear)

            tw_layout.addWidget(btn_row)

            indicator = QFrame()
            indicator.setFixedHeight(3)
            indicator.setStyleSheet(f"background:{p['surface']};border:none;")
            tw_layout.addWidget(indicator)

            # separator between tabs
            if cat_idx > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.VLine)
                sep.setFrameShadow(QFrame.Plain)
                sep.setStyleSheet(f"color:{p['border']};")
                self.tab_strip_layout.insertWidget(
                    self.tab_strip_layout.count() - 1, sep)

            self.tab_strip_layout.insertWidget(
                self.tab_strip_layout.count() - 1, tab_wrap)

            # ── content page ────────────────────────────────────────────────
            page = self._make_tab_page(cat, fs, cat_idx, cat_bg, cat_fg, p)
            self.stack.addWidget(page)

            self._tab_widgets[name] = {
                "btn": tab_btn, "indicator": indicator,
                "cat_fg": cat_fg, "cat_bg": cat_bg,
                "page_idx": self.stack.count() - 1,
            }

        if self.edit_mode:
            sep = QFrame()
            sep.setFrameShape(QFrame.VLine)
            sep.setFrameShadow(QFrame.Plain)
            sep.setStyleSheet(f"color:{p['border']};")
            self.tab_strip_layout.insertWidget(
                self.tab_strip_layout.count() - 1, sep)

            add_cat = QPushButton("  ＋ Category  ")
            add_cat.setCursor(Qt.PointingHandCursor)
            add_cat.setStyleSheet(
                f"QPushButton {{ background:{p['green_l']}; color:{p['green']}; "
                f"border:none; padding:11px 8px; font-family:'Segoe UI'; font-size:11px; }}"
                f"QPushButton:hover {{ background:{p['green_m']}; color:{p['green_d']}; }}"
            )
            add_cat.clicked.connect(self._new_category_direct)
            self.tab_strip_layout.insertWidget(
                self.tab_strip_layout.count() - 1, add_cat)

        if self._tab_widgets:
            self._select_tab(next(iter(self._tab_widgets)))

        threading.Thread(target=self._bg_update_check, daemon=True).start()

    def _make_tab_page(self, cat: dict, fs: int, cat_idx: int,
                       cat_bg: str, cat_fg: str, p: dict) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background:{p['surface']}; }}"
                             f"QWidget {{ background:{p['surface']}; }}")

        inner  = QWidget()
        grid   = QGridLayout(inner)
        grid.setSpacing(6)
        grid.setContentsMargins(8, 8, 8, 8)

        cols = cat.get("cols", self.PHRASE_COLS)

        if self.edit_mode:
            phrases = cat["phrases"]
            for i, phrase in enumerate(phrases):
                r, c = divmod(i, cols)
                cell = self._edit_cell(phrase, cat_idx, fs, p)
                grid.addWidget(cell, r, c)

            ar, ac = divmod(len(phrases), cols)
            add = QPushButton("+ Add phrase")
            add.setCursor(Qt.PointingHandCursor)
            add.setMinimumHeight(64)
            add.setStyleSheet(
                f"QPushButton {{ background:{p['green_l']}; color:{p['green']}; "
                f"border:1px solid {p['green']}; padding:10px 18px; "
                f"font-family:'Segoe UI'; font-size:{fs}px; font-weight:bold; }}"
                f"QPushButton:hover {{ background:{p['green_m']}; color:{p['green_d']}; }}"
            )
            add.clicked.connect(lambda checked=False, ci=cat_idx: self._add_phrase_direct(ci))
            grid.addWidget(add, ar, ac)
        else:
            cat_name = cat["name"]
            phrases_sorted = sorted(
                cat["phrases"],
                key=lambda ph: self.usage.get(f"{cat_name}|{ph}", 0),
                reverse=True,
            )
            for i, phrase in enumerate(phrases_sorted):
                r, c = divmod(i, cols)
                count = self.usage.get(f"{cat_name}|{phrase}", 0)
                label = phrase + (f"  [{count}]" if count > 0 else "")
                btn = PhraseButton(
                    label, cat_fg, "#FFFFFF", p["hover"], p["text"],
                    font_size=fs, bold=True,
                )
                btn.clicked.connect(
                    lambda ph=phrase, ci=cat_idx: self._add_phrase_tracked(ph, ci))
                grid.addWidget(btn, r, c)

        for c in range(cols):
            grid.setColumnStretch(c, 1)

        scroll.setWidget(inner)
        return scroll

    def _edit_cell(self, phrase: str, cat_idx: int, fs: int, p: dict) -> QWidget:
        cell = QFrame()
        cell.setStyleSheet(
            f"QFrame {{ background:{p['edit_bg']}; border:1px solid {p['edit_bd']}; }}")
        cell.setMinimumHeight(64)
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        pb = PhraseButton(
            phrase, p["edit_bg"], p["text"], p["hover"], p["text"],
            font_size=fs, bold=(p["weight"] == "bold"),
        )
        pb.clicked.connect(lambda ph=phrase, ci=cat_idx: self._add_phrase_tracked(ph, ci))
        layout.addWidget(pb, 1)

        eb = QPushButton("Edit")
        eb.setCursor(Qt.PointingHandCursor)
        eb.setMinimumHeight(64)
        eb.setStyleSheet(
            f"QPushButton {{ background:{p['info_bg']}; color:{p['info_fg']}; "
            f"border:1px solid {p['info_fg']}; padding:0 12px; "
            f"font-family:'Segoe UI'; font-size:10px; font-weight:bold; }}"
            f"QPushButton:hover {{ background:{p['info_hd']}; }}"
        )
        eb.clicked.connect(lambda checked=False, ci=cat_idx, ph=phrase:
                           self._edit_phrase_direct(ci, ph))
        layout.addWidget(eb)

        db = QPushButton("Del")
        db.setCursor(Qt.PointingHandCursor)
        db.setMinimumHeight(64)
        db.setStyleSheet(
            f"QPushButton {{ background:{p['danger_bg']}; color:{p['danger_fg']}; "
            f"border:1px solid {p['danger_fg']}; padding:0 12px; "
            f"font-family:'Segoe UI'; font-size:10px; font-weight:bold; }}"
            f"QPushButton:hover {{ background:{p['danger_hd']}; }}"
        )
        db.clicked.connect(lambda checked=False, ci=cat_idx, ph=phrase:
                           self._delete_phrase_direct(ci, ph))
        layout.addWidget(db)
        return cell

    # ── Update check ───────────────────────────────────────────────────────────

    def _bg_update_check(self):
        try:
            tag, exe_url = _fetch_latest_release()
            if tag and exe_url and _version_newer(tag, APP_VERSION):
                QTimer.singleShot(0, self, lambda t=tag, u=exe_url: self._show_update_banner(t, u))
        except Exception:
            pass

    def _show_update_banner(self, tag: str, exe_url: str):
        p   = self._p()
        btn = QPushButton(f"  ↑ Update v{tag}  ")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { background:#F59E0B; color:#1C1400; "
            "border:none; padding:6px 14px; font-family:'Segoe UI'; "
            "font-size:10px; font-weight:bold; }"
            "QPushButton:hover { background:#D97706; }"
        )
        btn.clicked.connect(lambda: self._prompt_update(tag, exe_url))
        self.header_layout.insertWidget(self.header_layout.count() - 1, btn)
        self._update_btn_ref = btn

    def _prompt_update(self, tag: str, exe_url: str):
        frozen = getattr(sys, "frozen", False)
        if frozen:
            ok = QMessageBox.question(
                self, "Update available",
                f"Version {tag} is available.\n\nDownload and restart now?",
            ) == QMessageBox.Yes
            if ok:
                self._status_label.setText(f"Downloading v{tag}…")
                QApplication.processEvents()
                threading.Thread(target=_perform_update, args=(exe_url,), daemon=True).start()
        else:
            QMessageBox.information(
                self, "Update available",
                f"Version {tag} is available.\n\n"
                f"Download it from:\n"
                f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
            )

    # ── Tab selection ──────────────────────────────────────────────────────────

    def _select_tab(self, name: str):
        p = self._p()
        if self._active_tab and self._active_tab in self._tab_widgets:
            prev = self._tab_widgets[self._active_tab]
            prev["btn"].setStyleSheet(
                f"QPushButton {{ background:{prev['cat_bg']}; color:{prev['cat_fg']}; "
                f"border:none; padding:11px 0; font-family:'Segoe UI'; font-size:14px; }}"
                f"QPushButton:hover {{ background:{prev['cat_fg']}; color:#FFFFFF; font-weight:bold; }}"
            )
            prev["indicator"].setStyleSheet(f"background:{p['surface']};border:none;")

        self._active_tab = name
        cur = self._tab_widgets[name]
        cur["btn"].setStyleSheet(
            f"QPushButton {{ background:{cur['cat_fg']}; color:#FFFFFF; "
            f"border:none; padding:11px 0; font-family:'Segoe UI'; "
            f"font-size:14px; font-weight:bold; }}"
        )
        cur["indicator"].setStyleSheet(
            f"background:{cur['cat_fg']};border:none;")
        self.stack.setCurrentIndex(cur["page_idx"])

    # ── Phrase tracking + suggestions ──────────────────────────────────────────

    def _add_phrase_tracked(self, phrase: str, cat_idx: int):
        self._add_phrase(phrase)
        cat_name = self.phrases_data["categories"][cat_idx]["name"]
        key = f"{cat_name}|{phrase}"
        self.usage[key] = self.usage.get(key, 0) + 1
        save_json(USAGE_FILE, self.usage)
        self._update_suggestions(cat_idx)

    def _toggle_suggestions(self):
        self._sugg_expanded = not self._sugg_expanded
        self.sugg_container.setVisible(self._sugg_expanded)
        self._refresh_sugg_header()

    def _refresh_sugg_header(self):
        p     = self._p()
        count = self.sugg_layout.count() - 1  # exclude stretch
        arrow = "▼" if self._sugg_expanded else "▶"
        self.sugg_header.setText(f"  {arrow}  Suggestions  ({count})")

    def _update_suggestions(self, from_cat_idx: int):
        p      = self._p()
        fs     = max(self.settings.get("font_size", 14) - 2, 10)
        bold   = p["weight"] == "bold"

        candidates = []
        for ci, cat in enumerate(self.phrases_data.get("categories", [])):
            if ci == from_cat_idx:
                continue
            for ph in cat["phrases"]:
                cnt = self.usage.get(f"{cat['name']}|{ph}", 0)
                if cnt > 0:
                    candidates.append((cnt, ci, ph))
        candidates.sort(reverse=True)
        top = candidates[:6]

        # clear existing
        while self.sugg_layout.count():
            item = self.sugg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not top:
            self.sugg_header.hide()
            self.sugg_container.hide()
            return

        for _cnt, ci, ph in top:
            cbg, cfg = self._cat_color(ci)
            short    = ph[:36] + ("…" if len(ph) > 36 else "")
            b = PhraseButton(short, cbg, cfg, p["hover"], p["text"],
                             font_size=fs, bold=bold)
            b.clicked.connect(lambda x=ph, idx=ci: self._add_phrase_tracked(x, idx))
            self.sugg_layout.addWidget(b)

        self.sugg_layout.addStretch()
        self._refresh_sugg_header()
        self.sugg_header.show()
        # body stays at its current expanded/collapsed state
        self.sugg_container.setVisible(self._sugg_expanded)

    # ── Sentence actions ───────────────────────────────────────────────────────

    def _add_phrase(self, phrase: str):
        current = self.sentence_text.toPlainText()
        sep = " " if current.rstrip() else ""
        cursor = self.sentence_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.sentence_text.setTextCursor(cursor)
        self.sentence_text.insertPlainText(sep + phrase)
        self.phrase_history.append(phrase)
        self._sync_to_mobile()

    def _undo(self):
        if not self.phrase_history:
            return
        self.phrase_history.pop()
        self.sentence_text.setPlainText(" ".join(self.phrase_history))
        self._sync_to_mobile()

    def _clear(self):
        self.sentence_text.clear()
        self.phrase_history.clear()
        while self.sugg_layout.count():
            item = self.sugg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.sugg_header.hide()
        self.sugg_container.hide()
        self._sugg_expanded = False
        self._sync_to_mobile()

    # ── Edit mode ──────────────────────────────────────────────────────────────

    def _toggle_edit(self):
        p = self._p()
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.edit_btn.setStyleSheet(
                f"QPushButton {{ background:{p['edit_act']}; color:#1C1400; "
                f"border:1px solid {p['edit_bd']}; padding:6px 14px; "
                f"font-family:'Segoe UI'; font-size:10px; }}"
                f"QPushButton:hover {{ background:#E88E00; }}"
            )
            self._status_label.setText("Edit mode — Del to remove, Edit to rename, + to add")
        else:
            self.edit_btn.setStyleSheet(
                f"QPushButton {{ background:{p['hdr']}; color:#FFFFFF; "
                f"border:1px solid #4A6FA5; padding:6px 14px; "
                f"font-family:'Segoe UI'; font-size:10px; }}"
                f"QPushButton:hover {{ background:{p['hdr_h']}; }}"
            )
            self._status_label.setText("Ready")
        self._rebuild_tabs()

    def _new_category_direct(self):
        dlg = CategoryDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.result_data:
            name, color_idx = dlg.result_data
            self.phrases_data["categories"].append(
                {"name": name, "phrases": [], "color_idx": color_idx}
            )
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()
            self._select_tab(name)

    def _edit_category_direct(self, cat_idx: int):
        cat           = self.phrases_data["categories"][cat_idx]
        default_color = cat.get("color_idx", cat_idx % len(CAT_COLORS))
        dlg = CategoryDialog(self, name=cat["name"], color_idx=default_color,
                             allow_delete=True)
        if dlg.exec() != QDialog.Accepted:
            return
        if dlg.result_data == "delete":
            self.phrases_data["categories"].pop(cat_idx)
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()
        elif dlg.result_data:
            new_name, new_color = dlg.result_data
            cat["name"]      = new_name
            cat["color_idx"] = new_color
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()
            if new_name in self._tab_widgets:
                self._select_tab(new_name)

    def _delete_phrase_direct(self, cat_idx: int, phrase: str):
        phrases = self.phrases_data["categories"][cat_idx]["phrases"]
        if phrase in phrases:
            phrases.remove(phrase)
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()

    def _edit_phrase_direct(self, cat_idx: int, phrase: str):
        phrases = self.phrases_data["categories"][cat_idx]["phrases"]
        if phrase not in phrases:
            return
        new_text, ok = QInputDialog.getText(
            self, "Edit Phrase", "Phrase text:", text=phrase)
        if ok and new_text.strip() and new_text.strip() != phrase:
            phrases[phrases.index(phrase)] = new_text.strip()
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()

    def _add_phrase_direct(self, cat_idx: int):
        text, ok = QInputDialog.getText(self, "New Phrase", "Phrase text:")
        if ok and text.strip():
            self.phrases_data["categories"][cat_idx]["phrases"].append(text.strip())
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()

    # ── GO ─────────────────────────────────────────────────────────────────────

    def _go(self):
        sentence = self.sentence_text.toPlainText().strip()
        if not sentence:
            return
        if not DEPS_OK:
            QMessageBox.critical(self, "Cannot paste",
                                 "Run: pip install pyautogui pyperclip")
            return
        delay_ms = int(float(self.settings.get("delay", 1.0)) * 1000)
        self._status_label.setText("Minimising…")
        QApplication.processEvents()
        self.showMinimized()
        QTimer.singleShot(delay_ms, lambda: self._do_paste(sentence))

    def _do_paste(self, sentence: str):
        try:
            pyperclip.copy(sentence)
            pyautogui.hotkey("ctrl", "v")
        except Exception as exc:
            self.showNormal()
            QMessageBox.critical(self, "Paste error", str(exc))
            return
        if self.settings.get("clear_after_go", True):
            self._clear()
        preview = sentence[:65] + ("…" if len(sentence) > 65 else "")
        self._status_label.setText(f"Pasted: {preview}")

    # ── Clean (Groq AI) ────────────────────────────────────────────────────────

    _CLEAN_SYSTEM = (
        "You are an expert arborist and tree surveyor writing formal "
        "BS 5837 tree survey reports in the UK.\n\n"
        "Rewrite the user's draft survey note into polished, professional "
        "arboricultural report language.\n\n"
        "Rules:\n"
        "- Preserve ALL technical observations, dimensions, species names, "
        "and measurements exactly as given.\n"
        "- Use professional arboricultural terminology and BS 5837 "
        "conventions where appropriate.\n"
        "- Write in third person, past tense (e.g. 'The tree was observed…').\n"
        "- Be concise — one to three sentences maximum.\n"
        "- Output ONLY the rewritten text. No preamble, no explanation, no commentary."
    )

    def _clean(self):
        sentence = self.sentence_text.toPlainText().strip()
        if not sentence:
            return
        if not AI_OK:
            QMessageBox.critical(self, "Missing package",
                                 "Run:  pip install openai\n\nThen restart.")
            return
        p  = self._p()
        fs = self.settings.get("font_size", 14)
        self.clean_btn.setEnabled(False)
        self.clean_btn.setText("Cleaning…")
        self.clean_btn.setStyleSheet(
            f"QPushButton {{ background:{p['hover']}; color:{p['text3']}; "
            f"border:1px solid {p['border']}; padding:14px 24px; "
            f"font-family:'Segoe UI'; font-size:{fs+8}px; font-weight:bold; }}"
        )
        self._status_label.setText(f"Cleaning with Groq ({GROK_MODEL})…")
        threading.Thread(target=self._do_clean,
                         args=(sentence, GROQ_API_KEY), daemon=True).start()

    def _do_clean(self, sentence: str, api_key: str):
        try:
            client   = _OpenAI(api_key=api_key, base_url=GROK_BASE_URL)
            response = client.chat.completions.create(
                model=GROK_MODEL, max_tokens=512,
                messages=[
                    {"role": "system", "content": self._CLEAN_SYSTEM},
                    {"role": "user",   "content": sentence},
                ],
            )
            improved = response.choices[0].message.content.strip()
            QTimer.singleShot(0, self, lambda i=improved: self._apply_clean(i))
        except Exception as exc:
            log.exception("Clean API call failed")
            msg = str(exc)
            QTimer.singleShot(0, self, lambda m=msg: self._clean_error(m))

    def _apply_clean(self, improved: str):
        self.sentence_text.setPlainText(improved)
        self.phrase_history.clear()
        self._sync_to_mobile()
        self._restore_clean_btn()
        self._status_label.setText("Sentence cleaned by Groq")

    def _clean_error(self, msg: str):
        self._restore_clean_btn()
        self._status_label.setText(f"Clean failed — {msg[:90]}")

    def _restore_clean_btn(self):
        p  = self._p()
        fs = self.settings.get("font_size", 14)
        self.clean_btn.setText("Clean")
        self.clean_btn.setEnabled(True)
        self.clean_btn.setCursor(Qt.PointingHandCursor)
        self.clean_btn.setStyleSheet(
            f"QPushButton {{ background:{p['info_fg']}; color:#FFFFFF; "
            f"border:1px solid {p['info_fg']}; padding:14px 24px; "
            f"font-family:'Segoe UI'; font-size:{fs+8}px; font-weight:bold; }}"
            f"QPushButton:hover {{ background:{p['info_dk']}; }}"
        )

    # ── Mobile input ───────────────────────────────────────────────────────────

    def _open_mobile(self):
        if self._mobile_server is None:
            try:
                self._mobile_server = MobileServer(self)
            except Exception as exc:
                QMessageBox.critical(self, "Mobile server error", str(exc))
                return
        ip  = _get_local_ip()
        url = f"http://{ip}:{self._mobile_server.port}/"
        if self._mobile_win is None:
            self._mobile_win = MobileWindow(self, url)
        self._mobile_win.show()
        self._mobile_win.raise_()
        self._mobile_win.activateWindow()

    def _stop_mobile(self):
        if self._mobile_server:
            self._mobile_server.stop()
            self._mobile_server = None
        self._mobile_win = None

    def _apply_mobile_text(self, text: str):
        current = self.sentence_text.toPlainText()
        if current == text:
            return
        self._mobile_updating = True
        self.sentence_text.setPlainText(text)
        self._mobile_updating = False

    def _sync_to_mobile(self, debounce: bool = False):
        if not self._mobile_server or self._mobile_updating:
            return
        if debounce:
            self._mobile_sync_timer.start()
        else:
            self._do_sync_to_mobile()

    def _do_sync_to_mobile(self):
        if self._mobile_server and not self._mobile_updating:
            self._mobile_server.set_text(self.sentence_text.toPlainText())

    # ── Settings ───────────────────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsWindow(self)
        dlg.exec()

    # ── Geometry persistence ───────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_resize_timer"):
            self._resize_timer.start()

    def _save_geometry(self):
        g = self.geometry()
        self.settings["geometry"] = f"{g.width()}x{g.height()}"
        save_json(SETTINGS_FILE, self.settings)

    def closeEvent(self, event):
        self._wifi_timer.stop()
        if self._mobile_server:
            self._mobile_server.stop()
        super().closeEvent(event)


# ── Category dialog ────────────────────────────────────────────────────────────

class CategoryDialog(QDialog):
    def __init__(self, parent: MainWindow, name: str = "",
                 color_idx: int = 0, allow_delete: bool = False):
        super().__init__(parent)
        self.result_data = None
        self._color_idx  = color_idx
        p    = parent._p()
        dark = parent.settings.get("dark_mode", False)

        self.setWindowTitle("Edit Category" if allow_delete else "New Category")
        self.setStyleSheet(_qss(p) + f"QDialog {{ background:{p['bg']}; }}")
        self.setFixedWidth(480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(0)

        # ── Name ────────────────────────────────────────────────────────────
        lbl_name = QLabel("NAME")
        lbl_name.setStyleSheet(f"color:{p['text3']};font-size:8px;font-weight:bold;"
                               f"font-family:'Segoe UI';background:{p['bg']};")
        layout.addWidget(lbl_name)
        layout.addSpacing(4)

        name_wrap = QFrame()
        name_wrap.setStyleSheet(f"background:{p['border']};")
        name_wrap.setFixedHeight(42)
        nw_layout = QHBoxLayout(name_wrap)
        nw_layout.setContentsMargins(1, 1, 1, 1)

        self._name_edit = QLineEdit(name)
        self._name_edit.setStyleSheet(
            f"background:{p['btn_bg']};color:{p['text']};border:none;"
            f"padding:8px;font-family:'Segoe UI';font-size:14px;"
        )
        nw_layout.addWidget(self._name_edit)
        layout.addWidget(name_wrap)
        layout.addSpacing(18)

        # ── Colour swatches ──────────────────────────────────────────────────
        lbl_col = QLabel("COLOUR")
        lbl_col.setStyleSheet(f"color:{p['text3']};font-size:8px;font-weight:bold;"
                              f"font-family:'Segoe UI';background:{p['bg']};")
        layout.addWidget(lbl_col)
        layout.addSpacing(4)

        swatch_widget = QWidget()
        swatch_widget.setStyleSheet(f"background:{p['bg']};")
        swatch_grid   = QGridLayout(swatch_widget)
        swatch_grid.setSpacing(4)
        swatch_grid.setContentsMargins(0, 0, 0, 0)

        self._swatch_btns = []
        for i, cc in enumerate(CAT_COLORS):
            bg_col = cc[2] if dark else cc[0]
            fg_col = cc[3] if dark else cc[1]
            r, c   = divmod(i, 4)
            btn    = QPushButton()
            btn.setFixedSize(48, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"background:{bg_col};border:2px solid transparent;")
            btn.clicked.connect(lambda checked=False, idx=i: self._pick_color(idx))
            swatch_grid.addWidget(btn, r, c)
            self._swatch_btns.append((btn, bg_col))

        layout.addWidget(swatch_widget)
        layout.addSpacing(20)
        self._highlight_swatch(color_idx)

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_row = QWidget()
        btn_row.setStyleSheet(f"background:{p['bg']};")
        br = QHBoxLayout(btn_row)
        br.setContentsMargins(0, 0, 0, 0)
        br.setSpacing(10)

        save_btn = QPushButton("Save")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(
            f"QPushButton {{ background:{p['green']}; color:#FFFFFF; border:none; "
            f"padding:10px 24px; font-family:'Segoe UI'; font-size:12px; font-weight:bold; }}"
            f"QPushButton:hover {{ background:{p['green_d']}; }}"
        )
        save_btn.clicked.connect(self._save)
        br.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(
            f"QPushButton {{ background:{p['btn_bg']}; color:{p['text2']}; "
            f"border:1px solid {p['border']}; padding:10px 24px; "
            f"font-family:'Segoe UI'; font-size:12px; }}"
            f"QPushButton:hover {{ background:{p['hover']}; }}"
        )
        cancel_btn.clicked.connect(self.reject)
        br.addWidget(cancel_btn)
        br.addStretch()

        if allow_delete:
            del_btn = QPushButton("Delete Category")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(
                f"QPushButton {{ background:{p['danger_bg']}; color:{p['danger_fg']}; "
                f"border:1px solid {p['danger_fg']}; padding:10px 24px; "
                f"font-family:'Segoe UI'; font-size:12px; }}"
                f"QPushButton:hover {{ background:{p['danger_hd']}; }}"
            )
            del_btn.clicked.connect(self._confirm_delete)
            br.addWidget(del_btn)

        layout.addWidget(btn_row)

    def _pick_color(self, idx: int):
        self._color_idx = idx
        self._highlight_swatch(idx)

    def _highlight_swatch(self, idx: int):
        for i, (btn, bg) in enumerate(self._swatch_btns):
            if i == idx:
                btn.setStyleSheet(f"background:{bg};border:3px solid #000000;")
            else:
                btn.setStyleSheet(f"background:{bg};border:2px solid transparent;")

    def _save(self):
        name = self._name_edit.text().strip()
        if not name:
            return
        self.result_data = (name, self._color_idx)
        self.accept()

    def _confirm_delete(self):
        name = self._name_edit.text().strip() or "this category"
        reply = QMessageBox.question(
            self, "Delete category",
            f"Delete '{name}' and all its phrases?",
        )
        if reply == QMessageBox.Yes:
            self.result_data = "delete"
            self.accept()


# ── Settings window ────────────────────────────────────────────────────────────

class SettingsWindow(QDialog):
    def __init__(self, parent: MainWindow):
        super().__init__(parent)
        self.app = parent
        p  = parent._p()
        fs = parent.settings.get("font_size", 14)

        self.setWindowTitle("Settings")
        self.resize(680, 480)
        self.setStyleSheet(_qss(p) + f"QDialog {{ background:{p['bg']}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # header
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{p['hdr']};")
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(20, 14, 20, 14)
        hdr_layout.addWidget(
            self._hdr_lbl("Settings", p))
        layout.addWidget(hdr)
        layout.addWidget(_hline())

        # content
        content = QWidget()
        content.setStyleSheet(f"background:{p['bg']};")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(28, 0, 28, 0)
        cl.setSpacing(0)

        def section(title):
            cl.addSpacing(22)
            lbl = QLabel(title)
            lbl.setStyleSheet(f"color:{p['text3']};font-size:8px;font-weight:bold;"
                              f"font-family:'Segoe UI';background:{p['bg']};")
            cl.addWidget(lbl)
            cl.addSpacing(8)

        def rule():
            cl.addSpacing(20)
            cl.addWidget(_hline())

        section("TYPING DELAY")
        row1 = QWidget()
        row1.setStyleSheet(f"background:{p['bg']};")
        r1 = QHBoxLayout(row1)
        r1.setContentsMargins(0, 0, 0, 0)
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.1, 30.0)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setDecimals(1)
        self.delay_spin.setValue(parent.settings.get("delay", 1.0))
        self.delay_spin.setStyleSheet(
            f"background:{p['surface']};color:{p['text']};"
            f"border:1px solid {p['border']};padding:4px;"
            f"font-family:'Segoe UI';font-size:{fs}px;"
        )
        self.delay_spin.setFixedWidth(90)
        r1.addWidget(self.delay_spin)
        lbl = QLabel("seconds between GO and paste")
        lbl.setStyleSheet(f"color:{p['text2']};font-size:11px;"
                          f"font-family:'Segoe UI';background:{p['bg']};")
        r1.addWidget(lbl)
        r1.addStretch()
        cl.addWidget(row1)

        rule()
        section("BEHAVIOUR")
        self.clear_check = QCheckBox("Clear sentence automatically after GO")
        self.clear_check.setChecked(parent.settings.get("clear_after_go", True))
        self.clear_check.setStyleSheet(
            f"color:{p['text']};font-size:{fs}px;font-family:'Segoe UI';"
            f"background:{p['bg']};"
        )
        cl.addWidget(self.clear_check)

        rule()
        section("PHRASE BUTTON TEXT SIZE")
        row3 = QWidget()
        row3.setStyleSheet(f"background:{p['bg']};")
        r3 = QHBoxLayout(row3)
        r3.setContentsMargins(0, 0, 0, 0)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 28)
        self.font_spin.setValue(fs)
        self.font_spin.setStyleSheet(
            f"background:{p['surface']};color:{p['text']};"
            f"border:1px solid {p['border']};padding:4px;"
            f"font-family:'Segoe UI';font-size:{fs}px;"
        )
        self.font_spin.setFixedWidth(70)
        r3.addWidget(self.font_spin)
        pt = QLabel("pt")
        pt.setStyleSheet(f"color:{p['text2']};font-size:11px;"
                         f"font-family:'Segoe UI';background:{p['bg']};")
        r3.addWidget(pt)
        r3.addStretch()
        cl.addWidget(row3)
        cl.addStretch()

        layout.addWidget(content, 1)

        # save bar
        layout.addWidget(_hline())
        save_bar = QWidget()
        save_bar.setStyleSheet(f"background:{p['bg']};")
        sb_layout = QHBoxLayout(save_bar)
        sb_layout.setContentsMargins(28, 16, 28, 16)
        save_btn = QPushButton("Save Settings")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(
            f"QPushButton {{ background:{p['green']}; color:#FFFFFF; border:none; "
            f"padding:11px 28px; font-family:'Segoe UI'; font-size:{fs}px; "
            f"font-weight:bold; }}"
            f"QPushButton:hover {{ background:{p['green_d']}; }}"
        )
        save_btn.clicked.connect(self._save)
        sb_layout.addWidget(save_btn)
        sb_layout.addStretch()
        layout.addWidget(save_bar)

    def _hdr_lbl(self, text, p):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:#FFFFFF;font-size:14px;font-weight:bold;"
                          f"font-family:'Segoe UI';background:{p['hdr']};")
        return lbl

    def _save(self):
        self.app.settings["delay"]          = round(self.delay_spin.value(), 1)
        self.app.settings["clear_after_go"] = self.clear_check.isChecked()
        self.app.settings["font_size"]      = self.font_spin.value()
        save_json(SETTINGS_FILE, self.app.settings)
        self.app._rebuild_tabs()
        QMessageBox.information(self, "Saved", "Settings saved.")


# ── Mobile window ──────────────────────────────────────────────────────────────

class MobileWindow(QDialog):
    def __init__(self, parent: MainWindow, url: str):
        super().__init__(parent)
        self.app = parent
        self._url = url
        p = parent._p()

        self.setWindowTitle("Mobile Input")
        self.setStyleSheet(_qss(p) + f"QDialog {{ background:{p['bg']}; }}")
        self.setFixedWidth(560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # header
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{p['hdr']};")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(16, 12, 16, 12)
        title = QLabel("Mobile Input")
        title.setStyleSheet(f"color:#FFFFFF;font-size:13px;font-weight:bold;"
                            f"font-family:'Segoe UI';background:{p['hdr']};")
        hdr_l.addWidget(title)
        layout.addWidget(hdr)

        inner = QWidget()
        inner.setStyleSheet(f"background:{p['bg']};")
        il = QVBoxLayout(inner)
        il.setContentsMargins(28, 20, 28, 20)
        il.setSpacing(0)
        layout.addWidget(inner)

        # QR code
        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignCenter)
        self._qr_label.setFixedSize(500, 500)
        self._qr_label.setStyleSheet("background:#FFFFFF;")
        self._refresh_qr(url)
        il.addWidget(self._qr_label, 0, Qt.AlignCenter)
        il.addSpacing(14)

        self._scan_lbl = QLabel("Scan with your phone's camera")
        self._scan_lbl.setAlignment(Qt.AlignCenter)
        self._scan_lbl.setStyleSheet(
            f"color:{p['text']};font-size:13px;font-weight:bold;"
            f"font-family:'Segoe UI';background:{p['bg']};")
        il.addWidget(self._scan_lbl)
        il.addSpacing(16)
        il.addWidget(_hline())
        il.addSpacing(6)

        # URL box
        url_wrap = QFrame()
        url_wrap.setStyleSheet(f"background:{p['border']};")
        uw_l = QHBoxLayout(url_wrap)
        uw_l.setContentsMargins(1, 1, 1, 1)
        self._url_edit = QLineEdit(url)
        self._url_edit.setReadOnly(True)
        self._url_edit.setStyleSheet(
            f"background:{p['surface']};color:{p['text']};border:none;"
            f"padding:6px 8px;font-family:'Segoe UI';font-size:10px;"
        )
        uw_l.addWidget(self._url_edit)
        il.addWidget(url_wrap)
        il.addSpacing(6)

        self._net_lbl = QLabel("WiFi only — click Tunnel to use on any network")
        self._net_lbl.setAlignment(Qt.AlignCenter)
        self._net_lbl.setStyleSheet(
            f"color:{p['text3']};font-size:9px;"
            f"font-family:'Segoe UI';background:{p['bg']};")
        il.addWidget(self._net_lbl)
        il.addSpacing(12)

        self._tunnel_btn = QPushButton("  Tunnel  (works anywhere, free)")
        self._tunnel_btn.setCursor(Qt.PointingHandCursor)
        self._tunnel_btn.setStyleSheet(
            f"QPushButton {{ background:{p['info_bg']}; color:{p['info_fg']}; "
            f"border:1px solid {p['info_fg']}; padding:8px 14px; "
            f"font-family:'Segoe UI'; font-size:10px; }}"
            f"QPushButton:hover {{ background:{p['info_hd']}; }}"
        )
        self._tunnel_btn.clicked.connect(self._start_tunnel)
        il.addWidget(self._tunnel_btn)
        il.addSpacing(16)

        close_btn = QPushButton("I'm connected / close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background:{p['btn_bg']}; color:{p['text2']}; "
            f"border:1px solid {p['border']}; padding:10px 24px; "
            f"font-family:'Segoe UI'; font-size:11px; }}"
            f"QPushButton:hover {{ background:{p['hover']}; }}"
        )
        close_btn.clicked.connect(self.hide)
        il.addWidget(close_btn, 0, Qt.AlignCenter)

    def _refresh_qr(self, url: str):
        if QR_OK:
            px = _draw_qr_pixmap(url, 500)
            if px:
                self._qr_label.setPixmap(px)
        else:
            self._qr_label.setText(
                "Install qrcode to show a scannable code:\n"
                "pip install qrcode")
            self._qr_label.setStyleSheet(
                "background:#FFFFFF;color:#333;font-size:10px;")

    def _update_url(self, url: str):
        self._url = url
        self._url_edit.setText(url)
        self._refresh_qr(url)

    def _start_tunnel(self):
        p = self.app._p()
        self._tunnel_btn.setEnabled(False)
        self._tunnel_btn.setText("Starting…")
        port = self.app._mobile_server.port if self.app._mobile_server else 0
        log.info("Tunnel requested on port %d", port)

        def _gui(fn):
            """Post fn() to the GUI thread via self's event loop."""
            QTimer.singleShot(0, self, fn)

        def _do():
            if not _find_cloudflared():
                log.info("cloudflared not found — downloading")
                _gui(lambda: self._tunnel_btn.setText("Downloading cloudflared… 0%"))
                try:
                    _download_cloudflared(
                        lambda pct: _gui(lambda v=pct:
                            self._tunnel_btn.setText(f"Downloading cloudflared… {v}%")))
                except Exception as exc:
                    log.error("cloudflared download failed: %s", exc)
                    _gui(lambda e=str(exc): self._on_tunnel_err(e))
                    return
            else:
                log.info("cloudflared found at %s", _find_cloudflared())
            _gui(lambda: self._tunnel_btn.setText("Connecting to Cloudflare…"))
            try:
                proc = _launch_cf_tunnel(
                    port,
                    on_url=lambda u: _gui(lambda u=u: self._on_tunnel_url(u)),
                    on_error=lambda e: _gui(lambda e=e: self._on_tunnel_err(e)),
                )
                if self.app._mobile_server:
                    self.app._mobile_server._cf_proc = proc
            except Exception as exc:
                log.error("_launch_cf_tunnel raised: %s", exc)
                _gui(lambda e=str(exc): self._on_tunnel_err(e))

        threading.Thread(target=_do, daemon=True).start()

    def _on_tunnel_url(self, url: str):
        p = self.app._p()
        log.info("Tunnel active: %s", url)
        self._tunnel_btn.setText("Tunnel active")
        self._tunnel_btn.setStyleSheet(
            f"QPushButton {{ background:{p['green_l']}; color:{p['green']}; "
            f"border:1px solid {p['green']}; padding:8px 14px; "
            f"font-family:'Segoe UI'; font-size:10px; }}"
        )
        self._net_lbl.setText("Tunnel active — works on any network")
        self._update_url(url)

    def _on_tunnel_err(self, msg: str):
        log.error("Tunnel error: %s", msg)
        p = self.app._p()
        self._tunnel_btn.setEnabled(True)
        self._tunnel_btn.setCursor(Qt.PointingHandCursor)
        self._tunnel_btn.setText(f"Error — {msg[:55]}")
        self._tunnel_btn.setStyleSheet(
            f"QPushButton {{ background:{p['danger_bg']}; color:{p['danger_fg']}; "
            f"border:1px solid {p['danger_fg']}; padding:8px 14px; "
            f"font-family:'Segoe UI'; font-size:10px; }}"
            f"QPushButton:hover {{ background:{p['danger_hd']}; }}"
        )

    def closeEvent(self, event):
        self.hide()
        event.ignore()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=== Survey Sentence Generator starting ===")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
