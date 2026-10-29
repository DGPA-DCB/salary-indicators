import re,json,traceback,os,html
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
for ds in [13973,13976]:
    try:
        j=json.loads(get(f"https://data.gov.tw/api/v2/rest/dataset/{ds}").decode("utf-8"))
        r=j.get("result",j); out[str(ds)]={"title":r.get("title"),"desc":(r.get("description") or "")[:300],"dist":[(d.get("resourceDescription"),d.get("resourceDownloadUrl"),d.get("resourceFormat")) for d in (r.get("distribution") or [])][:10]}
        # 下載第一個資源前2KB
        for d in (r.get("distribution") or [])[:3]:
            u=d.get("resourceDownloadUrl")
            try:
                b=get(u); txt=b[:6000].decode("utf-8","replace")
                out[str(ds)].setdefault("samples",[]).append([u,len(b),txt[:2500]])
            except Exception as e: out[str(ds)].setdefault("samples",[]).append([u,repr(e)[:120]])
    except Exception: out["err"].append([ds,traceback.format_exc()[-300:]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
