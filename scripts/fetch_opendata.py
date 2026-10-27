"""從政府資料開放平臺（data.gov.tw）取得資料集目錄及下載指定檔案。
由 GitHub Actions 執行（.github/workflows/fetch-opendata.yml），只使用平臺提供的資料集 API，
每月執行一次或手動執行，不逐頁擷取網站內容。
1. catalog：讀 opendata/catalog_ids.txt，取各資料集後設資料，寫入 opendata/catalog.json。
2. download：讀 opendata/resources.json（[{"name":"113_總預算案簡明表","url":"..."}]），
   下載檔案至 raw/<name>/，ZIP 自動解壓；內容未變則不改檔。結果記錄於 opendata/fetch_log.json。"""
import json, os, sys, time, hashlib, zipfile, io, urllib.request, datetime

UA = {"User-Agent": "DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"}
API = "https://data.gov.tw/api/v2/rest/dataset/{}"
log = {"run": datetime.datetime.utcnow().isoformat() + "Z", "catalog": [], "download": []}

def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()

def catalog():
    ids = [l.strip() for l in open("opendata/catalog_ids.txt", encoding="utf-8") if l.strip() and not l.startswith("#")]
    out = {}
    for i in ids:
        try:
            st, ct, b = get(API.format(i))
            d = json.loads(b.decode("utf-8"))
            r = d.get("result", d)
            out[i] = {
                "title": r.get("title"), "agency": r.get("publisher") or r.get("organization"),
                "description": (r.get("description") or "")[:500],
                "updated": r.get("modifiedDate") or r.get("updateDate"),
                "files": [{"desc": x.get("resourceDescription"), "format": x.get("resourceFormat"),
                           "url": x.get("resourceDownloadUrl"), "encoding": x.get("resourceCharacterEncoding")}
                          for x in (r.get("distribution") or [])],
            }
            log["catalog"].append({"id": i, "ok": True})
        except Exception as e:
            out[i] = {"error": repr(e)[:300]}
            log["catalog"].append({"id": i, "ok": False, "error": repr(e)[:300]})
        time.sleep(1)
    json.dump(out, open("opendata/catalog.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def download():
    res = json.load(open("opendata/resources.json", encoding="utf-8"))
    for it in res:
        name, url = it["name"], it["url"]
        d = os.path.join("raw", name); os.makedirs(d, exist_ok=True)
        try:
            st, ct, b = get(url, 120)
            h = hashlib.sha256(b).hexdigest()
            hp = os.path.join(d, ".sha256")
            if os.path.exists(hp) and open(hp).read().strip() == h:
                log["download"].append({"name": name, "ok": True, "changed": False}); continue
            if b[:2] == b"PK":
                with zipfile.ZipFile(io.BytesIO(b)) as z:
                    for m in z.infolist():
                        if m.is_dir(): continue
                        fn = m.filename
                        try: fn = m.filename.encode("cp437").decode("big5")
                        except Exception: pass
                        safe = os.path.basename(fn.replace("\\", "/"))
                        if not safe: continue
                        open(os.path.join(d, safe), "wb").write(z.read(m))
            else:
                ext = os.path.splitext(url.split("?")[0])[1] or ".bin"
                open(os.path.join(d, "data" + ext), "wb").write(b)
            open(hp, "w").write(h)
            log["download"].append({"name": name, "ok": True, "changed": True, "bytes": len(b), "type": ct})
        except Exception as e:
            log["download"].append({"name": name, "ok": False, "error": repr(e)[:300]})
        time.sleep(2)

if __name__ == "__main__":
    catalog(); download()
    json.dump(log, open("opendata/fetch_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(log, ensure_ascii=False)[:2000])
