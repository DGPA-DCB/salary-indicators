"""政府資料開放平臺：自動找出主計總處各年度「中央政府總決算（表）」「總預算（案）－預算表」資料集編號。
搜尋 API 不接受 GET，改讀平臺 sitemap 與資料集頁標題。輸出 opendata/discover.json。"""
import json, os, re, time, urllib.request, urllib.robotparser, gzip, io
UA="DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
log=[]
def step(**k): log.append(k); print(json.dumps(k,ensure_ascii=False)[:500])
def get(u,timeout=120):
    with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"*/*"}),timeout=timeout) as r:
        b=r.read()
        if r.headers.get("Content-Encoding")=="gzip" or u.endswith(".gz"): 
            try: b=gzip.decompress(b)
            except Exception: pass
        return b
rp=urllib.robotparser.RobotFileParser()
try: rp.parse(get("https://data.gov.tw/robots.txt").decode("utf-8","replace").splitlines()); step(robots="ok")
except Exception as e: rp=None; step(robots="error",error=repr(e)[:100])
can=lambda u: True if rp is None else rp.can_fetch(UA,u)
urls=[]
for sm in ["https://data.gov.tw/sitemap.xml","https://data.gov.tw/sitemap_index.xml","https://data.gov.tw/sitemaps.xml"]:
    if not can(sm): step(url=sm,skipped="robots"); continue
    try:
        b=get(sm); t=b.decode("utf-8","replace"); locs=re.findall(r"<loc>([^<]+)</loc>",t); step(url=sm,locs=len(locs),sample=locs[:3])
        for l in locs:
            if "sitemap" in l and l.endswith((".xml",".xml.gz")):
                try: tt=get(l).decode("utf-8","replace"); urls+=re.findall(r"<loc>([^<]+)</loc>",tt)
                except Exception as e: step(url=l,error=repr(e)[:100])
            else: urls.append(l)
        if locs: break
    except Exception as e: step(url=sm,error=repr(e)[:150])
ds=sorted({u for u in urls if "/dataset/" in u}); step(dataset_urls=len(ds))
# API detail for candidate ids via existing v2 dataset endpoint (works for GET)
out={}
# Use known DGBAS organization listing if sitemap empty
if not ds:
    for page in range(1,4):
        u=f"https://data.gov.tw/datasets/search?p={page}&size=100&s=_score_desc&qs=%E4%B8%AD%E5%A4%AE%E6%94%BF%E5%BA%9C%E7%B8%BD%E6%B1%BA%E7%AE%97"
        if not can(u): step(url=u,skipped="robots"); break
        try: t=get(u).decode("utf-8","replace"); ids=re.findall(r'/dataset/(\d+)',t); step(url=u,ids=len(set(ids))); ds+=["https://data.gov.tw/dataset/"+i for i in set(ids)]
        except Exception as e: step(url=u,error=repr(e)[:100])
json.dump({"log":log,"dataset_urls":ds[:5000]},open("opendata/discover.json","w"),ensure_ascii=False,indent=0)
