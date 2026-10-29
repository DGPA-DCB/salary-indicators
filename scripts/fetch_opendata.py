"""從政府資料開放平臺（data.gov.tw）取得資料集目錄及下載指定檔案。
由 GitHub Actions 執行（.github/workflows/fetch-opendata.yml），只使用平臺提供的資料集 API，
每月執行一次或手動執行，不逐頁擷取網站內容。
1. catalog：讀 opendata/catalog_ids.txt，取各資料集後設資料，寫入 opendata/catalog.json。
2. download：讀 opendata/resources.json（[{"name":"113_總預算案簡明表","url":"..."}]），
   下載檔案至 raw/<name>/，ZIP 自動解壓；內容未變則不改檔。結果記錄於 opendata/fetch_log.json。"""
import json, os, sys, time, re, hashlib, zipfile, io, urllib.request, urllib.parse, urllib.error, datetime, ssl

UA = {"User-Agent": "DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"}
API = "https://data.gov.tw/api/v2/rest/dataset/{}"
log = {"run": datetime.datetime.utcnow().isoformat() + "Z", "catalog": [], "download": []}

_CTX = {}
def _aia_context(host):
    """伺服器未附中繼憑證時，依憑證 AIA 欄位下載中繼憑證後再驗證（仍完整驗證至受信任根憑證，不關閉驗證）。"""
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding
    from cryptography.x509.oid import AuthorityInformationAccessOID as A, ExtensionOID as E
    extra = []
    cert = x509.load_pem_x509_certificate(ssl.get_server_certificate((host, 443)).encode())
    for _ in range(3):
        try:
            aia = cert.extensions.get_extension_for_oid(E.AUTHORITY_INFORMATION_ACCESS).value
        except x509.ExtensionNotFound:
            break
        urls = [d.access_location.value for d in aia if d.access_method == A.CA_ISSUERS]
        if not urls: break
        with urllib.request.urlopen(urllib.request.Request(urls[0], headers=UA), timeout=30) as r:
            b = r.read()
        try: cert = x509.load_der_x509_certificate(b)
        except Exception: cert = x509.load_pem_x509_certificate(b)
        extra.append(cert.public_bytes(Encoding.PEM).decode())
        if cert.issuer == cert.subject: break
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cadata="".join(extra))
    return ctx

def get(url, timeout=60):
    u = urllib.parse.urlsplit(url)
    url = urllib.parse.urlunsplit((u.scheme, u.netloc, urllib.parse.quote(u.path, safe="/%"), u.query, u.fragment))
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX.get(u.hostname)) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.URLError as e:
        if not isinstance(getattr(e, "reason", None), ssl.SSLCertVerificationError) or u.hostname in _CTX:
            raise
        _CTX[u.hostname] = _aia_context(u.hostname)
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX[u.hostname]) as r:
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

PAT_AUTO = re.compile(r"^(\d{3})年度中央政府(總決算|總預算案?)(?:[－-](預算表|簡明表|參考表))?$")
def auto_resources():
    """依 catalog.json 自動列出要下載的檔案：○年度中央政府總決算（各 XML）、總預算案－預算表/簡明表/參考表（ZIP）。"""
    out = []
    try: cat = json.load(open("opendata/catalog.json", encoding="utf-8"))
    except Exception: return out
    for i, v in cat.items():
        m = PAT_AUTO.match((v.get("title") or "").replace("　", "").strip())
        if not m: continue
        y, kind, sub = m.group(1), m.group(2), m.group(3)
        kind = "總預算案" if kind.startswith("總預算") else kind
        for f in v.get("files") or []:
            u = f.get("url") or ""
            if not u: continue
            stem = urllib.parse.unquote(u.split("?")[0].rsplit("/", 1)[-1]).rsplit(".", 1)[0]
            name = f"{y}_{kind}_{sub or stem}"
            if kind == "總決算" and not re.search(r"簡明|用途", stem): continue
            if name not in {o["name"] for o in out}: out.append({"name": name, "url": u})
    return out
NTA = {"D3-16F": "https://lgd.nta.gov.tw/newlgd/opendata/D3-16F.csv", "D3-17F": "https://lgd.nta.gov.tw/newlgd/opendata/D3-17F.csv"}
def nta_snapshot():
    """國庫署「各級政府1年以上公共債務明細表」實際數/預算數為每月覆寫之快照，依資料所屬年月留存歷史。"""
    os.makedirs("opendata/nta", exist_ok=True)
    for k, u in NTA.items():
        try:
            st, ct, b = get(u, 60); txt = b.decode("utf-8-sig", errors="replace")
            first = txt.splitlines()[1].split(",") if len(txt.splitlines()) > 1 else []
            ym = first[0] + (first[1].zfill(2) if k == "D3-16F" and len(first) > 1 else "") if first else datetime.date.today().strftime("%y%m")
            fn = f"opendata/nta/{k}_{ym}.csv"
            if not os.path.exists(fn): open(fn, "w", encoding="utf-8").write(txt)
            log["download"].append({"name": f"nta/{k}", "ok": True, "period": ym})
        except Exception as e:
            log["download"].append({"name": f"nta/{k}", "ok": False, "error": repr(e)[:200]})
def download():
    res = json.load(open("opendata/resources.json", encoding="utf-8"))
    seen = {r["name"] for r in res}
    res += [r for r in auto_resources() if r["name"] not in seen]
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
                ext = ".pdf" if b[:4] == b"%PDF" else (os.path.splitext(url.split("?")[0])[1] or ".bin")
                open(os.path.join(d, "data" + ext), "wb").write(b)
            open(hp, "w").write(h)
            log["download"].append({"name": name, "ok": True, "changed": True, "bytes": len(b), "type": ct})
        except Exception as e:
            log["download"].append({"name": name, "ok": False, "error": repr(e)[:300]})
        time.sleep(2)

if __name__ == "__main__":
    catalog(); download(); nta_snapshot()
    json.dump(log, open("opendata/fetch_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(log, ensure_ascii=False)[:2000])
