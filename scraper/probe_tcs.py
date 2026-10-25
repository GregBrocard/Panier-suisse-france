"""Sonde technique (test privé) : comment le radar TCS charge ses données. N'affiche aucun prix."""
import re
import requests
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
base = "https://benzin.tcs.ch"
r = requests.get(base + "/robots.txt", headers=UA, timeout=30)
print("robots.txt", r.status_code, r.text[:800])
r = requests.get(base + "/fr", headers=UA, timeout=30)
print("page", r.status_code, r.headers.get("server"), [h for h in r.headers if "cf-" in h.lower() or "captcha" in h.lower()])
scripts = re.findall(r'<script[^>]+src="([^"]+)"', r.text)
print("scripts", scripts)
for s in scripts:
    u = s if s.startswith("http") else base + s
    js = requests.get(u, headers=UA, timeout=60).text
    urls = sorted(set(re.findall(r'https?://[A-Za-z0-9./_-]+', js)))
    print("==", u, len(js))
    for x in urls:
        if any(k in x for k in ("api", "tcs", "benzin", "fuel", "price", "station")):
            print("   ", x)
    for m in sorted(set(re.findall(r'["\'](/api/[^"\']{0,80})["\']', js)))[:40]:
        print("   path", m)
