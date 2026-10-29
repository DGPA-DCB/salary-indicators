"""財政部財政統計年報自動下載（GitHub Actions，每月）。
取最新年度「提要分析及專載」PDF，解析：
  T/V：各級政府歲入歲出淨額餘絀（億元）及占GDP比率（近5年）
  W–Z：中央政府1年以上公共債務（非自償）之舉借、還本及餘額（近5年；舉借數及歲出為預算數）
輸出 opendata/fiscal/yearbook_table1-1.json（供 parse_raw.py 併入）。遵守 robots.txt。"""
import json, os, re, time, urllib.request, urllib.robotparser, subprocess
OUT="opendata/fiscal"; os.makedirs(OUT, exist_ok=True)
UA="DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
def get(u,timeout=120):
    with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"*/*"}),timeout=timeout) as r: return r.read()
rp=urllib.robotparser.RobotFileParser()
try: rp.parse(get("https://service.mof.gov.tw/robots.txt").decode("utf-8","replace").splitlines())
except Exception: rp=None
res={"T":{},"V":{},"W":{},"X":{},"Y":{},"Z":{},"meta":{}}
found=None
for y in range(118,112,-1):
    u=f"https://service.mof.gov.tw/public/Data/statistic/Year_Fin/{y}%E9%9B%BB%E5%AD%90%E6%9B%B8/htm/%E6%8F%90%E8%A6%81%E5%88%86%E6%9E%90%E5%8F%8A%E5%B0%88%E8%BC%89.pdf"
    if rp and not rp.can_fetch(UA,u): continue
    try:
        b=get(u)
        if b[:4]==b"%PDF": found=(y,u,b); break
    except Exception as e: pass
if not found: json.dump({"error":"no yearbook found"},open(f"{OUT}/yearbook_table1-1.json","w")); raise SystemExit
y,u,b=found; open("/tmp/y.pdf","wb").write(b)
tx=subprocess.run(["pdftotext","-layout","/tmp/y.pdf","-"],capture_output=True,text=True).stdout
open(f"{OUT}/yearbook{y}_full.txt","w",encoding="utf-8").write(tx)
res["meta"]={"yearbook":y,"url":u,"fetched":time.strftime("%Y-%m-%d")}
# T：餘(+)絀(-) 列
m=re.search(r"餘\(\+\)絀\(-\)\s+((?:-?[\d,]+\s+){3,6})",tx)
yrs=re.search(r"\n\s*((?:\d{3}\s+){3,6})\s*年",tx[:tx.find("餘(+)絀(-)")] if m else "")
if m:
    vals=[int(v.replace(",","")) for v in m.group(1).split()]
    ys=[int(v) for v in yrs.group(1).split()] if yrs else list(range(y-len(vals)+1,y+1))
    for yy,v in zip(ys[-len(vals):],vals): res["T"][yy]={"value":v,"basis":"決算","unit":"億元","source":u,"detail":"各級政府歲入歲出淨額及餘絀"}
# V：餘(+)絀(-)/GDP
m=re.search(r"餘\(\+\)絀\(-\)/GDP\s+((?:-?[\d.]+\s+){3,6})",tx)
h=re.search(r"\n\s*((?:\d{3} 年\s+){3,6})",tx[:m.start()] if m else "")
if m:
    vals=[float(v) for v in m.group(1).split()]
    ys=[int(v) for v in re.findall(r"(\d{3}) 年",h.group(1))] if h else list(range(y-len(vals)+1,y+1))
    for yy,v in zip(ys[-len(vals):],vals): res["V"][yy]={"value":v,"basis":"決算/GDP","unit":"%","source":u,"detail":"各級政府歲入歲出淨額及餘絀占GDP比率"}
# W–Z：中央政府1年以上公共債務表
sec=tx[tx.find("中央政府 1 年以上公共債務(非自償)之舉借、還本及餘額"):]
for mm in re.finditer(r"\n\s*(\d{3})年\s+([\d,]+)\s+([\d,－-]+)\s+([\d.－-]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)\s+([\d,]+)",sec[:4000]):
    yy=int(mm.group(1)); n=lambda s: None if s.strip("－-")=="" else float(s.replace(",",""))
    res["W"][yy]={"value":n(mm.group(2)),"basis":"預算數","unit":"億元","source":u,"detail":"當年舉借數合計"}
    res["X"][yy]={"value":n(mm.group(3)) or 0,"basis":"預算數","unit":"億元","source":u,"detail":"當年舉借數 列入債限"}
    res["Y"][yy]={"value":n(mm.group(9)),"basis":"預算數","unit":"億元","source":u,"detail":"歲出（總預算及未排除債限之特別預算）"}
    res["Z"][yy]={"value":n(mm.group(4)) or 0,"basis":"預算數","unit":"%","source":u,"detail":"列入債限占歲出比率"}
json.dump(res,open(f"{OUT}/yearbook_table1-1.json","w"),ensure_ascii=False,indent=1)
print(json.dumps({k:{kk:vv.get("value") for kk,vv in v.items()} for k,v in res.items() if k!="meta"},ensure_ascii=False))
