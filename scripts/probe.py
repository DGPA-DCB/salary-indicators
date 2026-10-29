import re,json,traceback,os,html,subprocess,tempfile,zipfile,io
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
try:
    u="https://www.nta.gov.tw/singlehtml/67?cntId=nta_840_67"
    p=get(u).decode("utf-8","replace")
    i=p.find("主要內容"); body=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",re.sub(r"<script.*?</script>|<style.*?</style>","",p[i:],flags=re.S))))
    out["text"]=body[:6000]
    files=[(html.unescape(h),re.sub(r"<[^>]+>","",t).strip()[:60]) for h,t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',p,re.S) if re.search(r"\.(pdf|xlsx?|ods|csv)|download|Download|File",h)]
    out["files"]=files[:20]
    # 嘗試表格
    tables=re.findall(r"<table.*?</table>",p,re.S)
    out["tables"]=[re.sub(r"\s+"," ",html.unescape(re.sub(r"</t[dh]>"," | ",re.sub(r"</tr>","\n",re.sub(r"<(?!/?t[rdh])[^>]+>","",t)))))[:6000] for t in tables][:3]
    for h,t in files[:3]:
        try:
            uu=h if h.startswith("http") else "https://www.nta.gov.tw"+h
            b=get(uu); fn=tempfile.mktemp(); open(fn,"wb").write(b)
            if b[:4]==b"%PDF": out["file:"+t]=subprocess.run(["pdftotext","-layout",fn,"-"],capture_output=True,text=True).stdout[:6000]
            elif b[:2]==b"PK": out["file:"+t]=[[c for c in r if c][:10] for r in ods_rows(b) if any(r)][:40] if uu.endswith(".ods") else "xlsx %d bytes"%len(b)
            else: out["file:"+t]=b[:3000].decode("utf-8","replace")
        except Exception as e: out["err"].append([t,repr(e)[:100]])
except Exception: out["err"].append(["nta",traceback.format_exc()[-300:]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
