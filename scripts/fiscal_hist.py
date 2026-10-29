"""財政統計年報歷年版（105–109 年版）提要分析「中央政府1年以上公共債務之舉借、還本及餘額」表：
各版說明「N年(含)以前為決算審定數」，取各年度最新一版之決算審定數 → W（合計）、X（列入債限）、Z（占歲出比率）。
（110 年版起舉借數改為預算數，故 108 年以後無逐年決算審定舉借數。）輸出 opendata/fiscal/debt_final.json。"""
import re,json,os,subprocess,tempfile,urllib.request,urllib.robotparser
OUT="opendata/fiscal"; os.makedirs(OUT,exist_ok=True)
UA="DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":UA}),timeout=120) as r: return r.read()
rp=urllib.robotparser.RobotFileParser()
try: rp.parse(get("https://service.mof.gov.tw/robots.txt").decode("utf-8","replace").splitlines())
except Exception: rp=None
res={"W":{},"X":{},"Z":{},"editions":{}}
best={}
for ed in range(103,112):
    u=f"https://service.mof.gov.tw/public/Data/statistic/Year_Fin/{ed}%E9%9B%BB%E5%AD%90%E6%9B%B8/htm/%E6%8F%90%E8%A6%81%E5%88%86%E6%9E%90%E5%8F%8A%E5%B0%88%E8%BC%89.pdf"
    if rp and not rp.can_fetch(UA,u): continue
    try: b=get(u)
    except Exception as e: res["editions"][ed]={"error":repr(e)[:80]}; continue
    if b[:4]!=b"%PDF": res["editions"][ed]={"error":"not pdf"}; continue
    fn=tempfile.mktemp(suffix=".pdf"); open(fn,"wb").write(b)
    t=subprocess.run(["pdftotext","-layout",fn,"-"],capture_output=True,text=True).stdout
    i=t.find("舉借、還本及餘額")
    if i<0: res["editions"][ed]={"error":"table not found"}; continue
    sec=t[i:i+3000]
    m=re.search(r"(\d{3})\s*年\s*\(含\)\s*以前為決算審定數",sec)
    cutoff=int(m.group(1)) if m else None
    rows={}
    for mm in re.finditer(r"\n\s*(\d{3})年\s+([\d,]+)\s+([\d,－-]+)\s+([\d.－-]+)\s+([\d,－-]+)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)\s+([\d,]+)",sec):
        n=lambda s: 0.0 if s.strip("－-")=="" else float(s.replace(",",""))
        rows[int(mm.group(1))]={"W":n(mm.group(2)),"X":n(mm.group(3)),"Z":n(mm.group(4)),"Y_budget":n(mm.group(9))}
    res["editions"][ed]={"cutoff":cutoff,"years":sorted(rows)}
    if cutoff is None: continue
    for y,v in rows.items():
        if y<=cutoff and (y not in best or ed>best[y][0]): best[y]=(ed,v,u)
for y,(ed,v,u) in sorted(best.items()):
    for k in "WXZ":
        res[k][y]={"value":v[k],"basis":"決算審定","unit":"%" if k=="Z" else "億元","source":u,"detail":f"{ed}年財政統計年報提要分析（{y}年為決算審定數）；歲出為預算數{v['Y_budget']:,.0f}"}
json.dump(res,open(f"{OUT}/debt_final.json","w"),ensure_ascii=False,indent=1)
print(json.dumps({k:{y:v["value"] for y,v in res[k].items()} for k in "WXZ"},ensure_ascii=False)); print(res["editions"])
