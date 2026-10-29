import re,json,traceback,os
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
for ds in [166502,173426,170600,170599,172964,173425,173427,173428,173429,173430,170601,170602,170603,166501,166503,166504,166505,166506,166507,166508,172960,172961,172962,172963,172965,172966,172967]:
    try:
        j=json.loads(get(f"https://data.gov.tw/api/v2/rest/dataset/{ds}").decode("utf-8")); r=j.get("result",j)
        out[str(ds)]={"title":r.get("title"),"n":len(r.get("distribution") or []),"f":[(d.get("resourceDescription"),d.get("resourceDownloadUrl","")[-60:]) for d in (r.get("distribution") or [])][:6]}
    except Exception as e: out["err"].append([ds,repr(e)[:100]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
