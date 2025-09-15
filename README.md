# Oprobe Combined Test Runner

This repository contains `run_all_tests.py`, a **single-entry** test orchestrator that launches multiple network health checks (DNS, HTTPS, NTP, jitter, bufferbloat-like, meeting test, and Wi‑Fi check) and collects **all outputs into one TXT report** with clear sections per test.

> **Key behavior:** If the agent’s primary connection is **Ethernet (BaseT)**, the Wi‑Fi test (`wificheck.py`) is **automatically skipped** and the combined report includes:
>
> ```
> ### wificheck.py ###
> Started: 2025-09-15T14:xx:xx
> STATUS: SKIPPED
> REASON: This agent connection BaseT
> ======================================================================
> ```

---

## Contents

- [Features](#features)
- [Test Suite](#test-suite)
- [How It Works](#how-it-works)
- [Output](#output)
- [Supported Linux Versions](#supported-linux-versions)
- [Prerequisites](#prerequisites)
  - [System packages (Linux)](#system-packages-linux)
  - [Python libraries](#python-libraries)
- [Installation](#installation)
  - [Virtualenv (recommended)](#virtualenv-recommended)
- [Usage](#usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Extending / Adding New Tests](#extending--adding-new-tests)
- [FAQ](#faq)

---

## Features

- Runs a curated set of network tests for **N** seconds each (default: `30`).
- Collects **stdout** and **stderr** for each test into a **single TXT file**.
- **Gracefully terminates** each test after the allotted duration (process group handling).
- Cleans up temporary directories left by some tests.
- **Smart Wi‑Fi logic:** detects primary egress interface; if it’s not wireless, Wi‑Fi test is skipped and the report notes **“This agent connection BaseT”**.

---

## Test Suite

The default `TESTS` list in `run_all_tests.py` is:

- `dns_resol_latency.py` — DNS resolve latency, avg latency in ms.
- `https_latency.py` — HTTPS request latency, avg latency in ms.
- `ntp_test.py` — NTP round-trip delay (requires `ntplib`), ms.
- `jitter_test.py` — Basic jitter summary (avg in ms).
- `bufferbloat_like_test.py` — Baseline vs load latency using parallel transfers.
- `meeting_test.py` — Meeting/RTC-like latency sampler (avg in ms).
- `wificheck.py` — Real-time Wi‑Fi snapshot: SSID/BSSID, channel/band, RSSI, SNR, basic GW/Internet ping, DHCP/DNS/Auth statuses. **Skipped on BaseT.**

> Not all scripts need to exist for the runner to work; missing tests will be reported in the combined output with a clear error block.

---

## How It Works

1. `run_all_tests.py` computes a batch timestamp and prepares `results/`.
2. For each test:
   - Builds a `python3 -u <script.py>` command
   - Runs it for `RUN_DURATION` seconds
   - Gracefully terminates the process group
   - Appends a formatted block with **stdout** / **stderr** to the report
3. **Wi‑Fi detection**: the runner calls `ip route get 8.8.8.8` to detect the **primary egress interface**. If that interface is not recognized as wireless (no `/sys/class/net/<iface>/wireless` and not listed by `iw dev`), Wi‑Fi is considered **inactive** and `wificheck.py` is skipped.

---

## Output

- One consolidated TXT file per run:
  - `results/YYYYMMDD_HHMMSS_all_tests.txt`
- Structure:
  ```
  # Oprobe Combined Test Results
  Generated at 2025-09-15T14:27:31
  ======================================================================

  ### dns_resol_latency.py ###
  Started: ... | Ended: ...
  PID: ... | Duration: 30s | Return code: 0
  --- STDOUT ---
  ...
  --- STDERR ---
  ...
  ======================================================================

  ### wificheck.py ###
  Started: ... 
  STATUS: SKIPPED
  REASON: This agent connection BaseT
  ======================================================================
  ```

---

## Supported Linux Versions

The runner targets modern Linux systems with `iproute2` and `iw`. Verified families:

- **Ubuntu**: 20.04 LTS, 22.04 LTS, 24.04 LTS
- **Debian**: 11 (Bullseye), 12 (Bookworm)
- **Raspberry Pi OS**: Bullseye / Bookworm (ARM; headless or desktop)
- **Fedora**: 38, 39, 40
- **Rocky / AlmaLinux**: 8, 9

> It should work on most Linux distros if `ip`, `iw`, and `python3` are available. macOS/Windows are not primary targets for the Wi‑Fi detection logic, but most tests can still run individually.

---

## Prerequisites

### System packages (Linux)

Install with your distro’s package manager:

**Debian/Ubuntu/Raspberry Pi OS:**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip iproute2 iw iputils-ping curl
```

**Fedora:**
```bash
sudo dnf install -y python3 python3-pip iproute iputils iw curl
```

**Rocky/AlmaLinux/CentOS (8/9):**
```bash
sudo dnf install -y python3 python3-pip iproute iputils iw curl
```

> `iputils-ping` might require root to send raw ICMP. Either run tests with `sudo`, or grant `cap_net_raw+ep` to the ping binary if needed.

### Python libraries

Create a virtualenv and install these libraries (superset to cover all included tests):

- `ntplib` — for NTP round-trip delay in `ntp_test.py`
- `requests` — common HTTP client (some tests may use it)
- `httpx` — async HTTP client (useful for bufferbloat-like test)
- `matplotlib` — used by `wificheck.py` (if graphing is enabled)
- `reportlab` — used by `wificheck.py` (if PDF output is enabled)

> If your test scripts import additional packages, include them similarly.

Quick install:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install ntplib requests httpx matplotlib reportlab
```

---

## Installation

Place all test scripts and `run_all_tests.py` in the **same directory**. Ensure executable permission (optional):
```bash
chmod +x run_all_tests.py
```

### Virtualenv (recommended)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install ntplib requests httpx matplotlib reportlab
```

---

## Usage

From the project directory:
```bash
python3 run_all_tests.py
```
- Output will be written to `results/YYYYMMDD_HHMMSS_all_tests.txt`

> **Wi‑Fi skip:** On BaseT, `wificheck.py` will be skipped automatically and the report will include “This agent connection BaseT”.

---

## Configuration

Open `run_all_tests.py` and adjust:

- `RUN_DURATION` — per-test runtime in seconds (default: `30`)
- `TESTS` — list of test script filenames
- `RESULTS_DIR` — output directory (default: `./results`)

---

## Troubleshooting

- **SyntaxError in runner**: Ensure you are on the updated `run_all_tests.py` (docstrings use standard triple quotes).
- **`iw: command not found`**: Install `iw` package (see prerequisites).
- **Wi‑Fi is active but still skipped**:
  - Verify the primary interface: `ip route get 8.8.8.8`
  - Check whether it appears in `iw dev` output.
  - Some drivers expose wireless under a different interface; you can adapt `_is_wireless_iface` logic if needed.
- **Ping requires root**: Either run `sudo python3 run_all_tests.py` or adjust capabilities for `ping`.
- **Missing Python modules**: Activate your venv and `pip install` the modules listed above.
- **No output (STDOUT)** for a test: That test may buffer output or only print at the end; the runner still captures whatever is printed within the run window.

---

## Extending / Adding New Tests

1. Drop your script (e.g., `my_new_test.py`) next to `run_all_tests.py`.
2. Add its filename to `TESTS` in `run_all_tests.py`.
3. (Optional) Extend `parse_metrics_from_text()` if you want to build a custom summary later.
4. Ensure your script prints useful runtime output to stdout/stderr.

---

## FAQ

**Q: Tek dosyalık rapor şart mı?**  
Evet, bu koşumlayıcı tek bir TXT dosyasına tüm çıktıları yazar. Gerektiğinde farklı formatlara (JSON/CSV/PDF) dönüştürülebilir.

**Q: Windows veya macOS’ta çalışır mı?**  
Çoğu test Python olduğundan çalışır, fakat **Wi‑Fi tespiti** Linux odaklıdır. Ethernet/BaseT tespiti Windows/macOS’ta farklı yöntemler gerektirir.

**Q: Wi‑Fi testini zorla çalıştırabilir miyim?**  
Evet, `is_wifi_active()` kontrolünü atlayacak bir bayrak ekleyebilir veya doğrudan `wificheck.py`’yi `TESTS` listesinden geçici çıkarabilirsiniz.
