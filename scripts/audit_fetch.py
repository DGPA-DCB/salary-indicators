"""審計部年報探勘／下載（GitHub Actions 執行）。
步驟：1) 讀 robots.txt 並遵守；2) 以 Playwright 開啟首頁，沿「審計報告」→「財務審核結果年報」找出年報清單；
3) 找出「直轄市及縣市地方決算審核結果年報」「鄉鎮縣轄市財務審核結果年報」各年度 PDF 連結；
4) 下載尚未處理之年度，以 pdftotext 擷取含「人事費負擔」的頁面文字存檔（不存整份 PDF）。
所有紀錄寫入 opendata/audit/。"""
import json, os, re, sys, time, subprocess, urllib.parse, urllib.robotparser, unicodedata
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

    # ---- 下載指定年度年報並擷取「人事費負擔」相關頁 ----
    try: targets = json.load(open(f"{OUT}/targets.json", encoding="utf-8"))
    except Exception: targets = []
    allL = links
    for t in targets:
        y, kind = t["year"], t["kind"]; d = f"{OUT}/{y}_{kind[:6]}"; os.makedirs(d, exist_ok=True)
        if os.path.exists(f"{d}/excerpt.txt"): step(target=y, skipped="already done"); continue
        det = [x for x in allL if re.search(rf"{y}年度{kind}", unicodedata.normalize("NFKC", x["t"]))]
        if not det: step(target=y, error="detail page not found"); continue
        items = grab(det[0]["h"], f"detail:{y}")
        pdfs = [x for x in items if x["t"].lower().endswith(".pdf") or ".pdf" in x["t"].lower()]
        step(target=y, detail=det[0]["h"], files=[x["t"] for x in items if "downloadfile" in x["h"]][:10])
        if not pdfs: step(target=y, error="no pdf link"); continue
        try:
            r = pg.request.get(pdfs[0]["h"], timeout=180000)
            body = r.body(); open("/tmp/r.pdf", "wb").write(body)
            step(target=y, pdf=pdfs[0]["t"], bytes=len(body), status=r.status)
            n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", "/tmp/r.pdf"], capture_output=True, text=True).stdout).group(1))
            hit = []
            for i in range(1, n + 1):
                txt = subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), "/tmp/r.pdf", "-"], capture_output=True, text=True).stdout
                if re.search(r"人事費負擔", txt): hit.append((i, txt))
            pages = sorted({p for i, _ in hit for p in (i, i + 1) if p <= n})
            with open(f"{d}/excerpt.txt", "w", encoding="utf-8") as f:
                for i in pages:
                    f.write(f"\n===== PDF第{i}頁 =====\n")
                    f.write(subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), "/tmp/r.pdf", "-"], capture_output=True, text=True).stdout)
            sel = [p for p in pages][:12]
            parts = []
            for i in sel:
                subprocess.run(["pdfseparate", "-f", str(i), "-l", str(i), "/tmp/r.pdf", f"/tmp/pg-{i}.pdf"]); parts.append(f"/tmp/pg-{i}.pdf")
            if parts: subprocess.run(["pdfunite", *parts, f"{d}/pages.pdf"])
            json.dump({"year": y, "kind": kind, "source": det[0]["h"], "pdf": pdfs[0]["h"], "pdf_name": pdfs[0]["t"], "total_pages": n, "keyword_pages": [i for i, _ in hit], "saved_pages": sel}, open(f"{d}/meta.json", "w"), ensure_ascii=False, indent=1)
            step(target=y, keyword_pages=[i for i, _ in hit])
        except Exception as e:
            step(target=y, error=repr(e)[:300])
    b.close()
json.dump(links, open(f"{OUT}/links.json", "w"), ensure_ascii=False, indent=0)
hits = [x for x in links if re.search(r"(地方決算審核結果年報|鄉鎮縣轄市財務審核結果年報)", unicodedata.normalize("NFKC", x["t"]))]
json.dump(hits, open(f"{OUT}/report_links.json", "w"), ensure_ascii=False, indent=1)
step(total_links=len(links), report_links=len(hits))
json.dump(log, open(f"{OUT}/log.json", "w"), ensure_ascii=False, indent=1)
