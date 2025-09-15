#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# bufferbloat_like_test.py
# Oprobe - Bufferbloat-like Latency Under Load (clean + signals, upload enabled by default)
#
# Özellikler:
# - Varsayılan: baseline 12s, load 12s (CLI ile değiştirilebilir)
# - Warm-up discard: ilk N örnek atılır (varsayılan 3)
# - Aynı rota probesi: download hedefinin host’una TCP connect (opsiyonel TLS)
# - Paralel download + upload yükü (varsayılan 4 DL + 2 UL akış)
# - Metrix: avg, stddev, IPDV, p5/p95, min/max
# - Skor: Δp95 ve Δavg’e göre Excellent/Good/Fair/Poor
# - SIGINT/SIGTERM yakalar → o ana kadarki verilerle “partial” özet basar
#
# Notlar:
# * Upload için varsayılan uç nokta: https://speed.cloudflare.com/__up
#   Erişilemiyorsa kendi sunucundaki benzer bir “sink” endpoint’i ver:
#   --ul https://example.com/upload-sink
#
import argparse
import math
import signal
import socket
import ssl
import statistics
import threading
import time
import urllib.parse
from dataclasses import dataclass
from typing import List, Tuple, Optional

import requests

# -------------------- Varsayılanlar --------------------
BASELINE_DURATION = 12.0
LOAD_DURATION     = 12.0
SAMPLE_PERIOD     = 0.25
WARMUP_DISCARD    = 3

DEFAULT_DOWNLOAD_URLS = [
    "https://speed.hetzner.de/100MB.bin",
]

# Varsayılan upload uç noktası (Cloudflare). Gerekirse CLI ile değiştir.
DEFAULT_UPLOAD_URLS: List[str] = [
    "https://speed.cloudflare.com/__up"
]

USER_AGENT = "Oprobe-Bufferbloat/2.1"
# -------------------------------------------------------


@dataclass
class PhaseStats:
    samples: int
    avg: float
    stddev: float
    ipdv: float
    p5: float
    p95: float
    p95_p5: float
    vmin: float
    vmax: float


def percentile(values: List[float], p: float) -> float:
    if not values:
        return float('nan')
    values = sorted(values)
    k = (len(values) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return d0 + d1


def compute_stats(array: List[float]) -> PhaseStats:
    n = len(array)
    if n == 0:
        return PhaseStats(0, float('nan'), float('nan'), float('nan'),
                          float('nan'), float('nan'), float('nan'),
                          float('nan'), float('nan'))
    avg = statistics.mean(array)
    stddev = statistics.pstdev(array) if n > 1 else 0.0
    ipdv = sum(abs(array[i] - array[i - 1]) for i in range(1, n)) / (n - 1) if n > 1 else 0.0
    p5 = percentile(array, 5)
    p95 = percentile(array, 95)
    return PhaseStats(n, avg, stddev, ipdv, p5, p95, (p95 - p5), min(array), max(array))


def tcp_connect_latency(host: str, port: int = 443, tls: bool = False, timeout: float = 5.0) -> Optional[float]:
    """TCP (veya TLS) connect gecikmesi (ms). Başarısızlıkta None döner."""
    try:
        addr_info = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return None
    for family, socktype, proto, _, sockaddr in addr_info:
        s = socket.socket(family, socktype, proto)
        s.settimeout(timeout)
        start = time.perf_counter()
        try:
            s.connect(sockaddr)
            if tls:
                context = ssl.create_default_context()
                s = context.wrap_socket(s, server_hostname=host)
            elapsed = (time.perf_counter() - start) * 1000.0
            s.close()
            return elapsed
        except Exception:
            try:
                s.close()
            except Exception:
                pass
            continue
    return None


def reader_thread(stop_evt: threading.Event, url: str, session: requests.Session, timeout: float):
    headers = {"User-Agent": USER_AGENT}
    try:
        with session.get(url, stream=True, headers=headers, timeout=timeout) as r:
            for _ in r.iter_content(chunk_size=64 * 1024):
                if stop_evt.is_set():
                    break
    except Exception:
        pass


def random_bytes_generator(total_bytes: int, chunk_size: int = 64 * 1024):
    sent = 0
    # CPU yükünü düşük tutmak için sabit '0' byte'ları
    while sent < total_bytes:
        yield b"0" * min(chunk_size, total_bytes - sent)
        sent += chunk_size


def writer_thread(stop_evt: threading.Event, url: str, session: requests.Session, timeout: float):
    headers = {"User-Agent": USER_AGENT}
    while not stop_evt.is_set():
        try:
            # ~8 MB gönder, sonra döngü
            data_iter = random_bytes_generator(8 * 1024 * 1024)
            session.post(url, data=data_iter, headers=headers, timeout=timeout)
        except Exception:
            time.sleep(0.2)  # kısa bekle ve devam et


def start_load(download_urls: List[str], upload_urls: List[str], num_dl: int, num_ul: int, timeout: float) -> Tuple[threading.Event, List[threading.Thread]]:
    stop_evt = threading.Event()
    threads: List[threading.Thread] = []
    session = requests.Session()
    for i in range(num_dl):
        url = download_urls[i % len(download_urls)]
        t = threading.Thread(target=reader_thread, args=(stop_evt, url, session, timeout), daemon=True)
        t.start()
        threads.append(t)
    for i in range(num_ul):
        url = upload_urls[i % len(upload_urls)]
        t = threading.Thread(target=writer_thread, args=(stop_evt, url, session, timeout), daemon=True)
        t.start()
        threads.append(t)
    return stop_evt, threads


def stop_load(stop_evt: threading.Event, threads: List[threading.Thread]):
    stop_evt.set()
    for t in threads:
        t.join(timeout=1.0)


def measure_phase(host_for_probe: str, duration: float, sample_period: float, tls_probe: bool, discard: int,
                  timeout: float, shared_buffer: Optional[List[float]] = None) -> List[float]:
    values: List[float] = []
    deadline = time.monotonic() + duration
    next_t = time.monotonic()
    while time.monotonic() < deadline:
        now = time.monotonic()
        if now < next_t:
            time.sleep(min(0.01, next_t - now))
            continue
        ms = tcp_connect_latency(host_for_probe, 443, tls=tls_probe, timeout=timeout)
        if ms is not None:
            values.append(ms)
            if shared_buffer is not None:
                shared_buffer.append(ms)
        next_t += sample_period
    if discard and len(values) > discard:
        values = values[discard:]
    return values


def printable_stats(title: str, stats: PhaseStats) -> str:
    return (
        f"=== {title} ===\n"
        f"Samples    : {stats.samples}\n"
        f"Avg (ms)   : {stats.avg:.2f}\n"
        f"StdDev (ms): {stats.stddev:.2f}\n"
        f"IPDV  (ms) : {stats.ipdv:.2f}\n"
        f"p95-p5 (ms): {stats.p95_p5:.2f}  (p5={stats.p5:.2f}, p95={stats.p95:.2f})\n"
        f"Min/Max (ms): {stats.vmin:.2f} / {stats.vmax:.2f}\n"
        f"==================================================\n"
    )


def decide_score(base: PhaseStats, load: PhaseStats) -> Tuple[str, str]:
    delta_avg = load.avg - base.avg
    delta_p95 = load.p95 - base.p95
    explanation = f">>> Δavg: {delta_avg:.2f} ms, Δp95: {delta_p95:.2f} ms\n"
    if math.isnan(delta_avg) or math.isnan(delta_p95):
        return "Unknown", explanation + "Insufficient data."
    if delta_p95 <= 2 and delta_avg <= 1:
        return "Excellent", explanation + "No meaningful latency growth under load."
    if delta_p95 <= 10 and delta_avg <= 5:
        return "Good", explanation + "Small latency growth under load."
    if delta_p95 <= 25 and delta_avg <= 15:
        return "Fair", explanation + "Noticeable latency growth under load."
    return "Poor", explanation + "Significant latency growth under load."


def pick_probe_host(download_urls: List[str]) -> str:
    if not download_urls:
        return "1.1.1.1"
    host = urllib.parse.urlparse(download_urls[0]).hostname or "1.1.1.1"
    return host


def main():
    parser = argparse.ArgumentParser(description="Oprobe Bufferbloat-like Latency Under Load")
    parser.add_argument("--baseline", type=float, default=BASELINE_DURATION)
    parser.add_argument("--load",     type=float, default=LOAD_DURATION)
    parser.add_argument("--period",   type=float, default=SAMPLE_PERIOD)
    parser.add_argument("--discard",  type=int,   default=WARMUP_DISCARD)
    parser.add_argument("--dl", nargs="+", default=DEFAULT_DOWNLOAD_URLS)
    parser.add_argument("--ul", nargs="+", default=DEFAULT_UPLOAD_URLS)
    parser.add_argument("--num-dl", type=int, default=4)
    parser.add_argument("--num-ul", type=int, default=2)   # ← Varsayılan: 2 upload akışı
    parser.add_argument("--tls-probe", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--enable-upload", action="store_true",
                        help="Kısayol: upload akışlarını (2) açar; --ul listesi kullanılacaktır.")
    args = parser.parse_args()

    # Kısayol bayrağı verilmişse UL akışlarını aç
    if args.enable_upload and args.num_ul == 0:
        args.num_ul = 2

    probe_host = pick_probe_host(args.dl)
    timeout     = float(args.timeout)

    print("=== Bufferbloat-like Latency Under Load ===")
    print(f"Baseline: {int(args.baseline)}s  | Load: {int(args.load)}s")
    print(f"Probe host: {probe_host}:443")
    print(f"Sample period: {args.period:.2f}s, timeout: {timeout:.1f}s, discard first {args.discard} samples/phase")
    print(f"Load: {args.num_dl}x download -> {', '.join(args.dl)}")
    if args.num_ul > 0 and args.ul:
        print(f"      {args.num_ul}x upload   -> {', '.join(args.ul)}")
    else:
        print("      (no upload streams)")
    print("======================================================================\n")

    # Sinyal için bağlam
    baseline_buf: List[float] = []
    load_buf: List[float] = []

    def handle_signal(signum, frame):
        print(f"\n>>> Received signal {signum}. Printing partial results...")
        # Baseline partial
        if baseline_buf:
            bvals = baseline_buf[args.discard:] if len(baseline_buf) > args.discard else baseline_buf[:]
            bstats = compute_stats(bvals)
            print(printable_stats("Baseline Summary (partial)", bstats))
        # Load partial
        if load_buf:
            lvals = load_buf[args.discard:] if len(load_buf) > args.discard else load_buf[:]
            lstats = compute_stats(lvals)
            print(printable_stats("Under Load Summary (partial)", lstats))
        # Skor partial (her ikisi de varsa)
        if baseline_buf and load_buf:
            bvals = baseline_buf[args.discard:] if len(baseline_buf) > args.discard else baseline_buf[:]
            lvals = load_buf[args.discard:] if len(load_buf) > args.discard else load_buf[:]
            score, expl = decide_score(compute_stats(bvals), compute_stats(lvals))
            print(f">>> Bufferbloat score (partial): {score}")
            print(expl)
        raise SystemExit(143)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Phase 1: Baseline
    print("--- Phase 1: Baseline (no load) ---")
    base_values = measure_phase(probe_host, args.baseline, args.period, args.tls_probe, args.discard,
                                timeout, shared_buffer=baseline_buf)
    base_stats = compute_stats(base_values)
    print(printable_stats("Baseline Summary", base_stats))

    # Phase 2: Under Load
    print("--- Phase 2: Under Load ---")
    stop_evt, threads = start_load(args.dl, args.ul, args.num_dl, args.num_ul, timeout)
    try:
        load_values = measure_phase(probe_host, args.load, args.period, args.tls_probe, args.discard,
                                    timeout, shared_buffer=load_buf)
    finally:
        stop_load(stop_evt, threads)
    load_stats = compute_stats(load_values)
    print(printable_stats("Under Load Summary", load_stats))

    score, expl = decide_score(base_stats, load_stats)
    print(f">>> Bufferbloat score: {score}")
    print(expl)
    print("Test complete.")


if __name__ == "__main__":
    main()
