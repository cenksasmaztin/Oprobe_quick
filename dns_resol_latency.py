#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, time, shutil, socket, subprocess
from datetime import datetime

NO_ARTIFACTS = True
DOMAINS = ["google.com","cloudflare.com","microsoft.com","amazon.com","apple.com","wikipedia.org"]
QUERY_TIMEOUT_SEC = 2.0

DIG = shutil.which("dig")
NSLOOKUP = shutil.which("nslookup")
RESOLVECTL = shutil.which("resolvectl")
GETENT = shutil.which("getent")

def get_system_dns():
    ips = []
    # 1) resolvectl
    if RESOLVECTL:
        try:
            out = subprocess.run([RESOLVECTL, "status"], capture_output=True, text=True, timeout=3).stdout
            for line in out.splitlines():
                if "DNS Servers" in line or re.search(r"\bDNS:\b", line):
                    ips += re.findall(r"(?:(?:\d{1,3}\.){3}\d{1,3})|(?:[A-Fa-f0-9:]+(?:%\w+)?)", line)
        except Exception:
            pass
    # 2) resolv.conf
    try:
        with open("/etc/resolv.conf","r",encoding="utf-8",errors="ignore") as f:
            for ln in f:
                ln = ln.strip()
                if ln.startswith("nameserver"):
                    parts = ln.split()
                    if len(parts)>=2:
                        ips.append(parts[1])
    except Exception:
        pass

    # benzersiz ve loopback en sona
    def is_loopback(ip): return ip in {"127.0.0.1","127.0.0.53","::1"}
    seen=set(); uniq=[]
    for ip in ips:
        if ip not in seen:
            seen.add(ip); uniq.append(ip)
    non_loop=[i for i in uniq if not is_loopback(i)]
    loop=[i for i in uniq if is_loopback(i)]
    return non_loop+loop

def _run(cmd, timeout):
    try:
        t0 = time.monotonic()
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        dt = (time.monotonic()-t0)*1000.0
        return p.returncode, p.stdout, p.stderr, round(dt,2)
    except subprocess.TimeoutExpired:
        return 124, "", "timeout", None
    except Exception as e:
        return 125, "", str(e), None

def dig_query(server, domain, use_tcp=False, qtype="A"):
    if not DIG: return None, "dig_missing"
    cmd = [DIG, f"@{server}", domain, qtype, "+tries=1", f"+time={int(QUERY_TIMEOUT_SEC)}", "+short"]
    if use_tcp: cmd.append("+tcp")
    rc, out, err, dt = _run(cmd, QUERY_TIMEOUT_SEC+0.5)
    if rc==0 and out.strip():
        return dt, None
    if rc==0 and not out.strip():
        # bazı durumlarda NOERROR ama cevap boş olabilir (dt yine de anlamlı)
        return dt, "dig_noanswer"
    if rc==124: return None, "dig_timeout"
    return None, f"dig_rc{rc}"

def nslookup_query(server, domain):
    if not NSLOOKUP: return None, "nslookup_missing"
    cmd = [NSLOOKUP, domain, server]
    rc, out, err, dt = _run(cmd, QUERY_TIMEOUT_SEC+0.5)
    if rc==0 and re.search(r"Address:\s", out): return dt, None
    if rc==124: return None, "nslookup_timeout"
    return None, f"nslookup_rc{rc}"

def system_resolver_query(domain):
    # En güvenlisi: socket.getaddrinfo süre ölçümü
    t0 = time.monotonic()
    try:
        socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
        dt = (time.monotonic()-t0)*1000.0
        return round(dt,2), None
    except socket.gaierror:
        # yedek: getent hosts
        if GETENT:
            rc, out, err, dt = _run([GETENT,"hosts",domain], QUERY_TIMEOUT_SEC+0.5)
            if rc==0 and out.strip(): return dt, None
            if rc==124: return None, "getent_timeout"
        return None, "resolver_error"

def normalize_ipv6_scope_for_tool(server, tool="dig"):
    # dig @fe80::1%eth0 destekler; nslookup genelde etmez. nslookup için %iface'i düşür.
    if "%" in server and tool=="nslookup":
        return server.split("%",1)[0]
    return server

def measure_server(server, domains):
    diags = []  # kısaca neden başarısız oldu
    lats = []
    for d in domains:
        # Önce dig UDP A, sonra AAAA, sonra dig TCP, sonra nslookup, en sonda sistem resolver
        val=None; reason=None

        if DIG:
            # UDP A
            val, reason = dig_query(server, d, use_tcp=False, qtype="A")
            if val is None:
                # UDP AAAA
                val, reason = dig_query(server, d, use_tcp=False, qtype="AAAA")
            if val is None:
                # TCP A
                val, reason = dig_query(server, d, use_tcp=True, qtype="A")
            if val is None:
                # TCP AAAA
                val, reason = dig_query(server, d, use_tcp=True, qtype="AAAA")

        if val is None and NSLOOKUP:
            srv = normalize_ipv6_scope_for_tool(server, tool="nslookup")
            val, reason = nslookup_query(srv, d)

        if val is None:
            # sistem resolver
            val, reason = system_resolver_query(d)

        if val is None and reason:
            diags.append(reason)
        lats.append(val)
    ok = [x for x in lats if x is not None]
    avg = round(sum(ok)/len(ok),2) if ok else None
    # en yaygın hata kodunu kısa bilgi olarak dönelim
    hint = max(set(diags), key=diags.count) if diags else None
    return avg, lats, hint

def main():
    os.environ["PYTHONUNBUFFERED"] = "1"
    servers = get_system_dns()
    print("=== DNS Resolver Latency Test (auto-detect) ===")
    print(f"Detected DNS servers: {', '.join(servers) if servers else '(none)'}")
    print(f"Domains: {', '.join(DOMAINS)}")
    print(f"(NO_ARTIFACTS={NO_ARTIFACTS}, timeout={QUERY_TIMEOUT_SEC}s per query)")
    print("="*70)

    n=1
    while True:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- Test #{n} @ {ts} ---")
        if servers:
            for srv in servers:
                avg, lst, hint = measure_server(srv, DOMAINS)
                hint_s = f"  [diag:{hint}]" if hint else ""
                if avg is None:
                    print(f"DNS {srv}: avg=N/A -> {lst}{hint_s}")
                else:
                    print(f"DNS {srv}: avg={avg:.2f} ms -> {lst}{hint_s}")
        else:
            # hiç server bulunamadı, sadece sistem resolver
            vals=[]; det=[]
            for d in DOMAINS:
                v, r = system_resolver_query(d)
                vals.append(v); det.append(v)
            oks=[x for x in vals if x is not None]
            avg = round(sum(oks)/len(oks),2) if oks else None
            print(f"System resolver: avg={avg if avg is not None else 'N/A'} -> {det}")
        n+=1
        time.sleep(5)

if __name__=="__main__":
    main()
