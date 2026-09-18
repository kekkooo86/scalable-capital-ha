#!/usr/bin/env python3
"""Scalable CLI Bridge add-on.

Read-only HTTP bridge around the official Scalable CLI (`sc`) plus a
device-code login helper. Never exposes trade/buy/sell commands.
"""
import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SC_BIN = "/usr/local/bin/sc"
OPTIONS_FILE = "/data/options.json"
WWW_DIR = "/app/www"
CONFIG_DIR = os.environ.get("XDG_CONFIG_HOME", "/data/.config") + "/scalable-cli"
BIND_HOST = "0.0.0.0"
BIND_PORT = int(os.environ.get("SC_BRIDGE_PORT", "8788"))


def load_options():
    try:
        with open(OPTIONS_FILE) as fh:
            return json.load(fh)
    except Exception:
        return {}


OPTIONS = load_options()

SCAN_INTERVAL_DEFAULT = 900
SCAN_INTERVAL_MIN = 300
SCAN_INTERVAL_MAX = 86400


def scan_interval() -> int:
    """Polling interval (seconds) suggested to consumers, from add-on options."""
    try:
        value = int(OPTIONS.get("scan_interval", SCAN_INTERVAL_DEFAULT))
    except (TypeError, ValueError):
        value = SCAN_INTERVAL_DEFAULT
    return max(SCAN_INTERVAL_MIN, min(SCAN_INTERVAL_MAX, value))


def sc_env():
    env = dict(os.environ)
    env["HOME"] = "/data"
    env["XDG_CONFIG_HOME"] = "/data/.config"
    env["PATH"] = "/usr/local/bin:/usr/bin:/bin"
    return env


def run_sc_raw(args, timeout=60):
    proc = subprocess.run(
        [SC_BIN] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=sc_env(),
    )
    return proc


def run_sc(args, timeout=60):
    proc = run_sc_raw(args, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "sc error").strip())
    return json.loads(proc.stdout)


def sc(args):
    out = run_sc(args)
    if not out.get("ok"):
        raise RuntimeError(json.dumps(out.get("error", out)))
    return out


def probe_session():
    payload = {
        "probed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "session_dir": "present" if os.path.isdir(CONFIG_DIR) else "missing",
        "state": "error",
        "detail": "",
    }
    try:
        proc = run_sc_raw(["whoami"], timeout=30)
    except Exception as exc:  # noqa: BLE001
        payload["detail"] = f"probe error: {exc}"
        return payload
    if proc.returncode == 0:
        payload["state"] = "active"
        payload["detail"] = proc.stdout.strip()[:300]
    else:
        msg = (proc.stderr or proc.stdout or "").strip()
        if "no_session" in msg or "No active session" in msg or "sc login" in msg:
            payload["state"] = "expired"
        else:
            payload["state"] = "error"
        payload["detail"] = msg[:500]
    return payload


class LoginManager:
    """Run `sc login --local-read-only` and capture the device-code prompt."""

    def __init__(self):
        self._lock = threading.Lock()
        self._proc = None
        self.url = None
        self.code = None
        self.started_at = None
        self.finished_at = None
        self.returncode = None
        self.error = None
        self.output = []

    def status(self):
        with self._lock:
            running = self._proc is not None and self._proc.poll() is None
            return {
                "running": running,
                "url": self.url,
                "code": self.code,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "returncode": self.returncode,
                "error": self.error,
                "output": "".join(self.output[-15:]),
            }

    def start(self):
        with self._lock:
            already_running = self._proc is not None and self._proc.poll() is None
            if not already_running:
                self.url = None
                self.code = None
                self.error = None
                self.returncode = None
                self.finished_at = None
                self.output = []
                self.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self._proc = subprocess.Popen(
                    [SC_BIN, "login", "--local-read-only"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                env=sc_env(),
            )
        if already_running:
            return self.status()
        threading.Thread(target=self._reader, daemon=True).start()
        time.sleep(2.0)
        return self.status()

    def _reader(self):
        proc = self._proc
        for line in proc.stdout:  # type: ignore[union-attr]
            with self._lock:
                self.output.append(line)
                if not self.url:
                    m = re.search(r"https?://\S+", line)
                    if m:
                        self.url = m.group(0)
                if not self.code:
                    m = re.search(r"\b([A-Z0-9]{4}-[A-Z0-9]{4})\b", line)
                    if m:
                        self.code = m.group(1)
        rc = proc.wait()
        with self._lock:
            self.returncode = rc
            self.finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if rc != 0:
                self.error = (
                    "".join(self.output[-5:]).strip() or f"sc login exit {rc}"
                )


LOGIN = LoginManager()


def get_overview():
    return sc(["broker", "overview", "--json"])["data"]["result"]


def get_holdings():
    items = sc(["broker", "holdings", "--json"])["data"]["result"]["items"]
    return {it["isin"]: it for it in items}


class Handler(BaseHTTPRequestHandler):
    server_version = "sc-cli-bridge/1.1"

    def _send(self, code, obj, content_type="application/json"):
        if isinstance(obj, (dict, list)):
            body = json.dumps(obj).encode()
        else:
            body = obj.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        try:
            with open(path, "rb") as fh:
                body = fh.read()
        except OSError:
            return self._send(404, {"ok": False, "error": "not found"})
        ctype = "text/html" if path.endswith(".html") else "text/plain"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _do(self):
        path = urllib.parse.urlparse(self.path)
        route = path.path
        qs = urllib.parse.parse_qs(path.query)

        if route in ("/", "/index.html"):
            return self._send_file(os.path.join(WWW_DIR, "index.html"))

        try:
            if route == "/health":
                return self._send(200, {"ok": True})
            if route == "/config":
                return self._send(
                    200,
                    {
                        "ok": True,
                        "scan_interval": scan_interval(),
                        "scan_interval_min": SCAN_INTERVAL_MIN,
                        "scan_interval_max": SCAN_INTERVAL_MAX,
                    },
                )
            if route == "/session":
                return self._send(200, {"ok": True, "session": probe_session()})
            if route == "/login/start":
                return self._send(200, {"ok": True, "login": LOGIN.start()})
            if route == "/login/status":
                return self._send(200, {"ok": True, "login": LOGIN.status()})
            if route == "/logout":
                try:
                    run_sc_raw(["logout", "--json"], timeout=30)
                except Exception:  # noqa: BLE001
                    pass
                return self._send(200, {"ok": True})
            if route == "/portfolio":
                overview = get_overview()
                holdings = get_holdings()
                return self._send(
                    200, {"ok": True, "overview": overview, "holdings": holdings}
                )
            if route == "/quote":
                isin = qs.get("isin", [""])[0]
                if not isin:
                    return self._send(400, {"ok": False, "error": "isin required"})
                return self._send(
                    200, sc(["broker", "quote", "--isin", isin, "--json"])
                )
            return self._send(404, {"ok": False, "error": "not found"})
        except Exception as exc:  # noqa: BLE001
            return self._send(500, {"ok": False, "error": str(exc)})

    def do_GET(self):
        self._do()

    def do_POST(self):
        self._do()

    def log_message(self, *args):
        pass


def main():
    if not os.path.exists(SC_BIN):
        raise SystemExit(f"sc not found at {SC_BIN}")
    server = ThreadingHTTPServer((BIND_HOST, BIND_PORT), Handler)
    print(f"sc-cli-bridge listening on {BIND_HOST}:{BIND_PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
