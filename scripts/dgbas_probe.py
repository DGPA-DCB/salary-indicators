import re,json,sys
sys.argv=['x']; src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]
exec(src)
out={}
lst=get("https://www.dgbas.gov.tw/News.aspx?n=3602&sms=10980").decode("utf-8","replace")
out["list"]=re.findall(r'href="(News_Content\.aspx\?n=3602&(?:amp;)?s=\d+)"[^>]*>([^<]{5,120})<',lst)[:40]
out["dates"]=re.findall(r'(\d{3}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2}|\d{3}/\d{2}/\d{2})',lst)[:40]
page=get("https://www.dgbas.gov.tw/News_Content.aspx?n=3602&s=236591").decode("utf-8","replace")
files=re.findall(r'href="([^"]+\.(?:ods|xlsx))"',page); out["gdp_files"]=files
for f in files:
    try:
        rows=ods_rows(get(f)) if f.endswith(".ods") else None
        if rows is None: continue
        flat="|".join("|".join(c for c in r if c) for r in rows)
        if "每人GDP" in flat or "消費者物價" in flat or "每人國內生產毛額" in flat:
            out.setdefault("hits",{})[f]=[[c for c in r if c][:14] for r in rows if any(r)][:45]
    except Exception as e: out.setdefault("err",[]).append([f,repr(e)[:100]])
# 表2 header
base="https://ws.dgbas.gov.tw/001/Upload/463/relfile/10980/236702"
rows=ods_rows(get(base+"/表2.ods")); out["t2"]=[[c for c in r if c][:16] for r in rows if any(r)][:12]
json.dump(out,open("opendata/dgbas/probe.json","w"),ensure_ascii=False,indent=1)
