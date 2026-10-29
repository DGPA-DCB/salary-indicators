"""中央政府總決算審核報告：取歲入、歲出審定數及餘絀（GitHub Actions）。
- 104年起：審計部「總決算審核報告查詢平臺」(auditreport.audit.gov.tw) 章節頁文字。
- 103年以前：審計部網站「103年以前總決算」(p/412-1000-97.php) 之報告 PDF，擷取含「歲入歲出」審定餘絀之頁面。
遵守 robots.txt；遇防機器人阻擋即停止，不繞過。輸出 opendata/audit_central/<年>/。"""
import json, os, re, time, subprocess, unicodedata, urllib.request, urllib.robotparser
from playwright.sync_api import sync_playwright
OUT = "opendata/audit_central"; os.makedirs(OUT, exist_ok=True)
UA = "DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
N = lambda s: unicodedata.normalize("NFKC", s or "")
log = {"run": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": []}
def step(**k): log["steps"].append(k); print(json.dumps(k, ensure_ascii=False)[:600])
rps = {}
def allowed(u):
    host = re.match(r"https?://[^/]+/", u).group(0)
    if host not in rps:
        rp = urllib.robotparser.RobotFileParser()
        try:
            t = urllib.request.urlopen(urllib.request.Request(host + "robots.txt", headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "replace"); rp.parse(t.splitlines())
        except Exception: rp = None
        rps[host] = rp
    return True if rps[host] is None else rps[host].can_fetch(UA, u)
KEY = re.compile(r"(歲入歲出相抵|賸餘|差短)")
targets = json.load(open(f"{OUT}/targets.json", encoding="utf-8"))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(user_agent=UA)
    def go(url, label):
        if not allowed(url): step(page=label, skipped="robots disallow"); return None
        try: pg.goto(url, wait_until="domcontentloaded", timeout=90000); pg.wait_for_timeout(6000)
        except Exception as e: step(page=label, error=repr(e)[:200]); return None
        html = pg.content()
        if "Request unsuccessful" in html: step(page=label, blocked="bot protection; stop"); return None
        return pg.eval_on_selector_all("a", "els=>els.map(a=>({t:(a.innerText||a.title||'').trim(),h:a.href||''}))")
    for t in targets:
        y = t["year"]; d = f"{OUT}/{y}"; os.makedirs(d, exist_ok=True)
        if os.path.exists(f"{d}/excerpt.txt"): step(target=y, skipped="done"); continue
        out = []
        if t["mode"] == "platform":
            home = go("https://auditreport.audit.gov.tw/", "platform") or []
            books = [x for x in home if re.search(rf"{y}年度中央政府總決算審核報告_第1冊", N(x["t"]))]
            if not books: step(target=y, error="book not found"); continue
            ch = go(books[0]["h"], f"book{y}") or []
            json.dump(ch, open(f"{d}/chapters.json", "w"), ensure_ascii=False, indent=0)
            cand = [x for x in ch if "/Book/" in x["h"] and re.search(r"(總說明|歲入歲出|審核概述|決算審定|綜合意見|收支)", N(x["t"]))][:12]
            step(target=y, chapters=len(ch), candidates=[x["t"][:30] for x in cand])
            for c in cand:
                if go(c["h"], "chap") is None: continue
                txt = pg.inner_text("body")
                paras = [s for s in re.split(r"\n+", txt) if KEY.search(s) and re.search(r"\d", s)]
                if paras: out.append(f"===== {c['t'][:40]} | {c['h']} =====\n" + "\n".join(paras[:30]))
        else:
            lst = go("https://www.audit.gov.tw/p/412-1000-97.php?Lang=zh-tw", "old-list") or []
            det = [x for x in lst if re.search(rf"{y}年度中央政府總決算審核報告", N(x["t"]))]
            step(target=y, found=[x["t"][:40] for x in det][:5])
            if not det: step(target=y, error="detail not found"); continue
            items = go(det[0]["h"], f"detail{y}") or []
            pdfs = [x for x in items if ".pdf" in x["t"].lower()]
            step(target=y, files=[x["t"][:50] for x in items if "downloadfile" in x["h"]][:15])
            for f in pdfs[:4]:
                r = pg.request.get(f["h"], timeout=180000); body = r.body()
                if body[:4] != b"%PDF": step(target=y, file=f["t"], error="not pdf"); continue
                open("/tmp/c.pdf", "wb").write(body)
                n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", "/tmp/c.pdf"], capture_output=True, text=True).stdout).group(1))
                hits = 0
                for i in range(1, min(n, 80) + 1):
                    tx = subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), "/tmp/c.pdf", "-"], capture_output=True, text=True).stdout
                    if re.search(r"歲入歲出", tx) and KEY.search(tx):
                        out.append(f"===== {f['t'][:40]} PDF第{i}頁 =====\n{tx}"); hits += 1
                    if hits >= 4: break
                step(target=y, file=f["t"][:40], pages=n, hits=hits)
                if hits: break
        open(f"{d}/excerpt.txt", "w", encoding="utf-8").write("\n\n".join(out) or "（未找到相關段落）")
        step(target=y, excerpts=len(out))
    b.close()
json.dump(log, open(f"{OUT}/log.json", "w"), ensure_ascii=False, indent=1)
