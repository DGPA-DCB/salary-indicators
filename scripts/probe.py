import re,json,traceback,os,html
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
def text(u,n=6000):
    p=get(u).decode("utf-8","replace"); p=re.sub(r"<script.*?</script>|<style.*?</style>","",p,flags=re.S)
    links=[(html.unescape(h),re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",t)).strip()[:60]) for h,t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',p,re.S) if re.search(r"\.(pdf|xlsx?|ods|docx?)",h,re.I)]
    i=p.find("主要內容"); body=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",p[i:] if i>0 else p)))
    return {"text":body[:n],"files":links}
for k,u in {"fdl16":"https://www.nta.gov.tw/singlehtml/1617?cntId=3898992fd32847d0adeca84eef685e0a","kpi":"https://www.nta.gov.tw/singlehtml/1617?cntId=nta_17283_1617","stat":"https://www.nta.gov.tw/singlehtml/17?cntId=46c30ccc22844fe98ee02123e8f261ad"}.items():
    try: out[k]=text(u)
    except Exception: out["err"].append([k,traceback.format_exc()[-300:]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
