# 📘 README – Oprobe Test Runner

---

## 🇹🇷 Türkçe

### 📌 Genel Bakış
`run_all_tests.py`, ağ performansı ve bağlantı kalitesini ölçmek için hazırlanmış test scriptlerini **periyodik aralıklarla** çalıştırır.  
Program başlatıldığında hemen bir test turu yapar, ardından **CTRL+C ile durdurulana kadar her 10 dakikada bir** testleri tekrarlar.  

Her turda sonuçlar `results/` klasöründe zaman damgalı (`YYYYMMDD_HHMMSS_all_tests.txt`) bir dosyaya kaydedilir.

---

### 🔍 Çalışan Testler
- **dns_resol_latency.py** – DNS çözümleme gecikmesi  
- **https_latency.py** – HTTPS bağlantı gecikmesi  
- **ntp_test.py** – NTP senkronizasyon gecikmesi  
- **jitter_test.py** – Jitter (gecikme dalgalanması)  
- **bufferbloat_like_test.py** – Bufferbloat etkisi  
- **meeting_test.py** – Online toplantı simülasyonu  
- **wificheck.py** – Kablosuz bağlantı kalitesi  
  > ⚠️ Kablolu (BaseT) bağlantıda `wificheck.py` otomatik atlanır.

---

### 📂 Çıktılar
- Tüm raporlar `results/` klasörüne yazılır.  
- Her tur için **yeni dosya** oluşturulur:  

```
results/
 ├── 20250917_220500_all_tests.txt
 ├── 20250917_221500_all_tests.txt
 └── ...
```

---

### ⚙️ Kurulum
1. Python 3.8+  
2. Gerekli kütüphaneler:
   ```bash
   pip install ntplib
   ```
3. Sistem araçları:
   - `ip`
   - `iw`

---

### ▶️ Kullanım
```bash
python3 run_all_tests.py
```

- Başlatıldığında ilk tur hemen yapılır.  
- Ardından **10 dakikada bir** tekrarlanır.  
- Durdurmak için `CTRL+C`.  

---

### 🔧 Ayarlar
- **RUN_DURATION** → her testin çalışma süresi (sn)  
- **INTERVAL_SECONDS** → testler arası bekleme süresi (sn)  

---

### 📑 Örnek Çıktılar
**dns_resol_latency.py**
```
### dns_resol_latency.py ###
Started: 2025-09-17T22:05:01  |  Ended: 2025-09-17T22:05:31
PID: 1234  |  Duration: 30s  |  Return code: 0
--- STDOUT ---
google.com latency: 1.2 ms
cloudflare.com latency: 0.8 ms
Average latency: 1.0 ms
--- STDERR ---
(No errors)
======================================================================
```

**https_latency.py**
```
### https_latency.py ###
Started: 2025-09-17T22:06:01  |  Ended: 2025-09-17T22:06:31
PID: 1250  |  Duration: 30s  |  Return code: 0
--- STDOUT ---
HTTPS Latency (avg): 45.7 ms
--- STDERR ---
(No errors)
======================================================================
```

**wificheck.py (kablolu bağlantıda)**  
```
### wificheck.py ###
Started: 2025-09-17T22:08:01
STATUS: SKIPPED
REASON: This agent connection BaseT
======================================================================
```

---

## 🇬🇧 English

### 📌 Overview
`run_all_tests.py` executes multiple network performance test scripts at **periodic intervals**.  
When started, it immediately runs one test round, then **repeats every 10 minutes until stopped with CTRL+C**.  

Each round generates a new timestamped file (`YYYYMMDD_HHMMSS_all_tests.txt`) inside the `results/` directory.

---

### 🔍 Included Tests
- **dns_resol_latency.py** – DNS resolution latency  
- **https_latency.py** – HTTPS connection latency  
- **ntp_test.py** – NTP synchronization delay  
- **jitter_test.py** – Jitter measurement  
- **bufferbloat_like_test.py** – Bufferbloat effect  
- **meeting_test.py** – Online meeting simulation  
- **wificheck.py** – Wireless connection quality  
  > ⚠️ Skipped automatically if the device is on wired (BaseT).

---

### 📂 Output
- All reports are stored in `results/`.  
- Each test round creates a **new file**:  

```
results/
 ├── 20250917_220500_all_tests.txt
 ├── 20250917_221500_all_tests.txt
 └── ...
```

---

### ⚙️ Installation
1. Python 3.8+  
2. Required libraries:
   ```bash
   pip install ntplib
   ```
3. System tools:
   - `ip`
   - `iw`

---

### ▶️ Usage
```bash
python3 run_all_tests.py
```

- Runs immediately once.  
- Repeats every **10 minutes**.  
- Stop with `CTRL+C`.  

---

### 🔧 Configuration
- **RUN_DURATION** → how long each test runs (seconds)  
- **INTERVAL_SECONDS** → interval between test rounds (seconds)  

---

### 📑 Sample Output
**dns_resol_latency.py**
```
### dns_resol_latency.py ###
Started: 2025-09-17T22:05:01  |  Ended: 2025-09-17T22:05:31
PID: 1234  |  Duration: 30s  |  Return code: 0
--- STDOUT ---
google.com latency: 1.2 ms
cloudflare.com latency: 0.8 ms
Average latency: 1.0 ms
--- STDERR ---
(No errors)
======================================================================
```

**https_latency.py**
```
### https_latency.py ###
Started: 2025-09-17T22:06:01  |  Ended: 2025-09-17T22:06:31
PID: 1250  |  Duration: 30s  |  Return code: 0
--- STDOUT ---
HTTPS Latency (avg): 45.7 ms
--- STDERR ---
(No errors)
======================================================================
```

**wificheck.py (wired connection)**  
```
### wificheck.py ###
Started: 2025-09-17T22:08:01
STATUS: SKIPPED
REASON: This agent connection BaseT
======================================================================
```
