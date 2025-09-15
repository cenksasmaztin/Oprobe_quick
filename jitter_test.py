#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jitter_test.py
- Hedef URL için periyodik HTTP HEAD isteği atarak gecikmeleri (ms) ölçer.
- Jitter metrikleri: stddev, IPDV (ardışık farkların ort. mutlak değeri), p95-p5 aralığı.
- Hiç dosya/klasör üretmez; sadece stdout'a yazar.
- Orkestratörün 30 sn sonra göndereceği SIGTERM'i yakalayıp özet basar.
"""

import os
import time
import signal
import math
from statistics import mean, pstdev
from datetime import datetime
import requests

# === AYARLAR ===
TARGET_URL = "https://www.microsoft.com"
METHOD = "HEAD"                 # GET de yapabilirsin ama HEAD daha hafif
REQUEST_TIMEOUT = 3.0           # saniye
SAMPLE_PERIOD = 0.5             # iki ölçüm arası bekleme (saniye)
USER_AGENT = "Oprobe-Jitter/1.0"

# Global durum (signal handler için)
_samples_ms = []     # float ms; timeout/başarısızlık için None ekleyeceğiz
_total = 0
_timeouts = 0
_running = True

def percentile(data_sorted, p):
    """Basit yüzdelik hesap (0..100), data_sorted: başarı ms listesi sıralı."""
    if not data_sorted:
        return None
    if p <= 0: return data_sorted[0]
    if p >= 100: return data_sorted[-1]
    k = (len(data_sorted)-1) * (p/100.0)
    f = math.floor(k); c = math.ceil(k)
    if f == c:
        return data_sorted[int(k)]
    d0 = data_sorted[f] * (c - k)
    d1 = data_sorted[c] * (k - f)
    return d0 + d1

def ipdv_mean_abs(rtts):
    """RFC 5481'e yakın: ardışık örnekler arası mutlak farkların ortalaması."""
    if len(rtts) < 2:
        return None
    diffs = [abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))]
    return mean(diffs)

def print_summary():
    """Program sonlanırken özet istatistikleri stdout'a yaz."""
    successes = [x for x in _samples_ms if x is not None]
    fail_count = sum(1 for x in _samples_ms if x is None)
    n = len(_samples_ms)

    print("\n=== Jitter Summary ===")
    print(f"Target     : {TARGET_URL}")
    print(f"Method     : {METHOD}")
    print(f"Samples    : {n}")
    print(f"Success    : {len(successes)}")
    print(f"Timeouts   : {fail_count} ({(fail_count/n*100):.1f}% if n>0 else 0.0)")
    if successes:
        mu = mean(successes)
        sd = pstdev(successes) if len(successes) > 1 else 0.0
        ipdv = ipdv_mean_abs(successes)
        srt = sorted(successes)
        p95 = percentile(srt, 95)
        p5  = percentile(srt, 5)
        spread = (p95 - p5) if (p95 is not None and p5 is not None) else None
        print(f"Avg (ms)   : {mu:.2f}")
        print(f"StdDev (ms): {sd:.2f}")
        print(f"IPDV  (ms) : {ipdv:.2f}" if ipdv is not None else "IPDV  (ms) : N/A")
        if spread is not None:
            print(f"p95-p5 (ms): {spread:.2f}  (p5={p5:.2f}, p95={p95:.2f})")
        else:
            print("p95-p5 (ms): N/A")
        print(f"Min/Max (ms): {min(successes):.2f} / {max(successes):.2f}")
    else:
        print("No successful samples.")
    print("=" * 50)

def _stop_handler(signum, frame):
    global _running
    _running = False
    # Özet hemen yazılsın
    print_summary()

def main():
    os.environ["PYTHONUNBUFFERED"] = "1"
    signal.signal(signal.SIGTERM, _stop_handler)
    signal.signal(signal.SIGINT, _stop_handler)

    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})

    print("=== HTTP Jitter Test ===")
    print(f"Target  : {TARGET_URL}")
    print(f"Method  : {METHOD}, timeout={REQUEST_TIMEOUT}s, period={SAMPLE_PERIOD}s")
    print("="*50)

    i = 1
    while _running:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        t0 = time.perf_counter()
        ok = True
        try:
            if METHOD.upper() == "HEAD":
                r = s.head(TARGET_URL, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            else:
                r = s.get(TARGET_URL, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            # sadece bağlantı kurup ilk bayta kadar geçen süreyi ölçmek istiyorsan stream=True + read(1) yapılabilir.
            status_ok = (200 <= r.status_code < 400)
        except requests.RequestException:
            ok = False
            status_ok = False

        dt_ms = (time.perf_counter() - t0) * 1000.0

        if ok and status_ok:
            _samples_ms.append(dt_ms)
            print(f"[{i:04d}] {ts}  {dt_ms:.2f} ms", flush=True)
        else:
            _samples_ms.append(None)
            print(f"[{i:04d}] {ts}  timeout/fail", flush=True)

        i += 1
        time.sleep(SAMPLE_PERIOD)

    # Eğer SIGTERM yerine normal çıkış olursa yine özet verelim
    if _running:  # değişmedi ise…
        print_summary()

if __name__ == "__main__":
    main()
