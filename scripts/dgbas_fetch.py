"""主計總處新聞稿附表自動下載（GitHub Actions，每月）：
A. 薪資及生產力統計新聞稿 → 表1.ods：年度平均（J/L全年值）、本年1至○月累計（J/L累計平均、K/M年增率）。
B. 國民所得統計新聞稿（含經濟預測） → t1-1.ods 重要經濟指標表：當年及次年經濟成長率、CPI、每人GDP(美元/元)預測。
遵守 robots.txt（主計總處僅封鎖特定爬蟲與兩類網址）。輸出 opendata/dgbas/wages.json、forecast.json。"""
import json, os, re, time, zipfile, io, urllib.request, urllib.parse, urllib.error, urllib.robotparser, ssl
OUT="opendata/dgbas"; os.makedirs(OUT,exist_ok=True)
UA="DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
exec(open("scripts/dgbas_probe.py").read().split("rps={}")[0].split("log=[]")[1].replace("def step(**k):","def _s(**k):") if False else "")
# --- 共用：AIA 中繼憑證 + 中文網址編碼 ---
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import AuthorityInformationAccessOID as A, ExtensionOID as E
_CTX={}
def _aia(host):
    cert=x509.load_pem_x509_certificate(ssl.get_server_certificate((host,443)).encode()); extra=[]
    for _ in range(3):
        try: aia=cert.extensions.get_extension_for_oid(E.AUTHORITY_INFORMATION_ACCESS).value
        except x509.ExtensionNotFound: break
        urls=[d.access_location.value for d in aia if d.access_method==A.CA_ISSUERS]
        if not urls: break
        b=urllib.request.urlopen(urllib.request.Request(urls[0],headers={"User-Agent":UA}),timeout=30).read()
        try: cert=x509.load_der_x509_certificate(b)
        except Exception: cert=x509.load_pem_x509_certificate(b)
        extra.append(cert.public_bytes(Encoding.PEM).decode())
        if cert.issuer==cert.subject: break
    ctx=ssl.create_default_context(); ctx.load_verify_locations(cadata="".join(extra)); return ctx
def raw(u,timeout=120):
    sp=urllib.parse.urlsplit(u); u=urllib.parse.urlunsplit((sp.scheme,sp.netloc,urllib.parse.quote(sp.path,safe="/%"),sp.query,sp.fragment)); h=sp.hostname
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"*/*"})
    try:
        with urllib.request.urlopen(req,timeout=timeout,context=_CTX.get(h)) as r: return r.read()
    except urllib.error.URLError as e:
        if isinstance(getattr(e,"reason",None),ssl.SSLCertVerificationError) and h not in _CTX:
            _CTX[h]=_aia(h)
            with urllib.request.urlopen(req,timeout=timeout,context=_CTX[h]) as r: return r.read()
        raise
rps={}
def allowed(u):
    m=re.match(r"https?://[^/]+/",u)
    if not m: raise RuntimeError("not absolute url: "+u)
    host=m.group(0)
    if host not in rps:
        rp=urllib.robotparser.RobotFileParser()
        try: rp.parse(raw(host+"robots.txt",30).decode("utf-8","replace").splitlines())
        except Exception: rp=None
        rps[host]=rp
    return True if rps[host] is None else rps[host].can_fetch(UA,u)
def get(u):
    if not allowed(u): raise RuntimeError("robots disallow: "+u)
    return raw(u)
def ods_rows(b):
    z=zipfile.ZipFile(io.BytesIO(b)); xml=z.read("content.xml").decode("utf-8","replace")
    rows=[]
    for r in re.findall(r"<table:table-row[^>]*>(.*?)</table:table-row>",xml,re.S):
        cells=[]
        for m in re.finditer(r"<table:table-cell([^>]*)>(.*?)</table:table-cell>|<table:table-cell([^>]*)/>",r,re.S):
            attrs=m.group(1) or m.group(3) or ""; inner=m.group(2) or ""
            rep=int(re.search(r'number-columns-repeated="(\d+)"',attrs).group(1)) if 'number-columns-repeated' in attrs else 1
            txt=re.sub(r"<[^>]+>","",inner).strip()
            cells+=[txt]*min(rep,50)
        rows.append(cells)
    return rows
def num(s):
    s=str(s).replace(" ","").replace(",","").replace("Ⓟ","").replace("Ⓡ","").replace("ｒ","").replace("p","")
    try: return float(s)
    except: return None
log={"run":time.strftime("%Y-%m-%d"),"wages":{},"forecast":{}}
# ---------- A. 薪資 ----------
try:
    lst=get("https://www.dgbas.gov.tw/News.aspx?n=3602&sms=10980").decode("utf-8","replace")
    items=[(h,t) for h,t in re.findall(r'href="(News_Content\.aspx\?n=3602&(?:amp;)?s=\d+)"[^>]*>([^<]{5,160})<',lst) if re.search(r"\d{3}年\d{1,2}月.*工業及服務業.*薪資",t)]
    if not items: raise RuntimeError("找不到薪資新聞稿")
    h,title=items[0]; url="https://www.dgbas.gov.tw/"+h.replace("&amp;","&")
    page=get(url).decode("utf-8","replace")
    ods=[x for x in re.findall(r'href="([^"]+/表1\.ods)"',page)]
    if not ods: raise RuntimeError("找不到表1.ods")
    rows=ods_rows(get(ods[0]))
    W={"source":url,"title":title.strip(),"ods":ods[0],"annual":{},"ytd":None}
    cur=None; HEAD=None
    for r in rows:
        cells=[c for c in r if c!=""]
        if len(cells)<8: continue
        j=" ".join(cells[:5])
        m=re.match(r"(\d{3})\s*年平均",j.replace(" ",""))
        if m or (re.match(r"\d{3}",cells[0]) and "年平均" in j):
            y=int(re.search(r"(\d{3})",j).group(1)); nums=[num(c) for c in cells if num(c) is not None]
            # 欄序：人數,工業,服務業,進入,率,退出,率,總工時,加班,年增,經常性薪資,年增率,加班費,年增率
            if len(nums)>=14: W["annual"][y]={"regular":nums[-4],"regular_yoy":nums[-3]}
        m2=re.search(r"(\d{3})\s*年\s*1\s*至\s*(\d{1,2})\s*月",j.replace("|"," "))
        if m2:
            nums=[num(c) for c in cells if num(c) is not None]
            if len(nums)>=14: W["ytd"]={"year":int(m2.group(1)),"to_month":int(m2.group(2)),"regular":nums[-4],"regular_yoy":nums[-3]}
    log["wages"]=W
except Exception as e: log["wages"]={"error":repr(e)[:300]}
# 總薪資累計平均：表2「○年累計」列÷月數；年增率以上年同期各月加總比較
try:
    if "ods" in log["wages"] and log["wages"].get("ytd"):
        y=log["wages"]["ytd"]["year"]; m=log["wages"]["ytd"]["to_month"]
        rows=ods_rows(get(log["wages"]["ods"].rsplit("/",1)[0]+"/表2.ods"))
        cur=None; months={}; cum={}
        for r in rows:
            c=[x for x in r if x!=""]
            if not c: continue
            mm=re.match(r"(\d{3})年累計",c[0].replace(" ",""))
            if mm: cur=int(mm.group(1)); cum[cur]=num(c[1]); continue
            mm=re.match(r"(\d{1,2})月$",c[0].replace(" ",""))
            if mm and cur: months[(cur,int(mm.group(1)))]=num(c[1])
        prev=[months.get((y-1,i)) for i in range(1,m+1)]
        if cum.get(y) and all(prev):
            log["wages"]["ytd_total"]={"year":y,"to_month":m,"cum":cum[y],"avg":round(cum[y]/m),"yoy":round((cum[y]/sum(prev)-1)*100,2),"prev_cum":sum(prev)}
        log["wages"]["annual_total"]={yy:round(v/12) for yy,v in cum.items() if yy<y}
except Exception as e: log["wages"]["ytd_total_error"]=repr(e)[:200]
try:
  if False:
    if "ods" in log["wages"]:
        base=log["wages"]["ods"].rsplit("/",1)[0]
        for t in ["表2.ods","表3.ods","表4.ods"]:
            rows=ods_rows(get(base+"/"+t)); flat="|".join("|".join(r) for r in rows[:6])
            if "總薪資" in flat and ("累計" in flat or "1至" in "|".join("|".join(r) for r in rows)):
                for r in rows:
                    j="".join(r)
                    m2=re.search(r"(\d{3})年1至(\d{1,2})月",j)
                    if m2:
                        nums=[num(c) for c in r if num(c) is not None]
                        log["wages"]["ytd_total"]={"table":t,"year":int(m2.group(1)),"to_month":int(m2.group(2)),"nums":nums[:12]}
                        break
                if "ytd_total" in log["wages"]: break
except Exception as e: log["wages"]["ytd_total_error"]=repr(e)[:200]
# ---------- B. 國民所得預測 ----------
try:
    lst=get("https://www.dgbas.gov.tw/News.aspx?n=3602&sms=10980").decode("utf-8","replace")
    items=re.findall(r'href="(News_Content\.aspx\?n=3602&(?:amp;)?s=\d+)"[^>]*>([^<]*(?:預測|經濟成長率)[^<]*)<',lst)
    items=[(h,t) for h,t in items if "預測" in t] or items
    if not items: raise RuntimeError("找不到國民所得新聞稿")
    h,title=items[0]; url="https://www.dgbas.gov.tw/"+h.replace("&amp;","&")
    page=get(url).decode("utf-8","replace")
    ods=re.findall(r'href="([^"]+/t1-1\.ods)"',page)
    F={"source":url,"title":title.strip(),"growth":{}}
    if ods:
        for r in ods_rows(get(ods[0])):
            c=[x for x in r if x!=""]
            mm=re.match(r"(\d{3})年(\(f\)|\(p\)|\(r\))?$",c[0].replace(" ","")) if c else None
            if mm and len(c)>=6 and num(c[5]) is not None: F["growth"][int(mm.group(1))]={"v":num(c[5]),"flag":(mm.group(2) or "").strip("()")}
    pdf=re.findall(r'href="([^"]+/news\d+\.pdf)"',page)
    if pdf:
        import subprocess,tempfile
        fn=tempfile.mktemp(suffix=".pdf"); open(fn,"wb").write(get(pdf[0]))
        t=subprocess.run(["pdftotext","-layout",fn,"-"],capture_output=True,text=True).stdout
        F["pdf"]=pdf[0]
        # 文字摘要：預測115年…每人GDP 4萬5,332美元，CPI上漲2.07％
        for mm in re.finditer(r"(\d{3})年(?:經濟成長|全年經濟成長率)\s*([\d.]+)％[^。]*?每人GDP\s*([\d萬,]+)美元[^。]*?CPI上漲\s*([\d.]+)％",t.replace("\n","")):
            yy=int(mm.group(1)); usd=mm.group(3).replace(",","")
            usd=int(usd.split("萬")[0])*10000+int(usd.split("萬")[1]) if "萬" in usd else int(usd)
            F.setdefault("text",{})[yy]={"growth":float(mm.group(2)),"gdp_usd":usd,"cpi":float(mm.group(4))}
        # 重要經濟指標表：抓含「年(f)」列
        seg=t[t.find("重要經濟指標表"):] if "重要經濟指標表" in t else ""
        F["table_lines"]=[l.strip() for l in seg.splitlines() if re.search(r"\d{3}\s*年?\s*\(?[fprFPR]\)?",l) and re.search(r"\d",l)][:30]
        F["table_head"]=[l.strip() for l in seg.splitlines()[:25] if l.strip()]
    log["forecast"]=F
except Exception as e: log["forecast"]={"error":repr(e)[:300]}
json.dump(log,open(f"{OUT}/latest.json","w"),ensure_ascii=False,indent=1)
print(json.dumps({"wages":{k:v for k,v in log["wages"].items() if k!="annual"},"forecast_title":log["forecast"].get("title"),"forecast_rows":len(log["forecast"].get("rows",[]))},ensure_ascii=False)[:1500])
