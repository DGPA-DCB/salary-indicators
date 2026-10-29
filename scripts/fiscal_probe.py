"""財政部來源第二階段探勘（GitHub Actions）。輸出 opendata/fiscal/。"""
import json, os, re, time, urllib.request, urllib.parse, urllib.robotparser, subprocess
OUT="opendata/fiscal"; os.makedirs(OUT, exist_ok=True)
UA="DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
log={"run":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"steps":[]}
def step(**k):
    log["steps"].append(k); print(json.dumps(k,ensure_ascii=False)[:700])
    json.dump(log,open(f"{OUT}/probe2.json","w"),ensure_ascii=False,indent=1)
rps={}
def allowed(u):
    host=re.match(r"https?://[^/]+/",u).group(0)
    if host not in rps:
        rp=urllib.robotparser.RobotFileParser()
        try: t=urllib.request.urlopen(urllib.request.Request(host+"robots.txt",headers={"User-Agent":UA}),timeout=30).read().decode("utf-8","replace"); rp.parse(t.splitlines())
        except Exception: rp=None
        rps[host]=rp
    return True if rps[host] is None else rps[host].can_fetch(UA,u)
def get(u,timeout=120):
    if not allowed(u): step(url=u,skipped="robots"); return None
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"*/*"}),timeout=timeout) as r: return r.read()
    except Exception as e: step(url=u[:120],error=repr(e)[:200]); return None
def pdf_pages(b, pat, maxp=400):
    open("/tmp/x.pdf","wb").write(b)
    n=int(re.search(r"Pages:\s+(\d+)",subprocess.run(["pdfinfo","/tmp/x.pdf"],capture_output=True,text=True).stdout).group(1))
    hits=[]
    for i in range(1,min(n,maxp)+1):
        tx=subprocess.run(["pdftotext","-layout","-f",str(i),"-l",str(i),"/tmp/x.pdf","-"],capture_output=True,text=True).stdout
        if re.search(pat,tx): hits.append((i,tx))
    return n,hits
# A. 財政統計年報 114 電子書：目錄與各級政府餘絀表、中央債務表
base="https://service.mof.gov.tw/public/Data/statistic/Year_Fin/114%E9%9B%BB%E5%AD%90%E6%9B%B8/htm/"
b=get(base+"%E6%8F%90%E8%A6%81%E5%88%86%E6%9E%90%E5%8F%8A%E5%B0%88%E8%BC%89.pdf")
if b:
    n,h=pdf_pages(b,r"(各級政府歲入歲出|歲入歲出餘絀|公共債務|債務舉借|1年以上)",120)
    step(yearbook="提要分析及專載",pages=n,hits=[i for i,_ in h])
    with open(f"{OUT}/yearbook114_excerpt.txt","w",encoding="utf-8") as f:
        for i,tx in h[:12]: f.write(f"\n===== 第{i}頁 =====\n{tx}")
# 年報章節表 PDF 清單（嘗試常見檔名）
for name in ["1-1.pdf","1-2.pdf","1-3.pdf","1-4.pdf","%E7%9B%AE%E9%8C%84.pdf","index.htm","index.html",""]:
    r=get(base+name,60)
    if r: step(try_=base+name, bytes=len(r), kind="PDF" if r[:4]==b"%PDF" else r[:80].decode("utf-8","replace"))
# B. 國庫署中央政府債務頁
for u in ["https://www.nta.gov.tw/multiplehtml/1617","https://www.nta.gov.tw/htmlList/70"]:
    b=get(u)
    if b:
        txt=b.decode("utf-8","replace")
        links=re.findall(r'href="([^"]+)"[^>]*>\s*([^<]{2,80})\s*<',txt)
        sel=[(t.strip(),h) for h,t in links if re.search(r"債務|舉借|未償|統計|年度",t)][:40]
        step(url=u,links=sel)
        open(f"{OUT}/nta_{u.rsplit('/',1)[1]}.html","w").write(txt[:200000])
# C. 開放平臺：用網頁搜尋頁（非API）
for q in ["中央政府總決算","中央政府債務","各級政府歲入歲出"]:
    b=get("https://data.gov.tw/datasets/search?p=1&size=50&s=_score_desc&qs="+urllib.parse.quote(q) if False else "https://data.gov.tw/datasets/search?qs="+urllib.parse.quote(q))
    if b:
        txt=b.decode("utf-8","replace"); ids=re.findall(r'/dataset/(\d+)"[^>]*>([^<]{3,80})<',txt)
        step(search=q,bytes=len(b),found=ids[:30])

# rerun 1793243682
