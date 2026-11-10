import re,json,traceback,os,html
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
try:
    p=get("https://www.ndc.gov.tw/nc_332_40618").decode("utf-8","replace")
    t=re.sub(r"<script.*?</script>|<style.*?</style>","",p,flags=re.S); t=html.unescape(re.sub(r"<[^>]+>"," ",t)); t=re.sub(r"\s+"," ",t)
    i=t.find("景氣"); out["text"]=t[max(0,i-300):i+4000]
    out["files"]=[html.unescape(h) for h in re.findall(r'href="([^"]+\.(?:pdf|xlsx?|ods))"',p)][:10]
except Exception: out["err"].append(["ndc",traceback.format_exc()[-400:]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
