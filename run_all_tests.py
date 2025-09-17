#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import signal
import subprocess
import shutil
from datetime import datetime

# === AYARLAR ===
RUN_DURATION = 30  # saniye: her test modülünü kaç saniye çalıştıracağımız
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "results")

TESTS = [
    "dns_resol_latency.py",
    "https_latency.py",
    "ntp_test.py",
    "jitter_test.py",
    "bufferbloat_like_test.py",
    "meeting_test.py",
    "wificheck.py",
]

REMOVE_DIRS = [
    "http_latency_test_result",
    "meeting_test",
]

# ------------------------------------------------------
# Yardımcılar
# ------------------------------------------------------
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def safe_kill_process_group(proc):
    """Try SIGTERM the whole group, fallback to kill, ignore if already gone."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    # Give it a moment
    try:
        proc.wait(timeout=3)
    except Exception:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass

def run_single_test(script_path, duration):
    start_ts = datetime.now()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    cmd = ["python3", "-u", script_path]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=BASE_DIR,
            preexec_fn=os.setsid
        )
    except FileNotFoundError as e:
        block = []
        block.append(f"### {os.path.basename(script_path)} ###")
        block.append(f"Started: {start_ts.isoformat(timespec='seconds')}  |  Ended: {datetime.now().isoformat(timespec='seconds')}")
        block.append("PID: -  |  Duration: 0s  |  Return code: -")
        block.append("--- STDOUT ---")
        block.append("(No output captured)")
        block.append("--- STDERR ---")
        block.append(str(e))
        block.append("=" * 70)
        block.append("")
        return "\n".join(block)

    pid = proc.pid
    time.sleep(duration)
    safe_kill_process_group(proc)
    end_ts = datetime.now()
    try:
        stdout, stderr = proc.communicate(timeout=5)
    except Exception:
        stdout, stderr = "", "process did not exit cleanly"
    rc = proc.returncode

    block = []
    block.append(f"### {os.path.basename(script_path)} ###")
    block.append(f"Started: {start_ts.isoformat(timespec='seconds')}  |  Ended: {end_ts.isoformat(timespec='seconds')}")
    block.append(f"PID: {pid}  |  Duration: {duration}s  |  Return code: {rc}")
    block.append("--- STDOUT ---")
    block.append(stdout.rstrip("\n") if stdout and stdout.strip() else "(No output captured)")
    block.append("--- STDERR ---")
    block.append(stderr.rstrip("\n") if stderr and stderr.strip() else "(No errors)")
    block.append("=" * 70)
    block.append("")
    return "\n".join(block)

def cleanup_dirs():
    for d in REMOVE_DIRS:
        p = os.path.join(BASE_DIR, d)
        if os.path.isdir(p):
            try:
                shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass

# --- Link Type Detection Helpers ---
def _get_primary_iface():
    """Return primary egress interface using 'ip route get'."""
    try:
        out = subprocess.check_output(
            ["bash", "-lc", "ip route get 8.8.8.8 | sed -n 's/.* dev \\([^ ]*\\).*/\\1/p'"],
            stderr=subprocess.STDOUT
        ).decode().strip()
        return out if out else None
    except Exception:
        return None

def _is_wireless_iface(iface):
    """Detect wireless by presence of /sys/class/net/<iface>/wireless or iw dev listing."""
    try:
        if iface and os.path.isdir(f"/sys/class/net/{iface}/wireless"):
            return True
    except Exception:
        pass
    try:
        out = subprocess.check_output(["iw", "dev"], stderr=subprocess.STDOUT).decode()
        if iface:
            if f"Interface {iface}\n" in out:
                return True
            if re.search(r"Interface\s+%s\b" % re.escape(iface), out):
                return True
        # If there is at least one wireless interface listed
        return bool(out.strip())
    except Exception:
        return False

def is_wifi_active():
    """Return True if the primary route egress interface appears to be Wi-Fi."""
    iface = _get_primary_iface()
    if not iface:
        # No info → default to not Wi-Fi (skip wificheck)
        return False
    return _is_wireless_iface(iface)

# (Opsiyonel) metrik çıkarımı – rapor başında özet yapmak istersek kullanılabilir
def parse_metrics_from_text(base, text):
    metrics = []

    def find_last_float(pat, flags=0):
        val = None
        for m in re.finditer(pat, text, flags):
            try:
                val = float(m.group(1))
            except Exception:
                pass
        return val

    if base == "dns_resol_latency.py":
        val = find_last_float(r"Average latency:\s*([0-9.]+)\s*ms")
        if val is not None:
            metrics.append(("DNS Avg (ms)", val))

    elif base == "https_latency.py":
        val = find_last_float(r"HTTPS Latency \(avg\):\s*([0-9.]+)\s*ms")
        if val is not None:
            metrics.append(("HTTPS Avg (ms)", val))

    elif base == "ntp_test.py":
        val = find_last_float(r"Round Trip Delay:\s*([0-9.]+)\s*ms")
        if val is not None:
            metrics.append(("NTP RTD (ms)", val))

    elif base == "jitter_test.py":
        val = find_last_float(r"Avg\s*\(ms\)\s*:\s*([0-9.]+)")
        if val is not None:
            metrics.append(("Jitter Avg (ms)", val))

    elif base == "bufferbloat_like_test.py":
        b = find_last_float(r"===\s*Baseline Summary\s*===.*?Avg\s*\(ms\)\s*:\s*([0-9.]+)", flags=re.S)
        if b is not None:
            metrics.append(("Bloat Baseline (ms)", b))
        l = find_last_float(r"---\s*Load Summary\s*---.*?Avg\s*\(ms\)\s*:\s*([0-9.]+)", flags=re.S)
        if l is not None:
            metrics.append(("Bloat Load (ms)", l))

    elif base == "meeting_test.py":
        vals = [float(m.group(1)) for m in re.finditer(r"Average Latency:\s*([0-9.]+)\s*ms", text)]
        if vals:
            metrics.append(("Meeting Avg (ms)", sum(vals)/len(vals)))

    elif base == "wificheck.py":
        # Heuristic: try to capture last SNR in a row line
        last_row = None
        for line in text.strip().splitlines():
            if re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", line):
                last_row = line
        if last_row:
            m = re.search(r"\bSNR\D*([-+]?\d+\.?\d*)", last_row, re.I)
            if m:
                try:
                    metrics.append(("WiFi SNR (dB)", float(m.group(1))))
                except Exception:
                    pass

    return metrics

# ------------------------------------------------------
# Tek bir tur tüm testleri çalıştır ve zaman damgalı dosyaya yaz
# ------------------------------------------------------
def run_once():
    ensure_dir(RESULTS_DIR)
    batch_ts = datetime.now().strftime("%Y%m%d_%H%M%S")  # her tur için yeni damga
    result_file = os.path.join(RESULTS_DIR, f"{batch_ts}_all_tests.txt")

    print(f"SUM {len(TESTS)} tests running... (each tests {RUN_DURATION} sn)")
    head = (
        f"# Oprobe Combined Test Results\n"
        f"Generated at {datetime.now().isoformat(timespec='seconds')}\n"
        + "=" * 70 + "\n\n"
    )

    blocks = []
    for test in TESTS:
        script_path = os.path.join(BASE_DIR, test)
        print(f"Running: {test} ...")

        if test == "wificheck.py" and not is_wifi_active():
            # Skip Wi-Fi test on BaseT and log a clear block
            start_ts = datetime.now().isoformat(timespec='seconds')
            block_text = (
                "### wificheck.py ###\n"
                f"Started: {start_ts}\n"
                "STATUS: SKIPPED\n"
                "REASON: This agent connection BaseT\n"
                + "="*70 + "\n\n"
            )
        else:
            block_text = run_single_test(script_path, RUN_DURATION)

        blocks.append(block_text)
        cleanup_dirs()

    with open(result_file, "w", encoding="utf-8") as f:
        f.write(head)
        f.write("\n".join(blocks))

    print(f"✅ Bitti. Tek dosya: {result_file}")

# ------------------------------------------------------
# Periyodik çalıştırma döngüsü
# ------------------------------------------------------
if __name__ == "__main__":
    INTERVAL_SECONDS = 10 * 60  # 10 dakika

    try:
        # İlk tur hemen
        run_once()

        # Sonra periyodik
        while True:
            print(f"⏳ Bir sonraki tur için bekleniyor: {INTERVAL_SECONDS} saniye (CTRL+C ile durdurabilirsiniz)")
            time.sleep(INTERVAL_SECONDS)
            run_once()
    except KeyboardInterrupt:
        print("\n❌ Program manuel olarak durduruldu (CTRL+C).")
