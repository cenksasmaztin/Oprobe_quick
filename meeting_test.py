import os
import time
import subprocess
import platform
import re
import matplotlib.pyplot as plt
from datetime import datetime

# Dosya/klasör üretimini kapat
NO_ARTIFACTS = True

# Hedef sunucu adresleri
TARGET_SERVERS = {
    "Zoom": "zoom.us",
    "Teams": "teams.microsoft.com",
    "Google Meet": "meet.google.com"
}

# Klasör/rapor isimleri artık kullanılmıyor
REPORT_DIR = None

def ensure_directory_exists(directory):
    # NO_ARTIFACTS True ise hiçbir şey yapma
    if not NO_ARTIFACTS and directory and not os.path.exists(directory):
        os.makedirs(directory)

def ping_server(host):
    try:
        # İşletim sistemine göre ping komutu ayarlanır
        param = "-n" if platform.system().lower() == "windows" else "-c"
        cmd = ["ping", param, "1", host]
        output = subprocess.run(cmd, capture_output=True, text=True)
        latency = parse_latency(output.stdout)
        return latency
    except Exception:
        return None

def parse_latency(ping_output):
    # Latency değerlerini regex ile bulma
    latency_pattern = re.compile(r"time[=<]\s?(\d+\.?\d*)\s?ms")
    latencies = [float(match) for match in latency_pattern.findall(ping_output)]
    if latencies:
        return sum(latencies) / len(latencies)
    else:
        return None

def save_text_report(results):
    """Eskiden dosyaya yazıyordu; şimdi sadece stdout'a döküyoruz."""
    print("\n=== Meeting Latency Text Report ===")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    for server, data in results.items():
        vals = [v for v in data['latencies'] if v is not None]
        avg = (sum(vals)/len(vals)) if vals else float('nan')
        print(f"Server: {server}")
        if vals:
            print(f"Average Latency: {avg:.2f} ms")
        else:
            print("Average Latency: N/A")
        print("Details:")
        for ts, latency in zip(data['timestamps'], data['latencies']):
            print(f"  {ts} - {('%.2f ms' % latency) if latency is not None else 'Timeout'}")
        print("")
    print("=" * 50)

def save_graph(results):
    """Grafik dosyası kaydetmek yerine, NO_ARTIFACTS True ise hiçbir şey yapma.
       İstersen burada sadece ekrana kısa bir özet yazdırıyoruz."""
    if NO_ARTIFACTS:
        print("(Graph generation skipped: NO_ARTIFACTS=True)")
        return

    ensure_directory_exists(REPORT_DIR)
    plt.figure(figsize=(10, 6))
    for server, data in results.items():
        timestamps = [datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") for ts in data['timestamps']]
        plt.plot(timestamps, data['latencies'], label=server)
    plt.xlabel("Time")
    plt.ylabel("Latency (ms)")
    plt.title("Latency Test Results")
    plt.legend()
    plt.grid()
    graph_filename = os.path.join(REPORT_DIR, f"latency_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    plt.gcf().autofmt_xdate()
    plt.savefig(graph_filename)
    print(f"Graph saved as {graph_filename}")

def main():
    # Artık klasör oluşturmuyoruz
    results = {
        name: {"timestamps": [], "latencies": []} for name in TARGET_SERVERS.keys()
    }

    try:
        while True:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for name, host in TARGET_SERVERS.items():
                latency = ping_server(host)
                results[name]["timestamps"].append(now_str)
                results[name]["latencies"].append(latency)
                print(f"[{now_str}] {name} ({host}) -> {('%.2f ms' % latency) if latency is not None else 'Timeout'}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nLatency test interrupted. Generating final summary to stdout...")
        save_text_report(results)
        save_graph(results)
        print("Summary printed. Exiting.")

if __name__ == "__main__":
    os.environ["PYTHONUNBUFFERED"] = "1"
    main()
