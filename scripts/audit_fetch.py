"""審計部年報探勘／下載（GitHub Actions 執行）。
步驟：1) 讀 robots.txt 並遵守；2) 以 Playwright 開啟首頁，沿「審計報告」→「財務審核結果年報」找出年報清單；
3) 找出「直轄市及縣市地方決算審核結果年報」「鄉鎮縣轄市財務審核結果年報」各年度 PDF 連結；
4) 下載尚未處理之年度，以 pdftotext 擷取含「人事費負擔」的頁面文字存檔（不存整份 PDF）。
所有紀錄寫入 opendata/audit/。"""
import json, os, re, sys, time, subprocess, urllib.parse, urllib.robotparser
from playwright.sync_api import sync_playwright
BASE = "https://www.audit.gov.tw/"
OUT = "opendata/audit"; os.makedirs(OUT, exist_ok=True)
UA = "DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
log = {"run": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}
def step(**k): log["steps"].append(k); print(json.dumps(k, ensure_ascii=False)[:500])

rp = urllib.robotparser.RobotFileParser()
try:
    import urllib.request
    txt = urllib.request.urlopen(urllib.request.Request(BASE + "robots.txt", headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "replace")
    open(f"{OUT}/robots.txt", "w").write(txt); rp.parse(txt.splitlines()); step(robots="ok", length=len(txt))
except Exception as e:
    step(robots="error", error=repr(e)[:200]); rp = None
def allowed(u): return True if rp is None else rp.can_fetch(UA, u)

links = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(user_agent=UA)
    def grab(url, label):
        if not allowed(url): step(page=label, url=url, skipped="robots disallow"); return []
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=90000); pg.wait_for_timeout(8000)
        except Exception as e:
            step(page=label, url=url, error=repr(e)[:200]); return []
        items = pg.eval_on_selector_all("a", "els=>els.map(a=>({t:(a.innerText||a.title||'').trim(),h:a.href}))")
        step(page=label, url=pg.url, title=pg.title(), links=len(items))
        return items
    home = grab(BASE, "home"); links += [dict(x, src="home") for x in home]
    # 找「財務審核結果年報」
    cand = [x for x in home if "財務審核結果年報" in x["t"]] or [x for x in home if "審計報告" in x["t"]]
    seen = set()
    for c in cand[:5]:
        if c["h"] in seen or not c["h"].startswith("http"): continue
        seen.add(c["h"]); sub = grab(c["h"], "L1:" + c["t"][:20]); links += [dict(x, src=c["t"][:20]) for x in sub]
        for s in [x for x in sub if "財務審核結果年報" in x["t"] or "決算審核結果年報" in x["t"]][:5]:
            if s["h"] in seen or not s["h"].startswith("http"): continue
            seen.add(s["h"]); sub2 = grab(s["h"], "L2:" + s["t"][:20]); links += [dict(x, src=s["t"][:20]) for x in sub2]
    b.close()
json.dump(links, open(f"{OUT}/links.json", "w"), ensure_ascii=False, indent=0)
hits = [x for x in links if re.search(r"(地方決算審核結果年報|鄉鎮縣轄市財務審核結果年報)", x["t"])]
json.dump(hits, open(f"{OUT}/report_links.json", "w"), ensure_ascii=False, indent=1)
step(total_links=len(links), report_links=len(hits))
json.dump(log, open(f"{OUT}/log.json", "w"), ensure_ascii=False, indent=1)
