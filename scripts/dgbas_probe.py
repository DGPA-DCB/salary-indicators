"""主計總處統計資訊網（stat.gov.tw）探勘：國民所得預測、薪資統計電子檔是否可自動取得。遵守 robots.txt。"""
import json, os, re, time, urllib.request, urllib.parse, urllib.error, urllib.robotparser, ssl
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
        with urllib.request.urlopen(urllib.request.Request(urls[0], headers={"User-Agent": UA}), timeout=30) as r:
            b = r.read()
        try: cert = x509.load_der_x509_certificate(b)
        except Exception: cert = x509.load_pem_x509_certificate(b)
        extra.append(cert.public_bytes(Encoding.PEM).decode())
        if cert.issuer == cert.subject: break
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cadata="".join(extra))
    return ctx


OUT="opendata/dgbas"; os.makedirs(OUT,exist_ok=True)
UA="DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
log=[]
def step(**k):
    log.append(k); print(json.dumps(k,ensure_ascii=False)[:700]); json.dump(log,open(f"{OUT}/probe.json","w"),ensure_ascii=False,indent=1)
rps={}
def allowed(u):
    host=re.match(r"https?://[^/]+/",u).group(0)
    if host not in rps:
        rp=urllib.robotparser.RobotFileParser()
        try:
            t=raw(host+"robots.txt",30).decode("utf-8","replace"); rp.parse(t.splitlines()); step(robots=host,text=t[:400])
        except Exception as e: rp=None; step(robots=host,error=repr(e)[:100])
        rps[host]=rp
    return True if rps[host] is None else rps[host].can_fetch(UA,u)
def raw(u,timeout=90):
    sp=urllib.parse.urlsplit(u); u=urllib.parse.urlunsplit((sp.scheme,sp.netloc,urllib.parse.quote(sp.path,safe="/%"),sp.query,sp.fragment))
    h=sp.hostname
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"*/*"}),timeout=timeout,context=_CTX.get(h)) as r: return r.read()
    except urllib.error.URLError as e:
        if isinstance(getattr(e,"reason",None),ssl.SSLCertVerificationError) and h not in _CTX:
            _CTX[h]=_aia_context(h)
            with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"*/*"}),timeout=timeout,context=_CTX[h]) as r: return r.read()
        raise
def get(u,timeout=90):
    if not allowed(u): step(url=u,skipped="robots disallow"); return None
    try: return raw(u,timeout)
    except Exception as e: step(url=u[:120],error=repr(e)[:200]); return None

import subprocess
# 1. 薪資新聞稿內容頁 + 附件
b=get("https://www.dgbas.gov.tw/News_Content.aspx?n=3602&s=236702")
if b:
    t=b.decode("utf-8","replace")
    att=re.findall(r'href="([^"]+)"[^>]*>([^<]*(?:pdf|xls|ods|csv|xlsx|附表|附件)[^<]*)<',t,re.I)
    step(page="薪資新聞稿115年7月",bytes=len(b),attachments=[(x.strip(),h[:120]) for h,x in att][:15])
    # 文字中的累計
    m=re.findall(r"[^。]*累計[^。]*。",re.sub(r"<[^>]+>"," ",t))
    step(page="薪資新聞稿累計句",sentences=[x.strip()[:160] for x in m][:6])
    for h,x in att[:2]:
        if re.search(r"pdf|xls|ods|csv",h+x,re.I):
            u=h if h.startswith("http") else "https://www.dgbas.gov.tw/"+h.lstrip("/")
            f=get(u)
            if f:
                kind="PDF" if f[:4]==b"%PDF" else ("ZIP/XLSX" if f[:2]==b"PK" else f[:30].decode("utf-8","replace"))
                step(attachment=x.strip()[:40],url=u[:120],bytes=len(f),kind=kind)
                if f[:2]==b"PK":
                    open("/tmp/t.ods","wb").write(f)
                    import zipfile; z=zipfile.ZipFile("/tmp/t.ods"); xml=z.read("content.xml").decode("utf-8","replace")
                    txt=re.sub(r"<[^>]+>","|",xml); txt=re.sub(r"\|+","|",txt)
                    step(attachment=x.strip()[:40],ods_text=txt[:2500])
                if f[:4]==b"%PDF":
                    open("/tmp/a.pdf","wb").write(f); tx=subprocess.run(["pdftotext","-layout","/tmp/a.pdf","-"],capture_output=True,text=True).stdout
                    hit=[l for l in tx.splitlines() if "累計" in l or "經常性薪資平均數" in l]
                    step(attachment=x.strip()[:40],lines=hit[:8])

# 2. 國民所得新聞稿：找最新一篇與其附件
for lst in ["https://www.dgbas.gov.tw/News.aspx?n=3602&sms=10980","https://www.stat.gov.tw/News.aspx?n=2679&sms=11024"]:
    b=get(lst)
    if not b: continue
    t=b.decode("utf-8","replace"); links=re.findall(r'href="(News_Content[^"]+)"[^>]*>([^<]{5,160})<',t)
    na=[(x.strip(),h) for h,x in links if re.search(r"國民所得|經濟成長|經濟預測|概估",x)]
    step(page=lst,national_income=na[:6])
    if na:
        u="https://www.dgbas.gov.tw/"+na[0][1] if "dgbas" in lst else "https://www.stat.gov.tw/"+na[0][1]
        b2=get(u)
        if b2:
            t2=b2.decode("utf-8","replace"); att=re.findall(r'href="([^"]+)"[^>]*>([^<]*)<',t2)
            att=[(x.strip(),h) for h,x in att if re.search(r"pdf|ods|xls",h,re.I)]
            step(page=na[0][0][:50],url=u,attachments=[(x[:30],h[:140]) for x,h in att][:20])
            for x,h in att:
                if re.search(r"ods",h,re.I) and re.search(r"重要|指標|預測|表",x+h):
                    f=get(h if h.startswith("http") else "https://www.dgbas.gov.tw/"+h.lstrip("/"))
                    if f and f[:2]==b"PK":
                        open("/tmp/n.ods","wb").write(f); import zipfile; z=zipfile.ZipFile("/tmp/n.ods"); xml=z.read("content.xml").decode("utf-8","replace")
                        txt=re.sub(r"<[^>]+>","|",xml); txt=re.sub(r"\|+","|",txt); step(ods=x[:40],text=txt[:2500]); break
        break
