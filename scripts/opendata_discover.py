"""政府資料開放平臺：以資料集詳情 API（GET 可用）掃描編號區間，找出主計總處「中央政府總決算（表）」
與「總預算（案）－預算表／簡明表」新年度資料集，寫入 opendata/discover.json 並自動加入 catalog_ids.txt。
每月執行；掃描上限 600 筆，間隔 0.5 秒。"""
import json, os, re, time, urllib.request
UA="DGPA-salary-indicators/1.0 (+https://github.com/DGPA-DCB/salary-indicators)"
API="https://data.gov.tw/api/v2/rest/dataset/{}"
PAT=re.compile(r"(\d{3})年度中央政府(總決算表?$|總決算$|總預算案?[－-](預算表|簡明表|參考表))")
try: st=json.load(open("opendata/discover.json",encoding="utf-8"))
except Exception: st={"found":{},"scanned_to":175205}
known=[int(l.strip()) for l in open("opendata/catalog_ids.txt",encoding="utf-8") if l.strip().isdigit()]
start=max(st.get("scanned_to",0),max(known)); end=start+600; n=0
for i in range(start+1,end+1):
    try:
        with urllib.request.urlopen(urllib.request.Request(API.format(i),headers={"User-Agent":UA}),timeout=30) as r: d=json.loads(r.read().decode("utf-8"))
        rr=d.get("result",d); t=(rr.get("title") or "").strip()
        if t and PAT.search(t): st["found"][str(i)]={"title":t,"updated":rr.get("modifiedDate")}; print(i,t)
        n+=1
    except Exception as e:
        pass
    time.sleep(0.5)
st["scanned_to"]=end; st["last_run"]=time.strftime("%Y-%m-%d")
json.dump(st,open("opendata/discover.json","w"),ensure_ascii=False,indent=1)
new=[k for k in st["found"] if int(k) not in known]
if new:
    with open("opendata/catalog_ids.txt","a",encoding="utf-8") as f: f.write("\n"+"\n".join(new)+"\n")
print({"scanned":n,"range":[start+1,end],"found_total":len(st["found"]),"new":new})
