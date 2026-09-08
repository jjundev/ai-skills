#!/usr/bin/env python3
"""
Unified Chrome CDP Allinpdf Converter (single & multi-worker).
Standard library only: zero third-party dependencies.
Distributes conversion jobs across isolated headless Chrome instances on independent debug ports.
"""

from __future__ import annotations
import sys
import os
import time
import json
import socket
import struct
import base64
import urllib.request
import subprocess
import argparse
import tempfile
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DEFAULT_BASE_PORT = 9222
DEFAULT_MAX_WORKERS = 3


def get_chrome_binary() -> str:
    """Lazily locate the Google Chrome binary without failing at module import."""
    env_path = os.environ.get("CHROME_PATH")
    if env_path:
        return env_path
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for cmd in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"]:
        found = shutil.which(cmd)
        if found and found not in candidates:
            candidates.append(found)
    for path in candidates:
        if os.path.exists(path):
            return path
    return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def discover_hwp_files(target: str) -> list[str]:
    """Discover all .hwp and .hwpx files from a single file or directory recursively."""
    target_path = Path(target).resolve()
    if target_path.is_file():
        if target_path.suffix.lower() in [".hwp", ".hwpx"] and not target_path.name.startswith("~$"):
            return [str(target_path)]
        return []

    hwp_files = []
    if target_path.is_dir():
        for root, _, files in os.walk(target_path):
            for f in files:
                if f.lower().endswith((".hwp", ".hwpx")) and not f.startswith("~$"):
                    hwp_files.append(os.path.join(root, f))
    return sorted(hwp_files)


def resolve_output_pdf_path(hwp_path: str, base_target: str | None = None, output_dir: str | None = None) -> str:
    """Determine the destination PDF path for a given HWP file."""
    hwp_p = Path(hwp_path).resolve()
    pdf_filename = hwp_p.stem + ".pdf"

    if output_dir is None:
        return str(hwp_p.parent / pdf_filename)

    out_root = Path(output_dir).resolve()
    if base_target is None:
        return str(out_root / pdf_filename)

    base_p = Path(base_target).resolve()
    if base_p.is_file():
        return str(out_root / pdf_filename)

    try:
        rel_parent = hwp_p.parent.relative_to(base_p)
        return str(out_root / rel_parent / pdf_filename)
    except ValueError:
        return str(out_root / pdf_filename)


def validate_pdf(pdf_path: str) -> bool:
    """Validate that the generated PDF exists, has minimum size >= 100 bytes, and starts with %PDF- header."""
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 100:
        return False
    try:
        with open(pdf_path, "rb") as f:
            header = f.read(1024)
            return header.lstrip().startswith(b"%PDF-")
    except Exception:
        return False


class SimpleWS:
    """Minimal WebSocket client for Chrome DevTools Protocol."""
    def __init__(self, url: str):
        _, rest = url.split("://", 1)
        host_port, path = rest.split("/", 1)
        host, port = host_port.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode("utf-8")
        req = (
            f"GET /{path} HTTP/1.1\r\n"
            f"Host: {host_port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode("utf-8"))
        resp = self.sock.recv(4096)
        if b"101 " not in resp:
            raise ConnectionError(f"WS Handshake failed: {resp}")
        self.msg_id = 0

    def send(self, method: str, params: dict | None = None) -> int:
        self.msg_id += 1
        payload = json.dumps({"id": self.msg_id, "method": method, "params": params or {}}).encode("utf-8")
        length = len(payload)
        mask = os.urandom(4)
        header = bytearray([0x81])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack(">H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack(">Q", length))
        header.extend(mask)
        masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(header + masked_payload)
        return self.msg_id

    def recv(self, timeout: float = 10) -> dict | None:
        self.sock.settimeout(timeout)
        try:
            h = self.sock.recv(2)
            if not h:
                return None
            b1, b2 = h[0], h[1]
            masked = bool(b2 & 0x80)
            length = b2 & 0x7f
            if length == 126:
                length = struct.unpack(">H", self.sock.recv(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self.sock.recv(8))[0]
            mask = self.sock.recv(4) if masked else None
            data = bytearray()
            while len(data) < length:
                chunk = self.sock.recv(length - len(data))
                if not chunk:
                    break
                data.extend(chunk)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            return json.loads(data.decode("utf-8", errors="ignore"))
        except socket.timeout:
            return None

    def call(self, method: str, params: dict | None = None, timeout: float = 20) -> dict | None:
        mid = self.send(method, params)
        start = time.time()
        while time.time() - start < timeout:
            msg = self.recv(timeout=1.0)
            if msg and msg.get("id") == mid:
                return msg.get("result")
        return None

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class AllinpdfConverter:
    """Chrome CDP controller for a single worker."""
    def __init__(self, port: int = DEFAULT_BASE_PORT, user_data_dir: str | None = None, chrome_path: str | None = None):
        self.port = port
        self.chrome_path = chrome_path
        self.user_data_dir = user_data_dir or tempfile.mkdtemp(prefix=f"chrome_allinpdf_{port}_")
        self.proc = None

    def start(self):
        if self.proc is None:
            chrome_bin = self.chrome_path or get_chrome_binary()
            if not os.path.exists(chrome_bin):
                raise FileNotFoundError(f"Google Chrome binary not found: {chrome_bin}")
            self.proc = subprocess.Popen([
                chrome_bin,
                "--headless=new",
                f"--remote-debugging-port={self.port}",
                "--remote-allow-origins=*",
                "--no-first-run",
                "--no-default-browser-check",
                f"--user-data-dir={self.user_data_dir}"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None
        shutil.rmtree(self.user_data_dir, ignore_errors=True)

    def restart(self):
        self.stop()
        self.user_data_dir = tempfile.mkdtemp(prefix=f"chrome_allinpdf_{self.port}_")
        self.start()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def convert_file(self, hwp_path: str, output_pdf_path: str, timeout_sec: int = 120) -> bool:
        abs_hwp = os.path.abspath(hwp_path)
        abs_out = os.path.abspath(output_pdf_path)
        os.makedirs(os.path.dirname(abs_out), exist_ok=True)
        file_size_mb = os.path.getsize(abs_hwp) / (1024 * 1024)

        if file_size_mb > 50:
            print(f"  [!] Error: File size {file_size_mb:.1f}MB exceeds Allinpdf 50MB limit. Split using split_hwp.py before converting: {abs_hwp}", flush=True)
            return False

        dynamic_timeout = min(180, max(timeout_sec, int(file_size_mb * 3) + 30))
        target_id = None
        ws = None
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/json/new?https://allinpdf.com/hwp-to-pdf", method="PUT")
            tab_info = json.loads(urllib.request.urlopen(req, timeout=10).read())
            ws_url = tab_info["webSocketDebuggerUrl"]
            target_id = tab_info["id"]

            ws = SimpleWS(ws_url)
            ws.call("Page.enable")
            ws.call("DOM.enable")
            ws.call("Network.enable")

            # 1. Page load & find input
            time.sleep(3)
            doc = ws.call("DOM.getDocument")
            if not doc or "root" not in doc:
                return False
            root_id = doc["root"]["nodeId"]
            node_res = ws.call("DOM.querySelector", {"nodeId": root_id, "selector": "input[type=file]"})
            if not node_res or "nodeId" not in node_res or node_res["nodeId"] == 0:
                return False

            file_node_id = node_res["nodeId"]

            # 2. Upload file
            ws.call("DOM.setFileInputFiles", {"files": [abs_hwp], "nodeId": file_node_id})

            # 3. Wait for options page
            options_loaded = False
            upload_wait_sec = min(120, max(45, int(file_size_mb * 3) + 30))
            start_upload_wait = time.time()
            while time.time() - start_upload_wait < upload_wait_sec:
                time.sleep(1)
                res = ws.call("Runtime.evaluate", {"expression": "location.href"})
                url = res.get("result", {}).get("value", "") if res else ""
                if "pdf-converter-options" in url:
                    options_loaded = True
                    break
                elif "limited-wait" in url or "exception" in url:
                    return False

            if not options_loaded:
                return False

            # 4. Click OK
            time.sleep(1)
            ws.call("Runtime.evaluate", {"expression": "document.getElementById('ContentPlaceHolder1_m_btnStartFileConvert')?.click()"})

            # 5. Wait for download link
            download_url = None
            start_wait = time.time()
            while time.time() - start_wait < dynamic_timeout:
                time.sleep(2)
                res = ws.call("Runtime.evaluate", {"expression": """
                    (() => {
                        const dl = document.querySelector('a.btn_download, a[href*="download"], a[href*="Download"], #btnDownload, #ContentPlaceHolder1_btnDownload, .btn_blue');
                        const links = Array.from(document.querySelectorAll('a')).map(a => ({href: a.href, text: a.innerText}));
                        return JSON.stringify({
                            url: location.href,
                            dl: dl ? dl.href : null,
                            links: links.filter(l => l.href.includes('File_Download') || l.href.includes('.pdf'))
                        });
                    })()
                """})
                val = json.loads(res["result"]["value"]) if res and "result" in res else {}
                current_url = val.get("url", "")
                if "exception" in current_url or "limited-wait" in current_url:
                    return False
                if val.get("dl"):
                    download_url = val["dl"]
                    break
                for l in val.get("links", []):
                    if "File_Download" in l.get("href", "") or "download" in l.get("href", "").lower():
                        download_url = l["href"]
                        break
                if download_url:
                    break

            if not download_url:
                return False

            # 6. Download PDF
            cookies_res = ws.call("Network.getCookies")
            cookies = cookies_res.get("cookies", []) if cookies_res else []
            cookie_hdr = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            dl_req = urllib.request.Request(download_url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Cookie": cookie_hdr,
                "Referer": val.get("url", "https://allinpdf.com/")
            })
            pdf_bytes = urllib.request.urlopen(dl_req, timeout=60).read()
            with open(abs_out, "wb") as f:
                f.write(pdf_bytes)

            return validate_pdf(abs_out)
        except Exception:
            return False
        finally:
            if ws:
                ws.close()
            if target_id:
                try:
                    close_req = urllib.request.Request(f"http://127.0.0.1:{self.port}/json/close/{target_id}", method="PUT")
                    urllib.request.urlopen(close_req, timeout=3)
                except Exception:
                    pass


def _worker_process(
    worker_id: int,
    port: int,
    tasks: list[tuple[str, str]],
    force: bool,
    retries: int,
    timeout: int,
    print_lock: threading.Lock
) -> list[tuple[str, str, bool, str]]:
    """Process a chunk of files using a dedicated Chrome CDP instance on a specific port."""
    results = []
    with AllinpdfConverter(port=port) as converter:
        for idx, (hwp_file, out_pdf) in enumerate(tasks, 1):
            rel_name = os.path.basename(hwp_file)
            if not force and validate_pdf(out_pdf):
                with print_lock:
                    print(f" [Worker {worker_id} (Port {port})] [SKIPPED] {rel_name}", flush=True)
                results.append((hwp_file, out_pdf, True, "skipped"))
                continue

            with print_lock:
                print(f" [Worker {worker_id} (Port {port})] [{idx}/{len(tasks)}] Converting: {rel_name}...", flush=True)

            success = False
            for attempt in range(1, retries + 2):
                if attempt > 1:
                    with print_lock:
                        print(f" [Worker {worker_id} (Port {port})] Retry {attempt - 1}/{retries} for {rel_name}...", flush=True)
                    converter.restart()
                    time.sleep(3)

                success = converter.convert_file(hwp_file, out_pdf, timeout_sec=timeout)
                if success:
                    break

            if success:
                with print_lock:
                    print(f" [Worker {worker_id} (Port {port})] [+] Successfully converted {rel_name}", flush=True)
                results.append((hwp_file, out_pdf, True, "converted"))
            else:
                with print_lock:
                    print(f" [Worker {worker_id} (Port {port})] [!] Failed {rel_name}", flush=True)
                results.append((hwp_file, out_pdf, False, "failed"))
            time.sleep(1)

    return results


def parallel_convert_hwp(
    files: list[str],
    max_workers: int = DEFAULT_MAX_WORKERS,
    force: bool = False,
    base_port: int = DEFAULT_BASE_PORT,
    base_target: str | None = None,
    output_dir: str | None = None,
    retries: int = 2,
    timeout: int = 120
) -> dict:
    """Execute multi-worker parallel conversion across available Chrome CDP ports."""
    print("[Notice] Document conversion is processed via external service (Allinpdf) via Headless Chrome.", flush=True)
    if not files:
        return {"total": 0, "success": 0, "skipped": 0, "failed": []}

    tasks = [(f, resolve_output_pdf_path(f, base_target, output_dir)) for f in files]
    num_workers = min(max_workers, len(tasks))

    # Split tasks evenly across workers
    chunks: list[list[tuple[str, str]]] = [[] for _ in range(num_workers)]
    for i, task in enumerate(tasks):
        chunks[i % num_workers].append(task)

    print_lock = threading.Lock()
    all_results = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(
                _worker_process,
                worker_id=w_idx + 1,
                port=base_port + w_idx,
                tasks=chunk,
                force=force,
                retries=retries,
                timeout=timeout,
                print_lock=print_lock
            )
            for w_idx, chunk in enumerate(chunks) if chunk
        ]
        for f in as_completed(futures):
            all_results.extend(f.result())

    success_cnt = sum(1 for _, _, ok, _ in all_results if ok)
    skipped_cnt = sum(1 for _, _, ok, status in all_results if ok and status == "skipped")
    failed_files = [(src, dst) for src, dst, ok, _ in all_results if not ok]

    return {
        "total": len(files),
        "success": success_cnt,
        "skipped": skipped_cnt,
        "failed": failed_files
    }


def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Multi-worker parallel HWP/HWPX to PDF batch converter via Headless Chrome CDP")
    parser.add_argument("target", help="Target HWP file or directory containing HWP files")
    parser.add_argument("--output-dir", "-o", default=None, help="Optional output directory (default: in-place next to HWP files)")
    parser.add_argument("--workers", "-w", type=int, default=DEFAULT_MAX_WORKERS, help=f"Number of parallel workers (default: {DEFAULT_MAX_WORKERS})")
    parser.add_argument("--base-port", "-p", type=int, default=DEFAULT_BASE_PORT, help=f"Base remote debugging port (default: {DEFAULT_BASE_PORT})")
    parser.add_argument("--force", "-f", action="store_true", help="Force overwrite existing PDF files")
    parser.add_argument("--retries", "-r", type=int, default=2, help="Number of retries per file (default: 2)")
    parser.add_argument("--timeout", "-t", type=int, default=120, help="Base timeout in seconds (default: 120)")
    args = parser.parse_args()

    target_path = os.path.abspath(args.target)
    if not os.path.exists(target_path):
        print(f"Error: Target path does not exist: {target_path}", flush=True)
        sys.exit(1)

    hwp_files = discover_hwp_files(target_path)
    if not hwp_files:
        print(f"No HWP files found in {target_path}", flush=True)
        return

    print(f"Found {len(hwp_files)} HWP files in {target_path}")
    print(f"Workers: {args.workers} (Ports {args.base_port} to {args.base_port + args.workers - 1})")
    print(f"Output mode: {'Mirrored to ' + args.output_dir if args.output_dir else 'In-place (alongside .hwp)'}\n")

    start_time = time.time()
    results = parallel_convert_hwp(
        files=hwp_files,
        max_workers=args.workers,
        force=args.force,
        base_port=args.base_port,
        base_target=target_path,
        output_dir=args.output_dir,
        retries=args.retries,
        timeout=args.timeout
    )
    elapsed = time.time() - start_time

    print("\n" + "=" * 50)
    print("Parallel Batch Conversion Finished!")
    print(f"Total: {results['total']} | Converted/Skipped: {results['success']} | Failed: {len(results['failed'])}")
    print(f"Elapsed Time: {elapsed:.2f}s")
    if results['failed']:
        print(f"\nFailed files ({len(results['failed'])}):")
        for src, dst in results['failed']:
            print(f" - {src}")


if __name__ == "__main__":
    main()
