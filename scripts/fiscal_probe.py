"""財政部來源探勘（GitHub Actions）：
A. 財政統計年報（service.mof.gov.tw）各級政府歲入歲出餘絀（T、V欄）
B. 國庫署債務統計（www.nta.gov.tw）中央政府債務舉借（W–Z欄）
C. 政府資料開放平臺搜尋 API：各年度「中央政府總決算 歲出用途別」資料集（P欄）、財政部債務相關資料集
遵守 robots.txt；遇阻擋即停。輸出 opendata/fiscal/probe.json。"""
import json, os, re, time, urllib.request, urllib.parse, urllib.robotparser, ssl, unicodedata
OUT="opendata/fiscal"; os.makedirs(OUT, exist_ok=True)
UA="DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
log={"run":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"steps":[]}
def step(**k): log["steps"].append(k); print(json.dumps(k,ensure_ascii=False)[:600])
rps={}
def allowed(u):
    host=re.match(r"https?://[^/]+/",u).group(0)
    if host not in rps:
        rp=urllib.robotparser.RobotFileParser()
        try:
            t=urllib.request.urlopen(urllib.request.Request(host+"robots.txt",headers={"User-Agent":UA}),timeout=30).read().decode("utf-8","replace"); rp.parse(t.splitlines()); step(robots=host,text=t[:200])
        except Exception as e: rp=None; step(robots=host,error=repr(e)[:100])
        rps[host]=rp
    return True if rps[host] is None else rps[host].can_fetch(UA,u)
def get(u,timeout=60):
    if not allowed(u): step(url=u,skipped="robots"); return None,None
    req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"*/*"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r: return r.status, r.read()
    except Exception as e:
        step(url=u[:120],error=repr(e)[:200]); return None,None
# C. data.gov.tw search API
res={"datasets":{}}
for q in ["中央政府總決算 歲出用途別","中央政府總決算表","中央政府總決算","債務 中央政府 舉借","財政統計年報","各級政府 歲入歲出 餘絀","公共債務 未償餘額"]:
    st,b=get("https://data.gov.tw/api/v2/rest/dataset?q="+urllib.parse.quote(q)+"&limit=50")
    if not b: continue
    try:
        d=json.loads(b.decode("utf-8")); items=d.get("result",d) if isinstance(d,dict) else d
        if isinstance(items,dict): items=items.get("results") or items.get("data") or []
        lst=[{"id":x.get("id"),"title":x.get("title"),"org":x.get("publisher") or x.get("organization"),"updated":x.get("modifiedDate")} for x in items]
        res["datasets"][q]=lst; step(search=q,n=len(lst),sample=[x["title"] for x in lst[:8]])
    except Exception as e: step(search=q,error=repr(e)[:200],head=b[:200].decode("utf-8","replace"))
# A. 財政統計年報
for u in ["https://service.mof.gov.tw/public/Data/statistic/Year_Fin/","https://www.mof.gov.tw/singlehtml/285?cntId=mof_285_1","https://service.mof.gov.tw/public/Data/statistic/Year_Fin/114%E9%9B%BB%E5%AD%90%E6%9B%B8/htm/%E6%8F%90%E8%A6%81%E5%88%86%E6%9E%90%E5%8F%8A%E5%B0%88%E8%BC%89.pdf"]:
    st,b=get(u,120)
    if b: step(url=u[:120],status=st,bytes=len(b),head=b[:120].decode("utf-8","replace") if b[:4]!=b"%PDF" else "PDF")
# B. 國庫署
for u in ["https://www.nta.gov.tw/singlehtml/67?cntId=nta_840_67","https://www.nta.gov.tw/","https://www.nta.gov.tw/multiplehtml/238"]:
    st,b=get(u,120)
    if b:
        txt=b.decode("utf-8","replace"); links=re.findall(r'href="([^"]+)"[^>]*>([^<]{2,60})<',txt)
        step(url=u,status=st,bytes=len(b),links=[(t.strip(),h[:80]) for h,t in links if re.search(r"債務|舉借|歲入歲出|決算|統計",t)][:25])
json.dump(res,open(f"{OUT}/datasets.json","w"),ensure_ascii=False,indent=1)
json.dump(log,open(f"{OUT}/probe.json","w"),ensure_ascii=False,indent=1)
