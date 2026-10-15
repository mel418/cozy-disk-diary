"""Cozy Disk Diary - a cute, read-only disk space explorer.

Run:  python app.py      (opens http://127.0.0.1:8765 in your browser)
No third-party packages needed. Nothing is ever deleted or modified.
"""
import heapq
import json
import os
import shutil
import string
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PORT = 8765
FROZEN = getattr(sys, "frozen", False)  # True when running as the built .exe
HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))  # bundled files
HOME_DIR = os.path.dirname(sys.executable) if FROZEN else HERE  # where scan history is kept
DATA = os.path.join(HOME_DIR, "data")
os.makedirs(DATA, exist_ok=True)
sys.setrecursionlimit(10000)

MB = 1024 * 1024
KEEP_MIN = 5 * MB      # deeper folders smaller than this are rolled into their parent
KEEP_DEPTH = 2         # folders this shallow are always kept
DIFF_MIN = 1 * MB      # ignore changes smaller than this in the change log

CATEGORIES = {
    "pictures": ".jpg .jpeg .png .gif .bmp .webp .heic .svg .tif .tiff .raw .psd .ico",
    "videos": ".mp4 .mkv .mov .avi .wmv .flv .webm .m4v",
    "music": ".mp3 .wav .flac .aac .ogg .m4a .wma",
    "documents": ".pdf .doc .docx .xls .xlsx .ppt .pptx .txt .md .csv .rtf .odt .epub",
    "code": ".py .js .ts .html .css .json .java .c .cpp .h .cs .go .rs .php .rb .sh .bat .ps1 .xml .yml .yaml",
    "archives": ".zip .rar .7z .tar .gz .iso .bz2 .cab",
    "apps": ".exe .dll .msi .sys .lib .pdb .apk",
}
EXT = {e: c for c, exts in CATEGORIES.items() for e in exts.split()}


def categorize(name):
    return EXT.get(os.path.splitext(name)[1].lower(), "other")


# ---------------------------------------------------------------- scanning
scan_state = {"running": False, "root": None, "files": 0, "current": "", "error": None,
              "started": 0, "last_id": None}
scan_lock = threading.Lock()


def scan_tree(path, depth, flat):
    size = files = 0
    cats = {}
    top = []
    newest = 0
    try:
        it = os.scandir(path)
    except OSError:
        return 0, 0, {}, [], 0
    with it:
        for e in it:
            try:
                if e.is_symlink() or (hasattr(e, "is_junction") and e.is_junction()):
                    continue
                if e.is_dir(follow_symlinks=False):
                    s, n, c, t, m = scan_tree(e.path, depth + 1, flat)
                    size += s
                    files += n
                    newest = max(newest, m)
                    for k, (cn, cs) in c.items():
                        cur = cats.setdefault(k, [0, 0])
                        cur[0] += cn
                        cur[1] += cs
                    top = heapq.nlargest(5, top + t)
                elif e.is_file(follow_symlinks=False):
                    st = e.stat(follow_symlinks=False)
                    k = categorize(e.name)
                    cur = cats.setdefault(k, [0, 0])
                    cur[0] += 1
                    cur[1] += st.st_size
                    size += st.st_size
                    files += 1
                    newest = max(newest, int(st.st_mtime))
                    top = heapq.nlargest(5, top + [[st.st_size, e.path]])
                    scan_state["files"] += 1
                    if scan_state["files"] % 500 == 0:
                        scan_state["current"] = path
            except OSError:
                continue
    if depth <= KEEP_DEPTH or size >= KEEP_MIN:
        flat[path] = {"s": size, "n": files, "c": cats, "t": top, "m": newest}
    return size, files, cats, top, newest


def run_scan(root):
    flat = {}
    try:
        started = time.time()
        total = scan_tree(root, 0, flat)[0]
        snap = {"root": root, "time": started, "seconds": round(time.time() - started, 1),
                "total": total, "folders": flat}
        sid = time.strftime("%Y%m%d-%H%M%S", time.localtime(started))
        fname = f"snap_{sid}.json"
        with open(os.path.join(DATA, fname), "w", encoding="utf-8") as f:
            json.dump(snap, f)
        scan_state["last_id"] = fname
        _cache[fname] = snap
    except Exception as ex:  # keep the UI alive no matter what
        scan_state["error"] = str(ex)
    finally:
        scan_state["running"] = False


def start_scan(root):
    root = os.path.normpath(root)
    if not os.path.isdir(root):
        return False, "That folder doesn't exist"
    with scan_lock:
        if scan_state["running"]:
            return False, "Already scanning"
        scan_state.update(running=True, root=root, files=0, current=root, error=None,
                          started=time.time())
    threading.Thread(target=run_scan, args=(root,), daemon=True).start()
    return True, "ok"


# --------------------------------------------------------------- snapshots
_cache = {}


def list_snaps():
    out = []
    for fn in sorted(os.listdir(DATA)):
        if fn.startswith("snap_") and fn.endswith(".json"):
            out.append(fn)
    return out


def load(fn):
    if fn not in _cache:
        with open(os.path.join(DATA, fn), encoding="utf-8") as f:
            _cache[fn] = json.load(f)
    return _cache[fn]


def snap_meta(fn):
    s = load(fn)
    return {"id": fn, "root": s["root"], "time": s["time"], "total": s["total"],
            "seconds": s.get("seconds", 0)}


def snaps_for(root=None):
    ids = list_snaps()
    if root:
        ids = [i for i in ids if load(i)["root"].lower() == root.lower()]
    return ids


def children_of(snap, path):
    kids = []
    for p, v in snap["folders"].items():
        if p != path and os.path.dirname(p) == path:
            kids.append((p, v))
    return kids


def node_view(snap, path):
    v = snap["folders"].get(path)
    if v is None:
        return None
    kids = sorted(children_of(snap, path), key=lambda kv: -kv[1]["s"])
    kid_sum = sum(k[1]["s"] for k in kids)
    return {
        "path": path, "name": os.path.basename(path) or path, "size": v["s"], "files": v["n"],
        "cats": {k: {"n": c[0], "s": c[1]} for k, c in v["c"].items()},
        "top": [{"size": t[0], "path": t[1]} for t in v["t"]],
        "newest": v["m"],
        "loose": max(v["s"] - kid_sum, 0),
        "children": [{"path": p, "name": os.path.basename(p), "size": c["s"], "files": c["n"],
                      "cats": {k: x[1] for k, x in c["c"].items()}} for p, c in kids],
    }


def diff_snaps(old, new):
    ofold, nfold = old["folders"], new["folders"]
    paths = set(ofold) | set(nfold)
    delta = {p: nfold.get(p, {"s": 0})["s"] - ofold.get(p, {"s": 0})["s"] for p in paths}
    big = {p for p, d in delta.items() if abs(d) >= DIFF_MIN}
    by_parent = {}
    for p in big:
        by_parent.setdefault(os.path.dirname(p), []).append(p)
    rows = []
    for p in big:
        d = delta[p]
        # skip a folder if one of its children explains most of the change (show the cause instead)
        if any(abs(delta[k]) >= 0.8 * abs(d) and (delta[k] > 0) == (d > 0) for k in by_parent.get(p, [])):
            continue
        kind = "appeared" if p not in ofold else "disappeared" if p not in nfold else ("grew" if d > 0 else "shrank")
        rows.append({"path": p, "delta": d, "kind": kind,
                     "before": ofold.get(p, {"s": 0})["s"], "after": nfold.get(p, {"s": 0})["s"]})
    rows.sort(key=lambda r: -abs(r["delta"]))
    return {"total_delta": new["total"] - old["total"], "rows": rows[:200]}


# ------------------------------------------------------------------- http
def drives():
    out = []
    for letter in string.ascii_uppercase:
        d = f"{letter}:\\"
        if os.path.exists(d):
            try:
                u = shutil.disk_usage(d)
                out.append({"path": d, "total": u.total, "used": u.used, "free": u.free})
            except OSError:
                pass
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self):
        return self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._host_ok():
            return self._json({"error": "bad host"}, 403)
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/api/status":
            self._json({**scan_state, "elapsed": round(time.time() - scan_state["started"], 1)
                        if scan_state["running"] else 0})
        elif u.path == "/api/drives":
            home = os.path.expanduser("~")
            self._json({"drives": drives(), "home": home})
        elif u.path == "/api/history":
            self._json([snap_meta(i) for i in reversed(snaps_for())])
        elif u.path == "/api/folder":
            ids = snaps_for(q.get("root"))
            if not ids:
                return self._json({"empty": True})
            sid = q.get("snap") or ids[-1]
            snap = load(sid)
            path = q.get("path") or snap["root"]
            view = node_view(snap, path)
            self._json({"snap": snap_meta(sid), "node": view} if view else {"missing": True,
                                                                          "snap": snap_meta(sid)})
        elif u.path == "/api/changes":
            ids = snaps_for(q.get("root"))
            if len(ids) < 2:
                return self._json({"need_more": True, "count": len(ids)})
            new_id = q.get("snap") or ids[-1]
            if new_id not in ids:
                return self._json({"error": "unknown snapshot"}, 404)
            idx = ids.index(new_id)
            if idx == 0:
                return self._json({"need_more": True, "count": len(ids)})
            old_id = ids[idx - 1]
            self._json({"old": snap_meta(old_id), "new": snap_meta(new_id),
                        **diff_snaps(load(old_id), load(new_id))})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._host_ok() or self.headers.get("Content-Type", "") != "application/json":
            return self._json({"error": "forbidden"}, 403)
        n = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self._json({"error": "bad json"}, 400)
        if self.path == "/api/scan":
            ok, msg = start_scan(str(data.get("path", "")))
            self._json({"ok": ok, "msg": msg})
        elif self.path == "/api/open":
            # only open folders that appear in a saved scan; opening only views, never changes anything
            p = str(data.get("path", ""))
            known = any(p in load(i)["folders"] for i in snaps_for())
            if known and os.path.isdir(p):
                os.startfile(p)
                self._json({"ok": True})
            else:
                self._json({"ok": False}, 400)
        else:
            self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        import ctypes
        import webview  # desktop window (pip install pywebview)
        # own taskbar identity, so it doesn't group under the Python icon
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CozyDiskDiary.App")
        ico = os.path.join(HERE, "icon.ico")

        def set_window_icon():
            u = ctypes.windll.user32
            for _ in range(50):
                hwnd = u.FindWindowW(None, "Cozy Disk Diary")
                if hwnd:
                    for size, which in ((32, 1), (16, 0)):  # ICON_BIG, ICON_SMALL
                        h = u.LoadImageW(None, ico, 1, size, size, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
                        u.SendMessageW(hwnd, 0x80, which, h)  # WM_SETICON
                    return
                time.sleep(0.2)

        webview.create_window("Cozy Disk Diary", url, width=1240, height=800, min_size=(820, 600))
        # keep browser storage on disk so the light/dark choice is remembered
        webview.start(set_window_icon, private_mode=False, storage_path=os.path.join(DATA, "webview"))
    except Exception:
        # fallback: open in the browser and keep the server alive
        webbrowser.open(url)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
