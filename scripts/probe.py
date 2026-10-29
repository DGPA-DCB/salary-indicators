import re,json,traceback,os
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
for ds in list(range(30948,30962))+[13761,13760,13762,13763,13764]:
    try:
        j=json.loads(get(f"https://data.gov.tw/api/v2/rest/dataset/{ds}").decode("utf-8")); r=j.get("result",j)
        if not r.get("title"): continue
        out[str(ds)]={"title":r.get("title"),"desc":(r.get("description") or "")[:200],"f":[(d.get("resourceDescription"),d.get("resourceFormat"),d.get("resourceDownloadUrl")) for d in (r.get("distribution") or [])][:6]}
        if "債務" in (r.get("title") or ""):
            for d in (r.get("distribution") or [])[:2]:
                try:
                    b=get(d.get("resourceDownloadUrl")); out[str(ds)].setdefault("samples",[]).append([len(b),b[:3000].decode("utf-8","replace")])
                except Exception as e: out[str(ds)].setdefault("samples",[]).append([repr(e)[:120]])
    except Exception as e: out["err"].append([ds,repr(e)[:100]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
