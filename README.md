📄 README.md
# oprobe_software_agent

---

## English

### Purpose
`oprobe_software_agent` is a desktop software tool designed to run and manage **Oprobe network performance tests** through a graphical interface.  
It integrates all Oprobe test modules (DNS resolution latency, HTTPS latency, NTP synchronization, jitter, bufferbloat, Wi-Fi analysis, meeting simulation, etc.) into a single GUI application.

The program helps network engineers and administrators:
- Monitor latency, jitter, and packet loss,
- Perform real-time Wi-Fi and internet performance analysis,
- Run performance simulations for video conferencing,
- Detect and observe bufferbloat problems.

---

### Features
- GUI with **Start/Stop** controls  
- Live logs visible in both **GUI** and **Terminal**  
- Automatic saving of reports into the `results/` folder  
- Report browser to view past test results  
- Modular test design (each test is its own `.py` file)  
- Cross-platform support (macOS, Linux, Windows)

---

### Requirements

#### Python Standard Libraries
- `os`, `sys`, `subprocess`, `threading`, `queue`, `time`, `shlex`, `datetime`
- `tkinter` (for GUI)

#### External Packages
- `requests` (for HTTP tests)  
- `ntplib` (for NTP synchronization test)

#### Installation
**macOS / Linux (Debian/Ubuntu):**
```bash
sudo apt install python3 python3-tk
pip install requests ntplib
Windows:
Install Python 3.8+
Then run:
pip install requests ntplib
Supported Operating Systems
macOS (with full Terminal.app integration)
Linux (tested on Debian/Ubuntu)
Windows 10/11 (GUI works, Terminal integration limited)
Usage
Start the GUI
python3 oprobe_software_agent.py
Run all tests at once
python3 run_all_tests.py
Run tests individually
python3 dns_resol_latency.py
python3 https_latency.py
python3 ntp_test.py
python3 jitter_test.py
python3 bufferbloat_like_test.py
python3 meeting_test.py
python3 wificheck.py
All results are saved in the results/ folder as timestamped .txt files.
Folder Structure
project-root/
 ├── oprobe_software_agent.py   # GUI desktop app
 ├── run_all_tests.py           # Master test runner
 ├── dns_resol_latency.py       # DNS resolution latency test
 ├── https_latency.py           # HTTPS latency test
 ├── ntp_test.py                # NTP synchronization test
 ├── jitter_test.py             # Jitter measurement
 ├── bufferbloat_like_test.py   # Bufferbloat test
 ├── meeting_test.py            # Video conference simulation test
 ├── wificheck.py               # Real-time Wi-Fi analysis
 └── results/                   # Test outputs (auto-created)
License
This project is part of the Oprobe initiative.
Internal use for Oxoo Networks and related projects.
Türkçe
Amaç
oprobe_software_agent, Oprobe ağ performans testlerini masaüstünden yönetmek için geliştirilmiş bir yazılımdır.
DNS çözümleme gecikmesi, HTTPS gecikmesi, NTP senkronizasyonu, jitter, bufferbloat, Wi-Fi analizi, toplantı simülasyonu gibi tüm test modüllerini tek bir grafik arayüz altında toplar.
Program, ağ yöneticilerine:
Gecikme, jitter ve paket kaybını izleme,
Gerçek zamanlı Wi-Fi ve internet performans analizi yapma,
Video konferans uygulamaları için performans testi yapma,
Bufferbloat sorunlarını tespit etme
konularında yardımcı olur.
Özellikler
GUI ile Başlat/Durdur kontrolü
Canlı loglar hem GUI hem Terminal üzerinde
Test sonuçlarını results/ klasörüne otomatik kaydetme
Rapor listesi ve seçili raporun içeriğini görüntüleme
Modüler test yapısı (her test ayrı .py dosyası)
Çoklu işletim sistemi desteği (macOS, Linux, Windows)
Gereken Kütüphaneler
Python Standart Kütüphaneler
os, sys, subprocess, threading, queue, time, shlex, datetime
tkinter (GUI için)
Harici Paketler
requests (HTTP testleri için)
ntplib (NTP testi için)
Kurulum
macOS / Linux (Debian/Ubuntu):
sudo apt install python3 python3-tk
pip install requests ntplib
Windows:
Python 3.8+ kurulu olmalı
Sonrasında:
pip install requests ntplib
Desteklenen İşletim Sistemleri
macOS (Terminal.app entegrasyonu ile tam uyumlu)
Linux (Debian/Ubuntu üzerinde test edildi)
Windows 10/11 (GUI çalışır, Terminal entegrasyonu sınırlı olabilir)
Kullanım
GUI Başlatma
python3 oprobe_software_agent.py
Tüm testleri çalıştırma
python3 run_all_tests.py
Testleri ayrı ayrı çalıştırma
python3 dns_resol_latency.py
python3 https_latency.py
python3 ntp_test.py
python3 jitter_test.py
python3 bufferbloat_like_test.py
python3 meeting_test.py
python3 wificheck.py
Tüm sonuçlar results/ klasöründe zaman damgalı .txt dosyaları olarak kaydedilir.
Klasör Yapısı
project-root/
 ├── oprobe_software_agent.py   # GUI masaüstü uygulaması
 ├── run_all_tests.py           # Tüm testleri çalıştıran ana script
 ├── dns_resol_latency.py       # DNS çözümleme testi
 ├── https_latency.py           # HTTPS gecikme testi
 ├── ntp_test.py                # NTP senkronizasyon testi
 ├── jitter_test.py             # Jitter ölçümü
 ├── bufferbloat_like_test.py   # Bufferbloat testi
 ├── meeting_test.py            # Toplantı simülasyonu
 ├── wificheck.py               # Gerçek zamanlı Wi-Fi analizi
 └── results/                   # Test sonuçları (otomatik oluşturulur)
