"""審計部「總決算審核報告」查詢平台探勘／下載（GitHub Actions）。遵守 robots.txt。
輸出 opendata/audit_central/：robots.txt、links.json、log.json；若 targets.json 指定年度，下載報告並擷取含「歲入歲出」審定數之頁面文字。"""
import json, os, re, time, subprocess, unicodedata, urllib.request, urllib.robotparser
from playwright.sync_api import sync_playwright
BASE = "https://auditreport.audit.gov.tw/"
OUT = "opendata/audit_central"; os.makedirs(OUT, exist_ok=True)
UA = "DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
log = {"run": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}
def step(**k): log["steps"].append(k); print(json.dumps(k, ensure_ascii=False)[:500])
rp = urllib.robotparser.RobotFileParser()
try:
    txt = urllib.request.urlopen(urllib.request.Request(BASE + "robots.txt", headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "replace")
    open(f"{OUT}/robots.txt", "w").write(txt); rp.parse(txt.splitlines()); step(robots="ok", text=txt[:300])
except Exception as e:
    step(robots="error", error=repr(e)[:200]); rp = None
def allowed(u): return True if rp is None else rp.can_fetch(UA, u)
N = lambda s: unicodedata.normalize("NFKC", s or "")
links = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(user_agent=UA)
    def grab(url, label):
        if not allowed(url): step(page=label, url=url, skipped="robots disallow"); return []
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=90000); pg.wait_for_timeout(8000)
        except Exception as e:
            step(page=label, url=url, error=repr(e)[:200]); return []
        items = pg.eval_on_selector_all("a,option,button", "els=>els.map(a=>({t:(a.innerText||a.title||a.value||'').trim(),h:a.href||'',tag:a.tagName}))")
        step(page=label, url=pg.url, title=pg.title(), n=len(items))
        open(f"{OUT}/{label.replace(':','_')[:30]}.html", "w").write(pg.content()[:300000])
        return items
    home = grab(BASE, "home"); links += [dict(x, src="home") for x in home]
    seen = {BASE}
    for x in home:
        t = N(x["t"])
        if x["h"].startswith("http") and "auditreport" in x["h"] and x["h"] not in seen and re.search(r"(中央政府|總決算|審核報告|102|114)", t):
            seen.add(x["h"]); sub = grab(x["h"], "L1:" + t[:15]); links += [dict(y, src=t[:15]) for y in sub]
            if len(seen) > 12: break
    b.close()
json.dump(links, open(f"{OUT}/links.json", "w"), ensure_ascii=False, indent=0)
json.dump(log, open(f"{OUT}/log.json", "w"), ensure_ascii=False, indent=1)
