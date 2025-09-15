import requests
import time
import os
from datetime import datetime

# Dosya/klasör üretimini kapat
NO_ARTIFACTS = True

# Test edilecek HTTPS adresleri
HTTPS_LIST = [
    "https://www.google.com", "https://www.facebook.com", "https://www.amazon.com", 
    "https://www.yahoo.com", "https://www.wikipedia.org", "https://www.twitter.com", 
    "https://www.instagram.com", "https://www.linkedin.com", "https://www.microsoft.com", 
    "https://www.apple.com", "https://www.netflix.com", "https://www.reddit.com",
    "https://www.yandex.ru", "https://www.baidu.com", "https://www.bing.com", 
    "https://www.ebay.com", "https://www.bbc.co.uk", "https://www.cnn.com", 
    "https://www.espn.com", "https://www.spotify.com"
]

TIMEOUT = 5  # saniye

def measure_latency(url):
    start_time = time.time()
    try:
        r = requests.get(url, timeout=TIMEOUT)
        elapsed = (time.time() - start_time) * 1000  # ms
        if r.status_code == 200:
            return elapsed
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def perform_https_test():
    latencies = []
    for url in HTTPS_LIST:
        try:
            latency = measure_latency(url)
            if latency is not None:
                latencies.append(latency)
            else:
                latencies.append(None)
        except requests.exceptions.RequestException:
            latencies.append(None)
    return latencies

def summarize_results(test_number, latencies):
    values = [lat for lat in latencies if lat is not None]
    avg_latency = sum(values) / len(values) if values else float('nan')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Ekrana yaz (dosya yok / klasör yok)
    print(f"\n=== HTTPS Latency Test #{test_number} ===")
    print(f"Timestamp: {timestamp}")
    for url, latency in zip(HTTPS_LIST, latencies):
        print(f"{url}: {latency if latency is not None else 'Timeout'} ms")
    if values:
        print(f"Average Latency: {avg_latency:.2f} ms")
    else:
        print("Average Latency: N/A (no successful responses)")
    print("=" * 50)
    return avg_latency

def main():
    test_number = 1
    while True:
        print(f"Starting Test #{test_number}")
        latencies = perform_https_test()
        summarize_results(test_number, latencies)
        test_number += 1
        time.sleep(60)  # 1 dakika bekle

if __name__ == "__main__":
    # unbuffered çıktı (orkestratör toplayabilsin diye)
    os.environ["PYTHONUNBUFFERED"] = "1"
    main()
