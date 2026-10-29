import re,json,traceback,os,html
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
B="https://ws.dgbas.gov.tw/001/Upload/461/relfile/10748/"
for k,u in {"前5_114_收支":B+"236210/2收支簡明.ods","前5_114_融資":B+"236210/6融資調度.ods","前4_112-113_收支":B+"234785/4-1收支.ods","前4_融資":B+"234785/4-5融資.ods"}.items():
    try:
        rows=ods_rows(get(u)); out[k]=[[c for c in r if c][:12] for r in rows if any(r)][:40]
    except Exception: out["err"].append([k,traceback.format_exc()[-200:]])
try:
    p=get("https://www.dgbas.gov.tw/News_Content.aspx?n=1751&s=236126").decode("utf-8","replace")
    out["疫後_files"]=[html.unescape(h) for h in re.findall(r'href="([^"]+\.ods)"',p)][:20]
    for h in out["疫後_files"]:
        if "收支" in urllib.parse.unquote(h):
            rows=ods_rows(get(h)); out["疫後_收支"]=[[c for c in r if c][:12] for r in rows if any(r)][:40]; break
except Exception: out["err"].append(["疫後",traceback.format_exc()[-200:]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
