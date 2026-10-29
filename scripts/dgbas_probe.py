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
    h=urllib.parse.urlsplit(u).hostname
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
for u in ["https://www.stat.gov.tw/cl.aspx?n=3680","https://www.stat.gov.tw/cp.aspx?n=2679","https://www.stat.gov.tw/News.aspx?n=3602","https://www.dgbas.gov.tw/News.aspx?n=3602","https://www.dgbas.gov.tw/cl.aspx?n=3680"]:
    b=get(u)
    if b:
        t=b.decode("utf-8","replace"); links=re.findall(r'href="([^"]+)"[^>]*>([^<]{2,80})<',t)
        step(url=u,bytes=len(b),links=[(x.strip(),h[:100]) for h,x in links if re.search(r"預測|展望|重要經濟指標|薪資|xls|ods|csv|新聞稿",x+h)][:30])
