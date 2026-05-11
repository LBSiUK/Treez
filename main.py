"""
Survey Sentence Generator
Tap phrase buttons to build a description, then GO types it automatically.

Dependencies: pip install pyautogui pyperclip openai
"""
import http.server
import json
import logging
import os
import socket
import socketserver as _sserver
import sys
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

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

# ── Paths ─────────────────────────────────────────────────────────────────────
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

# ── Light palette ─────────────────────────────────────────────────────────────
LT = dict(
    bg="#FFFFFF", surface="#F1F5F9",
    hdr="#1E3A5F", hdr_h="#2D4E7A",
    text="#0F172A", text2="#1E293B", text3="#334155",
    border="#000000", hover="#E2E8F0",
    btn_bg="#FFFFFF", btn_hov="#E8EDF3",
    green="#059669", green_d="#047857", green_l="#ECFDF5", green_m="#A7F3D0",
    danger_bg="#FEF2F2", danger_fg="#DC2626", danger_hd="#FEE2E2",
    info_bg="#EFF6FF", info_fg="#2563EB", info_hd="#DBEAFE", info_dk="#1D4ED8",
    edit_bg="#FFFBEB", edit_bd="#D97706", edit_act="#F59E0B",
    weight="normal",
)

# ── Dark / Field palette ──────────────────────────────────────────────────────
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

# ── Category accent colors (light_bg, light_fg, dark_bg, dark_fg) ─────────────
CAT_COLORS = [
    ("#E0F2FE", "#0369A1", "#0C4A6E", "#38BDF8"),  # sky
    ("#D1FAE5", "#065F46", "#022C22", "#34D399"),  # emerald
    ("#FEF3C7", "#92400E", "#451A03", "#FCD34D"),  # amber
    ("#FEE2E2", "#991B1B", "#450A0A", "#F87171"),  # red
    ("#EDE9FE", "#4C1D95", "#2E1065", "#A78BFA"),  # violet
    ("#FCE7F3", "#831843", "#500724", "#F472B6"),  # pink
    ("#CCFBF1", "#134E4A", "#042F2E", "#5EEAD4"),  # teal
    ("#FFEDD5", "#7C2D12", "#431407", "#FB923C"),  # orange
]

GROK_BASE_URL = "https://api.groq.com/openai/v1"
GROK_MODEL    = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

APP_VERSION  = "1.0.2"
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


# ── Auto-updater ──────────────────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _hover(w, nbg, hbg, nfg, hfg=None):
    hfg = hfg or nfg
    w.bind("<Enter>", lambda _e: w.config(bg=hbg, fg=hfg))
    w.bind("<Leave>", lambda _e: w.config(bg=nbg, fg=nfg))


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _draw_qr(canvas: tk.Canvas, url: str, size: int):
    if not QR_OK:
        return
    qr = _qrcode_lib.QRCode(
        error_correction=_qrcode_lib.constants.ERROR_CORRECT_M,
        box_size=1, border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    cell = max(1, size // n)
    for r, row in enumerate(matrix):
        for c, val in enumerate(row):
            if val:
                x0, y0 = c * cell, r * cell
                canvas.create_rectangle(x0, y0, x0 + cell, y0 + cell,
                                        fill="#000000", outline="")


_CF_EXE = os.path.join(BASE_DIR, "cloudflared.exe")
_CF_DL  = ("https://github.com/cloudflare/cloudflared/releases/latest"
           "/download/cloudflared-windows-amd64.exe")
_CF_URL_RE = __import__("re").compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


def _find_cloudflared() -> str | None:
    import shutil
    if os.path.exists(_CF_EXE):
        return _CF_EXE
    return shutil.which("cloudflared") or shutil.which("cloudflared.exe")


def _download_cloudflared(on_progress) -> str:
    """Download cloudflared.exe; calls on_progress(pct) periodically."""
    import urllib.request
    on_progress(0)
    with urllib.request.urlopen(_CF_DL, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        received = 0
        chunk = 65536
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


def _launch_cf_tunnel(port: int, on_url, on_error) -> "subprocess.Popen":
    import subprocess
    cf = _find_cloudflared()
    proc = subprocess.Popen(
        [cf, "--no-autoupdate", "tunnel", "--url", f"http://localhost:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    def _read():
        try:
            for line in proc.stdout:
                m = _CF_URL_RE.search(line)
                if m:
                    on_url(m.group())
                    return
            on_error("Tunnel closed without providing a URL")
        except Exception as exc:
            on_error(str(exc))

    threading.Thread(target=_read, daemon=True).start()
    return proc


# ── Mobile HTTP server ────────────────────────────────────────────────────────

class _MobileHTTPServer(_sserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

    def __init__(self, addr, handler, ms):
        super().__init__(addr, handler)
        self.ms = ms


class _MobileHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # silence request logs

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
        raw = self.rfile.read(length)
        if self.path == "/update":
            try:
                data = json.loads(raw)
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
    def __init__(self, app: "App"):
        self.app = app
        self._text = app.sentence_text.get("1.0", "end-1c")
        self._version = 0
        self._lock = threading.Lock()
        self._cf_proc = None
        self._httpd = _MobileHTTPServer(("", 0), _MobileHandler, self)
        self.port = self._httpd.server_address[1]
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
        """Called from the main thread when the desktop sentence changes."""
        with self._lock:
            if self._text == text:
                return
            self._text = text
            self._version += 1

    def phone_update(self, text: str) -> int:
        """Called from an HTTP thread; schedules a main-thread update."""
        with self._lock:
            self._text = text
            self._version += 1
            v = self._version
        self.app.root.after(0, lambda t=text: self.app._apply_mobile_text(t))
        return v

    def phone_go(self):
        self.app.root.after(0, self.app._go)


# ── Scrollable frame ──────────────────────────────────────────────────────────

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg="#F1F5F9", **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._canvas = tk.Canvas(self, bd=0, highlightthickness=0, bg=bg)
        sb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self.inner = tk.Frame(self._canvas, bg=bg)
        self._win = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self._canvas.configure(yscrollcommand=sb.set)
        self.inner.bind(
            "<Configure>",
            lambda _: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        sb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._canvas.bind("<MouseWheel>", self._scroll)
        self.inner.bind("<MouseWheel>", self._scroll)

    def _on_canvas_resize(self, event):
        self._canvas.itemconfig(self._win, width=event.width)

    def _scroll(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def bind_scroll(self, widget):
        widget.bind("<MouseWheel>", self._scroll)
        for child in widget.winfo_children():
            self.bind_scroll(child)


# ── Main application ──────────────────────────────────────────────────────────

class App:
    PHRASE_COLS = 3

    def __init__(self, root: tk.Tk):
        self.root         = root
        self.settings     = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self.phrases_data = load_json(PHRASES_FILE, DEFAULT_PHRASES)
        self.usage        = load_json(USAGE_FILE, {})
        self.phrase_history: list[str] = []
        self._resize_job  = None
        self.edit_mode    = False
        self._tab_frames: dict = {}
        self._active_tab: str | None = None
        self.sugg_container = None
        self._mobile_server: "MobileServer | None" = None
        self._mobile_win: "MobileWindow | None" = None
        self._mobile_updating = False
        self._mobile_sync_job = None

        root.title("Survey Sentence Generator")
        root.geometry(self.settings.get("geometry", DEFAULT_SETTINGS["geometry"]))
        root.state("zoomed")
        root.minsize(900, 580)

        self._configure_ttk()

        if not DEPS_OK:
            messagebox.showwarning(
                "Missing packages",
                "pyautogui or pyperclip not found.\n\n"
                "Run:  pip install pyautogui pyperclip\n\n"
                "The GO button will not work until installed.",
            )

        self._build_ui()
        root.bind("<Configure>", self._on_resize)

    # ── Palette helpers ───────────────────────────────────────────────────────

    def _p(self):
        return DK if self.settings.get("dark_mode", False) else LT

    def _cat_color(self, cat_idx: int):
        cats = self.phrases_data.get("categories", [])
        stored = cats[cat_idx].get("color_idx") if cat_idx < len(cats) else None
        key = (stored if stored is not None else cat_idx) % len(CAT_COLORS)
        cc = CAT_COLORS[key]
        if self.settings.get("dark_mode", False):
            return cc[2], cc[3]
        return cc[0], cc[1]

    # ── ttk scrollbar style ───────────────────────────────────────────────────

    def _configure_ttk(self):
        p = self._p()
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Vertical.TScrollbar",
            background=p["hover"], troughcolor=p["surface"],
            borderwidth=0, arrowcolor=p["text3"], relief="flat", width=8,
        )
        s.map("Vertical.TScrollbar", background=[("active", p["text3"])])

    # ── Full rebuild (for theme toggle) ───────────────────────────────────────

    def _full_rebuild(self):
        saved = ""
        if hasattr(self, "sentence_text"):
            try:
                saved = self.sentence_text.get("1.0", "end-1c")
            except Exception:
                pass
        for w in self.root.winfo_children():
            w.destroy()
        self._tab_frames    = {}
        self._active_tab    = None
        self.sugg_container = None
        self._configure_ttk()
        self._build_ui()
        if saved:
            self.sentence_text.insert("1.0", saved)

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        p    = self._p()
        fs   = self.settings.get("font_size", 14)
        dark = self.settings.get("dark_mode", False)

        self.root.configure(bg=p["bg"])

        # Pack bottom items first so they anchor to bottom before content expands
        tk.Frame(self.root, bg=p["border"], height=1).pack(side="bottom", fill="x")
        status_bar = tk.Frame(self.root, bg=p["surface"], padx=18, pady=7)
        status_bar.pack(side="bottom", fill="x")

        self.wifi_label = tk.Label(
            status_bar, text="",
            font=("Segoe UI", 13), bg=p["surface"],
        )
        self.wifi_label.pack(side="left", padx=(0, 10))

        self.status_var = tk.StringVar(value="Ready  |  v" + APP_VERSION)
        tk.Label(status_bar, textvariable=self.status_var,
                 font=("Segoe UI", 10), bg=p["surface"], fg=p["text3"]).pack(side="left")

        self._wifi_online: bool | None = None
        self._poll_wifi()

        tk.Frame(self.root, bg=p["border"], height=1).pack(side="bottom", fill="x")
        action_dock = tk.Frame(self.root, bg=p["surface"], padx=20, pady=14)
        action_dock.pack(side="bottom", fill="x")

        for label, cmd in [("Clear", self._clear), ("Undo", self._undo)]:
            b = tk.Button(
                action_dock, text=label,
                font=("Segoe UI", fs + 8, "bold"),
                command=cmd,
                bg=p["btn_bg"], fg=p["text2"],
                activebackground=p["hover"], activeforeground=p["text"],
                relief="flat", padx=24, pady=14, cursor="hand2",
                highlightthickness=1, highlightbackground=p["border"],
            )
            b.pack(side="left", padx=(0, 10))
            _hover(b, p["btn_bg"], p["hover"], p["text2"], p["text"])

        go = tk.Button(
            action_dock, text="GO",
            font=("Segoe UI", fs + 8, "bold"),
            command=self._go,
            bg=p["green"], fg="#FFFFFF",
            activebackground=p["green_d"], activeforeground="#FFFFFF",
            relief="flat", padx=72, pady=14, cursor="hand2",
        )
        go.pack(side="right")
        _hover(go, p["green"], p["green_d"], "#FFFFFF", "#FFFFFF")

        self.clean_btn = tk.Button(
            action_dock, text="Clean",
            font=("Segoe UI", fs + 8, "bold"),
            command=self._clean,
            bg=p["info_fg"], fg="#FFFFFF",
            activebackground=p["info_dk"], activeforeground="#FFFFFF",
            relief="flat", padx=30, pady=14, cursor="hand2",
        )
        self.clean_btn.pack(side="right", padx=(0, 14))
        _hover(self.clean_btn, p["info_fg"], p["info_dk"], "#FFFFFF", "#FFFFFF")

        # Header
        header = tk.Frame(self.root, bg=p["hdr"], padx=20, pady=14)
        header.pack(side="top", fill="x")

        tk.Label(header, text="Survey Sentence Generator",
                 font=("Segoe UI", 15, "bold"),
                 bg=p["hdr"], fg="#FFFFFF").pack(side="left")
        tk.Label(header, text=f"v{APP_VERSION}",
                 font=("Segoe UI", 10),
                 bg=p["hdr"], fg="#6B8BB5").pack(side="left", padx=(8, 0))

        self.header = header

        self.dark_btn = self._header_btn(
            header,
            "Field Mode ON" if dark else "Field Mode",
            self._toggle_dark,
        )
        self.dark_btn.pack(side="right", padx=(8, 0))
        if dark:
            self.dark_btn.config(bg=p["edit_act"], fg="#000000")

        self.edit_btn = self._header_btn(header, "Edit Phrases", self._toggle_edit)
        self.edit_btn.pack(side="right", padx=(8, 0))
        self._header_btn(header, "Mobile", self._open_mobile).pack(side="right", padx=(8, 0))
        self._header_btn(header, "Settings", self._open_settings).pack(side="right")

        # Sentence panel
        tk.Frame(self.root, bg=p["border"], height=1).pack(side="top", fill="x")
        sent_panel = tk.Frame(self.root, bg=p["bg"], padx=20, pady=12)
        sent_panel.pack(side="top", fill="x")

        tk.Label(sent_panel, text="GENERATED SENTENCE",
                 font=("Segoe UI", 9, "bold"),
                 bg=p["bg"], fg=p["text3"]).pack(anchor="w")

        text_wrap = tk.Frame(sent_panel, bg=p["border"], padx=1, pady=1)
        text_wrap.pack(fill="x", pady=(6, 0))

        self.sentence_text = tk.Text(
            text_wrap, height=3,
            font=("Segoe UI", fs + 1, p["weight"]),
            wrap="word", relief="flat", bd=0,
            padx=14, pady=12,
            bg=p["btn_bg"], fg=p["text"],
            insertbackground=p["green"],
            selectbackground=p["hover"],
            selectforeground=p["text"],
        )
        self.sentence_text.pack(fill="x")
        self.sentence_text.bind("<KeyRelease>",
                                lambda _: self._sync_to_mobile(debounce=True))

        # Suggestion strip — always packed, zero height when empty
        self.sugg_container = tk.Frame(self.root, bg=p["surface"])
        self.sugg_container.pack(side="top", fill="x")

        # Tab strip
        tk.Frame(self.root, bg=p["border"], height=1).pack(side="top", fill="x")
        self.tab_strip = tk.Frame(self.root, bg=p["surface"])
        self.tab_strip.pack(side="top", fill="x")
        tk.Frame(self.root, bg=p["border"], height=1).pack(side="top", fill="x")

        # Content area
        self.content_area = tk.Frame(self.root, bg=p["surface"])
        self.content_area.pack(fill="both", expand=True)

        self._rebuild_tabs()

    # ── Header button helper ──────────────────────────────────────────────────

    def _header_btn(self, parent, text, command):
        p = self._p()
        btn = tk.Button(
            parent, text=f"  {text}  ",
            font=("Segoe UI", 10),
            command=command,
            bg=p["hdr"], fg="#FFFFFF",
            activebackground=p["hdr_h"], activeforeground="#FFFFFF",
            relief="flat", padx=4, pady=6, cursor="hand2",
            highlightthickness=1, highlightbackground="#4A6FA5",
        )
        btn.bind("<Enter>", lambda _: btn.config(bg=p["hdr_h"]))
        btn.bind("<Leave>", lambda _: btn.config(bg=p["hdr"]))
        return btn

    # ── WiFi indicator ────────────────────────────────────────────────────────

    def _poll_wifi(self):
        def check():
            online = _is_online()
            self.root.after(0, lambda: self._apply_wifi(online))
        threading.Thread(target=check, daemon=True).start()
        self.root.after(10_000, self._poll_wifi)

    def _apply_wifi(self, online: bool):
        if online == self._wifi_online:
            return
        self._wifi_online = online
        p = self._p()
        if online:
            self.wifi_label.config(text="▲", fg="#22C55E")
        else:
            self.wifi_label.config(text="✕", fg="#EF4444")
        self._update_clean_btn()

    def _update_clean_btn(self):
        p = self._p()
        if self._wifi_online:
            self.clean_btn.config(
                state="normal", cursor="hand2",
                bg=p["info_fg"], fg="#FFFFFF",
            )
            _hover(self.clean_btn, p["info_fg"], p["info_dk"], "#FFFFFF", "#FFFFFF")
        else:
            self.clean_btn.config(
                state="disabled", cursor="",
                bg=p["hover"], fg=p["text3"],
            )
            self.clean_btn.unbind("<Enter>")
            self.clean_btn.unbind("<Leave>")

    # ── Dark mode toggle ──────────────────────────────────────────────────────

    def _toggle_dark(self):
        self.settings["dark_mode"] = not self.settings.get("dark_mode", False)
        save_json(SETTINGS_FILE, self.settings)
        self.root.after(0, self._full_rebuild)

    # ── Tab building ──────────────────────────────────────────────────────────

    def _rebuild_tabs(self):
        for w in self.tab_strip.winfo_children():
            w.destroy()
        for w in self.content_area.winfo_children():
            w.destroy()

        self._tab_frames = {}
        self._active_tab = None
        p  = self._p()
        fs = self.settings.get("font_size", 14)

        for cat_idx, cat in enumerate(self.phrases_data.get("categories", [])):
            name = cat["name"]
            cat_bg, cat_fg = self._cat_color(cat_idx)

            tab_wrap = tk.Frame(self.tab_strip, bg=p["surface"])
            tab_wrap.pack(side="left")
            if cat_idx > 0:
                tk.Frame(tab_wrap, bg=p["border"], width=1).pack(side="left", fill="y")

            btn = tk.Button(
                tab_wrap, text=f"  {name}  ",
                font=("Segoe UI", 11),
                bg=p["surface"], fg=p["text2"],
                activebackground=cat_bg, activeforeground=cat_fg,
                relief="flat", bd=0, pady=11, cursor="hand2",
                highlightthickness=0,
                command=lambda n=name: self._select_tab(n),
            )
            btn.pack(side="left")

            if self.edit_mode:
                gear = tk.Button(
                    tab_wrap, text=" ⚙ ",
                    font=("Segoe UI", 9),
                    command=lambda ci=cat_idx: self._edit_category_direct(ci),
                    bg=p["edit_act"], fg="#1C1400",
                    activebackground="#E88E00", activeforeground="#1C1400",
                    relief="flat", padx=2, pady=11, cursor="hand2",
                )
                gear.pack(side="left")
                _hover(gear, p["edit_act"], "#E88E00", "#1C1400")

            indicator = tk.Frame(tab_wrap, height=3, bg=p["surface"])
            indicator.pack(fill="x", side="bottom")

            content_frame = tk.Frame(self.content_area, bg=p["surface"])
            sf = ScrollableFrame(content_frame, bg=p["surface"])
            sf.pack(fill="both", expand=True, padx=8, pady=8)
            self._fill_tab(sf, cat, fs, cat_idx, cat_bg, cat_fg)

            self._tab_frames[name] = {
                "btn": btn, "indicator": indicator,
                "frame": content_frame, "cat_fg": cat_fg,
            }

        if self.edit_mode:
            tk.Frame(self.tab_strip, bg=p["border"], width=1).pack(side="left", fill="y")
            add_cat = tk.Button(
                self.tab_strip, text="  ＋ Category  ",
                font=("Segoe UI", 11),
                command=self._new_category_direct,
                bg=p["green_l"], fg=p["green"],
                activebackground=p["green_m"], activeforeground=p["green_d"],
                relief="flat", pady=11, padx=8, cursor="hand2",
                highlightthickness=0,
            )
            add_cat.pack(side="left")
            _hover(add_cat, p["green_l"], p["green_m"], p["green"], p["green_d"])

        if self._tab_frames:
            self._select_tab(next(iter(self._tab_frames)))

        threading.Thread(target=self._bg_update_check, daemon=True).start()

    # ── Update check ──────────────────────────────────────────────────────────

    def _bg_update_check(self):
        try:
            tag, exe_url = _fetch_latest_release()
            if tag and exe_url and _version_newer(tag, APP_VERSION):
                self.root.after(0, lambda: self._show_update_banner(tag, exe_url))
        except Exception:
            pass

    def _show_update_banner(self, tag: str, exe_url: str):
        p = self._p()
        btn = tk.Button(
            self.header,
            text=f"  ↑ Update v{tag}  ",
            font=("Segoe UI", 10, "bold"),
            command=lambda: self._prompt_update(tag, exe_url),
            bg="#F59E0B", fg="#1C1400",
            activebackground="#D97706", activeforeground="#1C1400",
            relief="flat", padx=4, pady=6, cursor="hand2",
        )
        btn.pack(side="right", padx=(8, 0))
        _hover(btn, "#F59E0B", "#D97706", "#1C1400")

    def _prompt_update(self, tag: str, exe_url: str):
        frozen = getattr(sys, "frozen", False)
        if frozen:
            ok = messagebox.askyesno(
                "Update available",
                f"Version {tag} is available.\n\nDownload and restart now?",
                parent=self.root,
            )
            if ok:
                self.status_var.set(f"Downloading v{tag}…")
                self.root.update()
                threading.Thread(target=_perform_update, args=(exe_url,), daemon=True).start()
        else:
            messagebox.showinfo(
                "Update available",
                f"Version {tag} is available.\n\n"
                f"Download it from:\nhttps://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest",
                parent=self.root,
            )

    def _select_tab(self, name: str):
        p = self._p()
        if self._active_tab and self._active_tab in self._tab_frames:
            prev = self._tab_frames[self._active_tab]
            prev["btn"].config(bg=p["surface"], fg=p["text2"], font=("Segoe UI", 11))
            prev["indicator"].config(bg=p["surface"])
            prev["frame"].pack_forget()

        self._active_tab = name
        cur = self._tab_frames[name]
        cur["btn"].config(bg=p["bg"], fg=cur["cat_fg"], font=("Segoe UI", 11, "bold"))
        cur["indicator"].config(bg=cur["cat_fg"])
        cur["frame"].pack(fill="both", expand=True)

    # ── Fill tab ──────────────────────────────────────────────────────────────

    def _fill_tab(self, sf: ScrollableFrame, cat: dict, fs: int,
                  cat_idx: int, cat_bg: str, cat_fg: str):
        p      = self._p()
        weight = p["weight"]
        cols   = cat.get("cols", self.PHRASE_COLS)

        if self.edit_mode:
            phrases = cat["phrases"]
            for i, phrase in enumerate(phrases):
                r, c = divmod(i, cols)
                cell = tk.Frame(sf.inner, bg=p["edit_bg"],
                                highlightthickness=1, highlightbackground=p["edit_bd"])
                cell.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
                sf.inner.columnconfigure(c, weight=1, minsize=200)
                sf.inner.rowconfigure(r, minsize=64)

                pb = tk.Button(
                    cell, text=phrase,
                    font=("Segoe UI", fs, weight),
                    wraplength=480, justify="left", anchor="w",
                    command=lambda ph=phrase, ci=cat_idx: self._add_phrase_tracked(ph, ci),
                    bg=p["edit_bg"], fg=p["text"],
                    activebackground=p["hover"], activeforeground=p["text"],
                    relief="flat", padx=10, pady=18, cursor="hand2",
                )
                pb.pack(side="left", fill="both", expand=True)
                _hover(pb, p["edit_bg"], p["hover"], p["text"])

                eb = tk.Button(
                    cell, text="Edit",
                    font=("Segoe UI", 10, "bold"),
                    command=lambda ci=cat_idx, ph=phrase: self._edit_phrase_direct(ci, ph),
                    bg=p["info_bg"], fg=p["info_fg"],
                    activebackground=p["info_hd"], activeforeground=p["info_fg"],
                    relief="flat", padx=12, pady=18, cursor="hand2",
                    highlightthickness=1, highlightbackground=p["info_fg"],
                )
                eb.pack(side="right", padx=(0, 1))
                _hover(eb, p["info_bg"], p["info_hd"], p["info_fg"])

                db = tk.Button(
                    cell, text="Del",
                    font=("Segoe UI", 10, "bold"),
                    command=lambda ci=cat_idx, ph=phrase: self._delete_phrase_direct(ci, ph),
                    bg=p["danger_bg"], fg=p["danger_fg"],
                    activebackground=p["danger_hd"], activeforeground=p["danger_fg"],
                    relief="flat", padx=12, pady=18, cursor="hand2",
                    highlightthickness=1, highlightbackground=p["danger_fg"],
                )
                db.pack(side="right")
                _hover(db, p["danger_bg"], p["danger_hd"], p["danger_fg"])
                sf.bind_scroll(cell)

            ar, ac = divmod(len(phrases), cols)
            add = tk.Button(
                sf.inner, text="+ Add phrase",
                font=("Segoe UI", fs, "bold"),
                command=lambda ci=cat_idx: self._add_phrase_direct(ci),
                bg=p["green_l"], fg=p["green"],
                activebackground=p["green_m"], activeforeground=p["green_d"],
                relief="flat", padx=10, pady=18, cursor="hand2",
                highlightthickness=1, highlightbackground=p["green"],
            )
            add.grid(row=ar, column=ac, padx=6, pady=6, sticky="nsew")
            _hover(add, p["green_l"], p["green_m"], p["green"], p["green_d"])
            sf.bind_scroll(add)

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
                btn = tk.Button(
                    sf.inner,
                    text=label,
                    font=("Segoe UI", fs, weight),
                    wraplength=500, justify="left", anchor="w",
                    command=lambda ph=phrase, ci=cat_idx: self._add_phrase_tracked(ph, ci),
                    bg=cat_bg, fg=cat_fg,
                    activebackground=p["hover"], activeforeground=p["text"],
                    relief="flat",
                    padx=16, pady=20,
                    cursor="hand2",
                    highlightthickness=1, highlightbackground=cat_fg,
                )
                btn.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
                sf.inner.columnconfigure(c, weight=1, minsize=200)
                sf.inner.rowconfigure(r, minsize=64)
                _hover(btn, cat_bg, p["hover"], cat_fg, p["text"])
                sf.bind_scroll(btn)

    # ── Phrase tracking + suggestions ─────────────────────────────────────────

    def _add_phrase_tracked(self, phrase: str, cat_idx: int):
        self._add_phrase(phrase)
        cat_name = self.phrases_data["categories"][cat_idx]["name"]
        key = f"{cat_name}|{phrase}"
        self.usage[key] = self.usage.get(key, 0) + 1
        save_json(USAGE_FILE, self.usage)
        self._update_suggestions(cat_idx)

    def _update_suggestions(self, from_cat_idx: int):
        p      = self._p()
        fs     = max(self.settings.get("font_size", 14) - 2, 10)
        weight = p["weight"]

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

        for w in self.sugg_container.winfo_children():
            w.destroy()

        if not top:
            return

        tk.Frame(self.sugg_container, bg=p["border"], height=1).pack(fill="x")
        row = tk.Frame(self.sugg_container, bg=p["surface"], padx=12, pady=8)
        row.pack(fill="x")
        tk.Label(row, text="Suggest:",
                 font=("Segoe UI", 9), bg=p["surface"], fg=p["text3"],
                 ).pack(side="left", padx=(0, 8))

        for _cnt, ci, ph in top:
            cbg, cfg = self._cat_color(ci)
            short = ph[:36] + ("…" if len(ph) > 36 else "")
            b = tk.Button(
                row, text=short,
                font=("Segoe UI", fs, weight),
                command=lambda x=ph, idx=ci: self._add_phrase_tracked(x, idx),
                bg=cbg, fg=cfg,
                activebackground=p["hover"], activeforeground=p["text"],
                relief="flat", padx=10, pady=6, cursor="hand2",
                highlightthickness=1, highlightbackground=cfg,
            )
            b.pack(side="left", padx=(0, 6))
            _hover(b, cbg, p["hover"], cfg, p["text"])

    # ── Sentence actions ──────────────────────────────────────────────────────

    def _add_phrase(self, phrase: str):
        current = self.sentence_text.get("1.0", "end-1c")
        sep = " " if current.rstrip() else ""
        self.sentence_text.insert("end", sep + phrase)
        self.phrase_history.append(phrase)
        self._sync_to_mobile()

    def _undo(self):
        if not self.phrase_history:
            return
        self.phrase_history.pop()
        self.sentence_text.delete("1.0", "end")
        self.sentence_text.insert("1.0", " ".join(self.phrase_history))
        self._sync_to_mobile()

    def _clear(self):
        self.sentence_text.delete("1.0", "end")
        self.phrase_history.clear()
        if self.sugg_container:
            for w in self.sugg_container.winfo_children():
                w.destroy()
        self._sync_to_mobile()

    # ── Edit mode ─────────────────────────────────────────────────────────────

    def _toggle_edit(self):
        p = self._p()
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.edit_btn.config(bg=p["edit_act"], fg="#1C1400",
                                 highlightbackground=p["edit_bd"])
            self.edit_btn.bind("<Enter>", lambda _: self.edit_btn.config(bg="#E88E00"))
            self.edit_btn.bind("<Leave>", lambda _: self.edit_btn.config(bg=p["edit_act"]))
            self.status_var.set("Edit mode — Del to remove, Edit to rename, + to add")
        else:
            self.edit_btn.config(bg=p["hdr"], fg="#FFFFFF",
                                 highlightbackground="#4A6FA5")
            self.edit_btn.bind("<Enter>", lambda _: self.edit_btn.config(bg=p["hdr_h"]))
            self.edit_btn.bind("<Leave>", lambda _: self.edit_btn.config(bg=p["hdr"]))
            self.status_var.set("Ready")
        self._rebuild_tabs()

    def _new_category_direct(self):
        dlg = CategoryDialog(self.root, self)
        self.root.wait_window(dlg)
        if dlg.result:
            name, color_idx = dlg.result
            self.phrases_data["categories"].append(
                {"name": name, "phrases": [], "color_idx": color_idx}
            )
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()
            self._select_tab(name)

    def _edit_category_direct(self, cat_idx: int):
        cat = self.phrases_data["categories"][cat_idx]
        default_color = cat.get("color_idx", cat_idx % len(CAT_COLORS))
        dlg = CategoryDialog(self.root, self, name=cat["name"], color_idx=default_color,
                             allow_delete=True)
        self.root.wait_window(dlg)
        if dlg.result == "delete":
            self.phrases_data["categories"].pop(cat_idx)
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()
        elif dlg.result:
            new_name, new_color = dlg.result
            cat["name"] = new_name
            cat["color_idx"] = new_color
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()
            if new_name in self._tab_frames:
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
        new_text = simpledialog.askstring(
            "Edit Phrase", "Phrase text:", initialvalue=phrase, parent=self.root
        )
        if new_text and new_text.strip() and new_text.strip() != phrase:
            phrases[phrases.index(phrase)] = new_text.strip()
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()

    def _add_phrase_direct(self, cat_idx: int):
        text = simpledialog.askstring("New Phrase", "Phrase text:", parent=self.root)
        if text and text.strip():
            self.phrases_data["categories"][cat_idx]["phrases"].append(text.strip())
            save_json(PHRASES_FILE, self.phrases_data)
            self._rebuild_tabs()

    # ── GO ────────────────────────────────────────────────────────────────────

    def _go(self):
        sentence = self.sentence_text.get("1.0", "end-1c").strip()
        if not sentence:
            return
        if not DEPS_OK:
            messagebox.showerror("Cannot paste", "Run: pip install pyautogui pyperclip")
            return
        delay_ms = int(float(self.settings.get("delay", 1.0)) * 1000)
        self.status_var.set("Minimising…")
        self.root.update()
        self.root.iconify()
        self.root.after(delay_ms, lambda: self._do_paste(sentence))

    def _do_paste(self, sentence: str):
        try:
            pyperclip.copy(sentence)
            pyautogui.hotkey("ctrl", "v")
        except Exception as exc:
            self.root.deiconify()
            messagebox.showerror("Paste error", str(exc))
            return
        if self.settings.get("clear_after_go", True):
            self._clear()
        preview = sentence[:65] + ("…" if len(sentence) > 65 else "")
        self.status_var.set(f"Pasted: {preview}")

    # ── Clean (Groq AI) ───────────────────────────────────────────────────────

    def _clean(self):
        sentence = self.sentence_text.get("1.0", "end-1c").strip()
        if not sentence:
            return
        if not AI_OK:
            messagebox.showerror("Missing package", "Run:  pip install openai\n\nThen restart.")
            return
        api_key = GROQ_API_KEY

        p  = self._p()
        fs = self.settings.get("font_size", 14)
        self.clean_btn.config(text="Cleaning…", font=("Segoe UI", fs + 2, "bold"),
                              bg=p["hover"], fg=p["text3"], state="disabled", cursor="")
        self.clean_btn.unbind("<Enter>")
        self.clean_btn.unbind("<Leave>")
        self.status_var.set(f"Cleaning with Groq ({GROK_MODEL})…")
        threading.Thread(target=self._do_clean, args=(sentence, api_key), daemon=True).start()

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
            self.root.after(0, lambda: self._apply_clean(improved))
        except Exception as exc:
            log.exception("Clean API call failed")
            msg = str(exc)
            self.root.after(0, lambda: self._clean_error(msg))

    def _apply_clean(self, improved: str):
        self.sentence_text.delete("1.0", "end")
        self.sentence_text.insert("1.0", improved)
        self.phrase_history.clear()
        self._sync_to_mobile()
        self._restore_clean_btn()
        self.status_var.set("Sentence cleaned by Groq")

    def _clean_error(self, msg: str):
        self._restore_clean_btn()
        self.status_var.set(f"Clean failed — {msg[:90]}")

    def _restore_clean_btn(self):
        p  = self._p()
        fs = self.settings.get("font_size", 14)
        self.clean_btn.config(text="Clean", font=("Segoe UI", fs + 8, "bold"),
                              bg=p["info_fg"], fg="#FFFFFF", state="normal", cursor="hand2")
        _hover(self.clean_btn, p["info_fg"], p["info_dk"], "#FFFFFF", "#FFFFFF")

    # ── Mobile input ──────────────────────────────────────────────────────────

    def _open_mobile(self):
        if self._mobile_server is None:
            try:
                self._mobile_server = MobileServer(self)
            except Exception as exc:
                messagebox.showerror("Mobile server error", str(exc), parent=self.root)
                return
        ip  = _get_local_ip()
        url = f"http://{ip}:{self._mobile_server.port}/"
        if self._mobile_win is None or not self._mobile_win.winfo_exists():
            self._mobile_win = MobileWindow(self.root, self, url)
        else:
            self._mobile_win.lift()
            self._mobile_win.focus_force()

    def _stop_mobile(self):
        if self._mobile_server:
            self._mobile_server.stop()
            self._mobile_server = None
        self._mobile_win = None

    def _apply_mobile_text(self, text: str):
        """Apply text received from the phone; guards against echo loops."""
        current = self.sentence_text.get("1.0", "end-1c")
        if current == text:
            return
        self._mobile_updating = True
        self.sentence_text.delete("1.0", "end")
        self.sentence_text.insert("1.0", text)
        self._mobile_updating = False

    def _sync_to_mobile(self, debounce: bool = False):
        """Push the current sentence text to the mobile server."""
        if not self._mobile_server or self._mobile_updating:
            return
        if debounce:
            if self._mobile_sync_job:
                self.root.after_cancel(self._mobile_sync_job)
            self._mobile_sync_job = self.root.after(300, self._do_sync_to_mobile)
        else:
            self._do_sync_to_mobile()

    def _do_sync_to_mobile(self):
        self._mobile_sync_job = None
        if self._mobile_server and not self._mobile_updating:
            self._mobile_server.set_text(self.sentence_text.get("1.0", "end-1c"))

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsWindow(self.root, self)

    def _on_resize(self, event):
        if event.widget is not self.root:
            return
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(400, self._save_geometry)

    def _save_geometry(self):
        self.settings["geometry"] = self.root.geometry()
        save_json(SETTINGS_FILE, self.settings)


# ── Category dialog ───────────────────────────────────────────────────────────

class CategoryDialog(tk.Toplevel):
    """Name + colour picker for creating or editing a category."""

    def __init__(self, parent, app, name="", color_idx=0, allow_delete=False):
        super().__init__(parent)
        self.app = app
        self.result = None
        self._color_idx = color_idx

        p = app._p()
        dark = app.settings.get("dark_mode", False)
        self.title("Edit Category" if allow_delete else "New Category")
        self.configure(bg=p["bg"])
        self.resizable(False, False)
        self.grab_set()

        pad = dict(padx=24, pady=0)

        # ── Name ──────────────────────────────────────────────────────────
        tk.Frame(self, bg=p["bg"], height=20).pack()
        tk.Label(self, text="NAME", font=("Segoe UI", 8, "bold"),
                 bg=p["bg"], fg=p["text3"]).pack(anchor="w", **pad)

        name_wrap = tk.Frame(self, bg=p["border"], padx=1, pady=1)
        name_wrap.pack(fill="x", padx=24, pady=(4, 18))
        self._name_var = tk.StringVar(value=name)
        tk.Entry(name_wrap, textvariable=self._name_var,
                 font=("Segoe UI", 14), relief="flat", bd=0,
                 bg=p["btn_bg"], fg=p["text"],
                 insertbackground=p["green"],
                 ).pack(fill="x", padx=8, pady=8)

        # ── Colour swatches ───────────────────────────────────────────────
        tk.Label(self, text="COLOUR", font=("Segoe UI", 8, "bold"),
                 bg=p["bg"], fg=p["text3"]).pack(anchor="w", **pad)

        swatch_frame = tk.Frame(self, bg=p["bg"])
        swatch_frame.pack(padx=24, pady=(4, 20), anchor="w")

        self._swatch_btns = []
        for i, cc in enumerate(CAT_COLORS):
            bg_col = cc[2] if dark else cc[0]
            fg_col = cc[3] if dark else cc[1]
            r, c = divmod(i, 4)
            btn = tk.Button(
                swatch_frame,
                text="",
                bg=bg_col,
                activebackground=fg_col,
                relief="flat",
                width=5, height=2,
                cursor="hand2",
                command=lambda idx=i: self._pick_color(idx),
            )
            btn.grid(row=r, column=c, padx=4, pady=4)
            self._swatch_btns.append((btn, bg_col, fg_col))

        self._highlight_swatch(color_idx)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = tk.Frame(self, bg=p["bg"])
        btn_row.pack(fill="x", padx=24, pady=(0, 20))

        save = tk.Button(btn_row, text="Save",
                         font=("Segoe UI", 12, "bold"),
                         command=self._save,
                         bg=p["green"], fg="#FFFFFF",
                         activebackground=p["green_d"], activeforeground="#FFFFFF",
                         relief="flat", padx=24, pady=10, cursor="hand2")
        save.pack(side="left")
        _hover(save, p["green"], p["green_d"], "#FFFFFF", "#FFFFFF")

        cancel = tk.Button(btn_row, text="Cancel",
                           font=("Segoe UI", 12),
                           command=self.destroy,
                           bg=p["btn_bg"], fg=p["text2"],
                           activebackground=p["hover"], activeforeground=p["text"],
                           relief="flat", padx=24, pady=10, cursor="hand2",
                           highlightthickness=1, highlightbackground=p["border"])
        cancel.pack(side="left", padx=(10, 0))
        _hover(cancel, p["btn_bg"], p["hover"], p["text2"], p["text"])

        if allow_delete:
            delete = tk.Button(btn_row, text="Delete Category",
                               font=("Segoe UI", 12),
                               command=self._confirm_delete,
                               bg=p["danger_bg"], fg=p["danger_fg"],
                               activebackground=p["danger_hd"], activeforeground=p["danger_fg"],
                               relief="flat", padx=24, pady=10, cursor="hand2",
                               highlightthickness=1, highlightbackground=p["danger_fg"])
            delete.pack(side="right")
            _hover(delete, p["danger_bg"], p["danger_hd"], p["danger_fg"])

        self.update_idletasks()
        # centre over parent
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - self.winfo_width() // 2}+{py - self.winfo_height() // 2}")

    def _pick_color(self, idx: int):
        self._color_idx = idx
        self._highlight_swatch(idx)

    def _highlight_swatch(self, idx: int):
        p = self.app._p()
        for i, (btn, nbg, _nfg) in enumerate(self._swatch_btns):
            if i == idx:
                btn.config(highlightthickness=3,
                           highlightbackground=p["text"],
                           relief="solid")
            else:
                btn.config(highlightthickness=0, relief="flat")

    def _save(self):
        name = self._name_var.get().strip()
        if not name:
            return
        self.result = (name, self._color_idx)
        self.destroy()

    def _confirm_delete(self):
        p = self.app._p()
        name = self._name_var.get().strip() or "this category"
        if messagebox.askyesno("Delete category",
                               f"Delete '{name}' and all its phrases?",
                               parent=self):
            self.result = "delete"
            self.destroy()


# ── Settings window ───────────────────────────────────────────────────────────

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent: tk.Tk, app: App):
        super().__init__(parent)
        self.app = app
        p  = app._p()
        fs = app.settings.get("font_size", 14)
        self.title("Settings")
        self.geometry("1100x680")
        self.resizable(True, True)
        self.configure(bg=p["bg"])
        self.grab_set()

        # header
        hdr = tk.Frame(self, bg=p["hdr"], padx=20, pady=14)
        hdr.pack(side="top", fill="x")
        tk.Label(hdr, text="Settings", font=("Segoe UI", 14, "bold"),
                 bg=p["hdr"], fg="#FFFFFF").pack(side="left")

        # save button anchored to bottom
        tk.Frame(self, bg=p["border"], height=1).pack(side="bottom", fill="x")
        save_bar = tk.Frame(self, bg=p["bg"], padx=28, pady=16)
        save_bar.pack(side="bottom", fill="x")
        sb = tk.Button(save_bar, text="Save Settings", command=self._save,
                       font=("Segoe UI", fs, "bold"),
                       bg=p["green"], fg="#FFFFFF",
                       activebackground=p["green_d"], activeforeground="#FFFFFF",
                       relief="flat", padx=28, pady=11, cursor="hand2")
        sb.pack(side="left")
        _hover(sb, p["green"], p["green_d"], "#FFFFFF", "#FFFFFF")

        # content
        content = tk.Frame(self, bg=p["bg"])
        content.pack(side="top", fill="both", expand=True)

        def section(title):
            f = tk.Frame(content, bg=p["bg"])
            f.pack(fill="x", padx=28, pady=(22, 0))
            tk.Label(f, text=title, font=("Segoe UI", 8, "bold"),
                     bg=p["bg"], fg=p["text3"]).pack(anchor="w", pady=(0, 8))
            return f

        def rule():
            tk.Frame(content, bg=p["border"], height=1).pack(fill="x", padx=28, pady=(20, 0))

        r1 = tk.Frame(section("TYPING DELAY"), bg=p["bg"])
        r1.pack(fill="x")
        self.delay_var = tk.DoubleVar(value=app.settings.get("delay", 1.0))
        tk.Spinbox(r1, from_=0.1, to=30.0, increment=0.1, format="%.1f",
                   textvariable=self.delay_var, width=7,
                   font=("Segoe UI", fs), relief="flat",
                   bg=p["surface"], fg=p["text"],
                   highlightthickness=1, highlightbackground=p["border"],
                   ).pack(side="left")
        tk.Label(r1, text="seconds between GO and paste",
                 font=("Segoe UI", 11), fg=p["text2"], bg=p["bg"]).pack(side="left", padx=14)

        rule()

        self.clear_var = tk.BooleanVar(value=app.settings.get("clear_after_go", True))
        tk.Checkbutton(section("BEHAVIOUR"), text="Clear sentence automatically after GO",
                       variable=self.clear_var,
                       font=("Segoe UI", fs), bg=p["bg"], fg=p["text"],
                       activebackground=p["bg"], selectcolor=p["bg"],
                       cursor="hand2").pack(anchor="w")

        rule()

        r3 = tk.Frame(section("PHRASE BUTTON TEXT SIZE"), bg=p["bg"])
        r3.pack(fill="x")
        self.font_var = tk.IntVar(value=fs)
        tk.Spinbox(r3, from_=10, to=28, increment=1,
                   textvariable=self.font_var, width=5,
                   font=("Segoe UI", fs), relief="flat",
                   bg=p["surface"], fg=p["text"],
                   highlightthickness=1, highlightbackground=p["border"],
                   ).pack(side="left")
        tk.Label(r3, text="pt", font=("Segoe UI", 11),
                 fg=p["text2"], bg=p["bg"]).pack(side="left", padx=14)

    def _save(self):
        self.app.settings["delay"]          = round(float(self.delay_var.get()), 1)
        self.app.settings["clear_after_go"] = self.clear_var.get()
        self.app.settings["font_size"]      = int(self.font_var.get())
        save_json(SETTINGS_FILE, self.app.settings)
        self.app._rebuild_tabs()
        messagebox.showinfo("Saved", "Settings saved.", parent=self)


# ── Mobile window (QR code popup) ────────────────────────────────────────────

class MobileWindow(tk.Toplevel):
    def __init__(self, parent: tk.Tk, app: App, url: str):
        super().__init__(parent)
        self.app = app
        p = app._p()

        self.title("Mobile Input")
        self.configure(bg=p["bg"])
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._close)

        hdr = tk.Frame(self, bg=p["hdr"], padx=16, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Mobile Input",
                 font=("Segoe UI", 13, "bold"),
                 bg=p["hdr"], fg="#FFFFFF").pack(side="left")

        inner = tk.Frame(self, bg=p["bg"], padx=28, pady=20)
        inner.pack(fill="both", expand=True)

        if QR_OK:
            self._qr_canvas = tk.Canvas(inner, width=500, height=500,
                                        bg="#FFFFFF", highlightthickness=0)
            self._qr_canvas.pack(pady=(0, 14))
            _draw_qr(self._qr_canvas, url, 500)
        else:
            self._qr_canvas = None
            tk.Label(inner,
                     text="Install qrcode to show a scannable code:\n"
                          "pip install qrcode",
                     font=("Segoe UI", 10),
                     bg=p["bg"], fg=p["text3"],
                     justify="center").pack(pady=(0, 8))

        self._scan_lbl = tk.Label(inner, text="Scan with your phone's camera",
                                  font=("Segoe UI", 13, "bold"),
                                  bg=p["bg"], fg=p["text"])
        self._scan_lbl.pack()

        tk.Frame(inner, bg=p["border"], height=1).pack(fill="x", pady=(16, 6))

        url_wrap = tk.Frame(inner, bg=p["border"], padx=1, pady=1)
        url_wrap.pack(fill="x")
        self._url_var = tk.StringVar(value=url)
        tk.Entry(url_wrap, textvariable=self._url_var,
                 font=("Segoe UI", 10), relief="flat", bd=0,
                 state="readonly", readonlybackground=p["surface"],
                 fg=p["text"]).pack(fill="x", padx=8, pady=6)

        self._net_lbl = tk.Label(
            inner, text="WiFi only — click Tunnel to use on any network",
            font=("Segoe UI", 9), bg=p["bg"], fg=p["text3"])
        self._net_lbl.pack(pady=(6, 0))

        self._tunnel_btn = tk.Button(
            inner,
            text="  Tunnel  (works anywhere, free)",
            font=("Segoe UI", 10),
            command=self._start_tunnel,
            bg=p["info_bg"], fg=p["info_fg"],
            activebackground=p["info_hd"], activeforeground=p["info_fg"],
            relief="flat", padx=14, pady=8, cursor="hand2",
            highlightthickness=1, highlightbackground=p["info_fg"],
        )
        self._tunnel_btn.pack(pady=(12, 0), fill="x")
        _hover(self._tunnel_btn, p["info_bg"], p["info_hd"], p["info_fg"])

        close = tk.Button(inner, text="Close & stop server",
                          font=("Segoe UI", 11),
                          command=self._close,
                          bg=p["btn_bg"], fg=p["text2"],
                          activebackground=p["hover"], activeforeground=p["text"],
                          relief="flat", padx=24, pady=10, cursor="hand2",
                          highlightthickness=1, highlightbackground=p["border"])
        close.pack(pady=(16, 0))
        _hover(close, p["btn_bg"], p["hover"], p["text2"], p["text"])

        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - self.winfo_width()//2}+{py - self.winfo_height()//2}")

    def _update_url(self, url: str):
        self._url_var.set(url)
        if self._qr_canvas:
            self._qr_canvas.delete("all")
            _draw_qr(self._qr_canvas, url, 500)

    def _start_tunnel(self):
        p = self.app._p()
        self._tunnel_btn.config(state="disabled", cursor="", text="Starting…")
        self._tunnel_btn.unbind("<Enter>")
        self._tunnel_btn.unbind("<Leave>")
        port = self.app._mobile_server.port if self.app._mobile_server else 0

        def _do():
            if not _find_cloudflared():
                self.after(0, lambda: self._tunnel_btn.config(
                    text="Downloading cloudflared… 0%"))
                try:
                    _download_cloudflared(
                        lambda pct: self.after(0, lambda v=pct:
                            self._tunnel_btn.config(
                                text=f"Downloading cloudflared… {v}%")))
                except Exception as exc:
                    self.after(0, lambda e=str(exc): self._on_tunnel_err(e))
                    return
            self.after(0, lambda: self._tunnel_btn.config(
                text="Connecting to Cloudflare…"))
            try:
                proc = _launch_cf_tunnel(
                    port,
                    on_url=lambda u: self.after(0, lambda u=u: self._on_tunnel_url(u)),
                    on_error=lambda e: self.after(0, lambda e=e: self._on_tunnel_err(e)),
                )
                if self.app._mobile_server:
                    self.app._mobile_server._cf_proc = proc
            except Exception as exc:
                self.after(0, lambda e=str(exc): self._on_tunnel_err(e))

        threading.Thread(target=_do, daemon=True).start()

    def _on_tunnel_url(self, url: str):
        p = self.app._p()
        self._tunnel_btn.config(
            text="Tunnel active", state="disabled", cursor="",
            bg=p["green_l"], fg=p["green"],
            highlightbackground=p["green"])
        self._net_lbl.config(text="Tunnel active — works on any network")
        self._scan_lbl.config(text="Scan with your phone's camera")
        self._update_url(url)

    def _on_tunnel_err(self, msg: str):
        p = self.app._p()
        self._tunnel_btn.config(
            text=f"Error — {msg[:55]}",
            state="normal", cursor="hand2",
            bg=p["danger_bg"], fg=p["danger_fg"],
            highlightbackground=p["danger_fg"])
        _hover(self._tunnel_btn, p["danger_bg"], p["danger_hd"], p["danger_fg"])

    def _close(self):
        self.app._stop_mobile()
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=== Survey Sentence Generator starting ===")
    root = tk.Tk()
    # Locate the .ico whether running as a script or a frozen PyInstaller exe
    _bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    _icon = os.path.join(_bundle_dir, "treez.ico")
    if os.path.exists(_icon):
        root.iconbitmap(_icon)
    App(root)
    root.mainloop()
