"""主計總處統計資訊網（stat.gov.tw）探勘：國民所得預測、薪資統計電子檔是否可自動取得。遵守 robots.txt。"""
import json, os, re, time, urllib.request, urllib.robotparser
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
            t=urllib.request.urlopen(urllib.request.Request(host+"robots.txt",headers={"User-Agent":UA}),timeout=30).read().decode("utf-8","replace"); rp.parse(t.splitlines()); step(robots=host,text=t[:400])
        except Exception as e: rp=None; step(robots=host,error=repr(e)[:100])
        rps[host]=rp
    return True if rps[host] is None else rps[host].can_fetch(UA,u)
def get(u,timeout=90):
    if not allowed(u): step(url=u,skipped="robots disallow"); return None
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"*/*"}),timeout=timeout) as r: return r.read()
    except Exception as e: step(url=u[:120],error=repr(e)[:200]); return None
for u in ["https://www.stat.gov.tw/cl.aspx?n=3680","https://www.stat.gov.tw/cp.aspx?n=2679","https://www.stat.gov.tw/News.aspx?n=3602","https://www.dgbas.gov.tw/News.aspx?n=3602","https://www.dgbas.gov.tw/cl.aspx?n=3680"]:
    b=get(u)
    if b:
        t=b.decode("utf-8","replace"); links=re.findall(r'href="([^"]+)"[^>]*>([^<]{2,80})<',t)
        step(url=u,bytes=len(b),links=[(x.strip(),h[:100]) for h,x in links if re.search(r"預測|展望|重要經濟指標|薪資|xls|ods|csv|新聞稿",x+h)][:30])
