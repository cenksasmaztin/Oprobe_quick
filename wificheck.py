#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, sys, time, shutil, socket, platform, subprocess
from datetime import datetime
from typing import Dict, Optional, List

REFRESH_SEC = 3
INTERNAL_PING_HOST = "1.1.1.1"
PING_TIMEOUT_SEC = 1.5

HEADERS = [
    "Timestamp","MAC Address","SSID","AP","Frequency","Channel","Signal Strength",
    "Data Rate","Throughput","SNR","GTW Ping","INT Ping","DHCP","DNS","Auth","WIFI Performance"
]

IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

def run(cmd: List[str], timeout: float = 2.5) -> str:
    try:
        out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=timeout, check=False, text=True)
        return out.stdout.strip()
    except Exception:
        return ""

def which(x: str) -> Optional[str]:
    return shutil.which(x)

def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def hz_from_channel(ch: int) -> str:
    if ch <= 0: return "-"
    if 1 <= ch <= 14: return "2.4 GHz"
    if 36 <= ch <= 165: return "5 GHz"
    if 1 <= ch <= 233 and ch not in range(1,15) and not (36 <= ch <= 165): return "6 GHz"
    return "-"

def parse_ping_ms(output: str) -> Optional[float]:
    m = re.search(r"time[=<]\s*([\d\.]+)\s*ms", output)
    return float(m.group(1)) if m else None

def do_ping(host: Optional[str]) -> Optional[float]:
    if not host: return None
    if IS_MAC:
        out = run(["ping","-c","1","-n",host], timeout=PING_TIMEOUT_SEC)
    else:
        out = run(["ping","-c","1","-n","-w",str(int(PING_TIMEOUT_SEC)),host], timeout=PING_TIMEOUT_SEC+0.5)
    return parse_ping_ms(out)

def get_default_gateway() -> Optional[str]:
    if IS_MAC:
        out = run(["route","-n","get","default"], timeout=1.5)
        m = re.search(r"gateway:\s+([0-9\.]+)", out)
        return m.group(1) if m else None
    elif IS_LINUX:
        out = run(["ip","route","show","default"], timeout=1.5)
        m = re.search(r"default via ([0-9\.]+)", out)
        return m.group(1) if m else None
    return None

def resolv_conf_dns() -> List[str]:
    try:
        with open("/etc/resolv.conf") as f:
            return re.findall(r"^nameserver\s+([0-9a-fA-F:\.]+)", f.read(), re.M)
    except Exception:
        return []

# -------------------- macOS helpers --------------------
def mac_airport_path() -> Optional[str]:
    p = which("airport")
    if p: return p
    cand = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
    return cand if os.path.exists(cand) else None

def mac_iface_from_route() -> Optional[str]:
    out = run(["route","-n","get","default"], timeout=1.5)
    m = re.search(r"interface:\s*(\S+)", out)
    return m.group(1) if m else None

def mac_wifi_device() -> Optional[str]:
    # Primary: map "Hardware Port: Wi-Fi" -> Device
    out = run(["networksetup","-listallhardwareports"], timeout=2.5)
    blocks = re.split(r"\n\s*\n", out)
    for b in blocks:
        if "Wi-Fi" in b or "AirPort" in b:
            m = re.search(r"Device:\s*(\S+)", b)
            if m: return m.group(1)
    # Fallback to default-route iface if it looks like enX
    riface = mac_iface_from_route()
    if riface and riface.startswith("en"): return riface
    # Last resort guesses
    for g in ("en0","en1","en2"):
        if run(["ifconfig", g]): return g
    return None

def mac_wifi_info() -> Dict[str,str]:
    info: Dict[str,str] = {}
    iface = mac_wifi_device()
    if not iface:
        return info

    # MAC
    ifcfg = run(["ifconfig", iface], timeout=1.5)
    mm = re.search(r"ether\s+([0-9a-f\:]{17})", ifcfg, re.I)
    info["mac"] = mm.group(1) if mm else "-"

    # Try airport first (rich data)
    airport = mac_airport_path()
    airport_ok = False
    if airport:
        aout = run([airport,"-I"], timeout=2.5)
        if aout:
            airport_ok = True
            def g(key: str) -> Optional[str]:
                m = re.search(rf"^{key}:\s*(.+)$", aout, re.M)
                return m.group(1).strip() if m else None
            info["ssid"]   = g("SSID") or "-"
            info["bssid"]  = g("BSSID") or "-"
            rssi           = g("agrCtlRSSI")
            noise          = g("agrCtlNoise")
            info["rssi"]   = (rssi + " dBm") if rssi else "-"
            info["noise"]  = (noise + " dBm") if noise else "-"
            info["txrate"] = g("lastTxRate") or "-"
            ch_raw         = g("channel") or "-"
            chm = re.match(r"(\d+)", ch_raw)
            ch_num = int(chm.group(1)) if chm else -1
            info["channel"]= str(ch_num) if ch_num>0 else "-"
            info["freq"]   = hz_from_channel(ch_num)

            # Auth (varies by OS)
            info["auth"]   = g("link auth") or g("agrCtlSecurity") or "-"

    # Fallbacks if airport failed or gave blanks
    # SSID
    if not info.get("ssid") or info["ssid"] in ("-",""):
        ss = run(["networksetup","-getairportnetwork", iface], timeout=1.5)
        # "Current Wi-Fi Network: MySSID"
        m = re.search(r"Network:\s*(.+)$", ss)
        if m: info["ssid"] = m.group(1).strip()
        else: info["ssid"] = "-"

    # BSSID / Channel / Auth via system_profiler (slower but works)
    if (not info.get("bssid") or info["bssid"] in ("-","")) or \
       (not info.get("channel") or info["channel"] in ("-","")) or \
       (not info.get("auth") or info["auth"] in ("-","")):
        prof = run(["system_profiler","SPAirPortDataType","-detailLevel","mini"], timeout=4.0)
        # Active data usually under "Current Network Information:"
        cur = re.search(r"Current Network Information:(.*?)(?:\n\n|\Z)", prof, re.S)
        block = cur.group(1) if cur else prof
        if not info.get("bssid") or info["bssid"] in ("-",""):
            m = re.search(r"BSSID:\s*([0-9a-f:]{17})", block, re.I)
            if m: info["bssid"] = m.group(1)
        if not info.get("channel") or info["channel"] in ("-",""):
            mc = re.search(r"Channel:\s*(\d+)", block)
            if mc:
                info["channel"] = mc.group(1)
                try:
                    info["freq"] = hz_from_channel(int(mc.group(1)))
                except Exception:
                    pass
        if not info.get("auth") or info["auth"] in ("-",""):
            ma = re.search(r"Security:\s*(.+)", block)
            if ma: info["auth"] = ma.group(1).strip()

    # DNS
    scdns = run(["scutil","--dns"], timeout=2.5)
    dns = re.findall(r"nameserver\[[0-9]+\]\s*:\s*([0-9a-fA-F\:\.]+)", scdns)
    info["dns"] = ", ".join(dns[:2]) if dns else "-"

    # DHCP server
    dh = run(["ipconfig","getpacket", iface], timeout=2.5)
    dm = re.search(r"server_identifier\s*=\s*([0-9\.]+)", dh)
    info["dhcp"] = dm.group(1) if dm else "-"

    # If still absolutely nothing useful, return {}
    if all(info.get(k, "-") in ("-","") for k in ("ssid","bssid","mac")):
        return {}
    return info

# -------------------- Linux (same as önceki sürüm) --------------------
def linux_wifi_iface() -> Optional[str]:
    iw = which("iw")
    if iw:
        out = run([iw,"dev"], timeout=2.0)
        for b in re.split(r"\n\s*\n", out):
            if "type managed" in b:
                m = re.search(r"Interface\s+(\S+)", b)
                if m: return m.group(1)
    for g in ("wlan0","wlp2s0","wlp3s0","wlp0s20f3","wlx"):
        if os.path.exists(f"/sys/class/net/{g}"): return g
    return None

def linux_wifi_info() -> Dict[str,str]:
    info: Dict[str,str] = {}
    iface = linux_wifi_iface()
    if not iface: return info
    try:
        with open(f"/sys/class/net/{iface}/address") as f:
            info["mac"] = f.read().strip()
    except Exception:
        info["mac"] = "-"
    iw = which("iw")
    iwgetid = which("iwgetid")
    if iw:
        out = run([iw,"dev",iface,"link"], timeout=2.0)
        m_b = re.search(r"Connected to\s+([0-9a-f\:]{17})", out, re.I)
        m_s = re.search(r"SSID:\s*(.+)", out)
        m_f = re.search(r"freq:\s*(\d+)", out)
        m_ch= re.search(r"channel\s*(\d+)", out)
        m_sig=re.search(r"signal:\s*(-?\d+)\s*dBm", out)
        m_br =re.search(r"tx bitrate:\s*([\d\.]+\s*[A-Za-z/]+)", out)
        info["bssid"] = m_b.group(1) if m_b else "-"
        info["ssid"]  = m_s.group(1).strip() if m_s else "-"
        if m_f:
            f=int(m_f.group(1))
            info["freq"] = "2.4 GHz" if 2400<=f<=2500 else ("5 GHz" if 4900<=f<=5900 else ("6 GHz" if 5925<=f<=7125 else f"{f} MHz"))
        else:
            info["freq"]="-"
        info["channel"]= m_ch.group(1) if m_ch else "-"
        info["rssi"]   = (m_sig.group(1)+" dBm") if m_sig else "-"
        info["noise"]  = "-"
        info["txrate"] = m_br.group(1) if m_br else "-"
    if (not info.get("ssid") or info["ssid"]=="-") and iwgetid:
        ss = run([iwgetid,"-r"], timeout=1.0)
        if ss: info["ssid"] = ss.strip()
    dns_list = resolv_conf_dns()
    info["dns"] = ", ".join(dns_list[:2]) if dns_list else "-"
    info["dhcp"]= "-"
    wpa = which("wpa_cli")
    if wpa:
        st = run([wpa,"status"], timeout=1.5)
        m = re.search(r"key_mgmt=([^\n]+)", st)
        info["auth"] = m.group(1) if m else "-"
    else:
        info["auth"]="-"
    return info

def compute_snr(rssi: str, noise: str) -> str:
    try:
        r = float(str(rssi).replace(" dBm","").strip())
        n = float(str(noise).replace(" dBm","").strip())
        return f"{int(r-n)} dB"
    except Exception:
        return "-"

def rate_pretty(rate: str) -> str:
    if not rate or rate == "-": return "-"
    m = re.search(r"([\d\.]+)\s*([A-Za-z/]+)", rate)
    if not m: return rate
    v = float(m.group(1)); u = m.group(2).lower()
    if "gbps" in u or "gbit" in u: return f"{v*1000:.0f} Mbps"
    if "mbps" in u or "mbit" in u: return f"{v:.0f} Mbps"
    if "kbit" in u or "kbps" in u: return f"{v/1000:.1f} Mbps"
    return f"{v} {m.group(2)}"

def classify_perf(signal: str, snr: str, gtw_ms: Optional[float], int_ms: Optional[float]) -> str:
    score = 0
    try:
        sig = float(signal.replace(" dBm","").strip())
        score += 3 if sig>=-55 else 2 if sig>=-65 else 1 if sig>=-75 else 0
    except Exception: pass
    try:
        s = int(snr.replace(" dB","").strip())
        score += 3 if s>=30 else 2 if s>=20 else 1 if s>=10 else 0
    except Exception: pass
    if gtw_ms is not None:
        score += 3 if gtw_ms<=3 else 2 if gtw_ms<=8 else 1 if gtw_ms<=20 else 0
    if int_ms is not None:
        score += 3 if int_ms<=10 else 2 if int_ms<=25 else 1 if int_ms<=60 else 0
    return "Excellent" if score>=9 else "Good" if score>=6 else "Fair" if score>=3 else "Poor"

def display_header():
    print("Real-Time Wi-Fi Analysis Started (Press CTRL+C to stop)")
    widths = [19,17,12,18,10,7,16,12,14,6,8,8,6,8,6,16]
    cols = ["{:<19}"] + ["{:>"+str(w)+"}" for w in widths[1:]]
    print(" ".join(fmt.format(h) for fmt,h in zip(cols,HEADERS)))

def render_row(fields: List[str]):
    widths = [19,17,12,18,10,7,16,12,14,6,8,8,6,8,6,16]
    out = []
    for i,(v,w) in enumerate(zip(fields,widths)):
        v = v if v not in (None,"") else "-"
        v = (v[:w-1]+"…") if len(v)>w else v
        out.append(("{:<"+str(w)+"}" if i==0 else "{:>"+str(w)+"}").format(v))
    print(" ".join(out))

def not_connected_row() -> List[str]:
    return [ts()] + ["-"]*(len(HEADERS)-1)

def main_loop():
    display_header()
    while True:
        try:
            if IS_MAC:
                wi = mac_wifi_info()
            elif IS_LINUX:
                wi = linux_wifi_info()
            else:
                wi = {}

            if not wi or wi.get("ssid","-") in ("-",""):
                render_row(not_connected_row())
                time.sleep(REFRESH_SEC); continue

            mac = wi.get("mac","-")
            ssid= wi.get("ssid","-")
            bssid=wi.get("bssid","-")
            freq= wi.get("freq","-")
            chan= wi.get("channel","-")
            rssi= wi.get("rssi","-")
            noise=wi.get("noise","-")
            tx  = rate_pretty(wi.get("txrate","-"))
            auth= wi.get("auth","-")

            snr = compute_snr(rssi, noise) if rssi!="-" and noise!="-" else "-"

            gw = get_default_gateway()
            gms = do_ping(gw)
            ims = do_ping(INTERNAL_PING_HOST)
            gstr = f"{gms:.3f} ms" if gms is not None else "-"
            istr = f"{ims:.3f} ms" if ims is not None else "-"

            dns = wi.get("dns","-")
            dhcp= wi.get("dhcp","-")
            thr = "-"

            perf = classify_perf(rssi, snr, gms, ims)

            row = [ts(), mac, ssid, bssid, freq, str(chan) if chan else "-",
                   rssi, tx, thr, snr, gstr, istr, dhcp, dns, auth, perf]
            render_row(row)
            time.sleep(REFRESH_SEC)
        except KeyboardInterrupt:
            print("\nStopped."); break
        except Exception as e:
            sys.stderr.write(f"\n[WARN] {e}\n"); time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    if not (IS_MAC or IS_LINUX):
        print("This script currently supports macOS and Linux."); sys.exit(1)
    main_loop()
