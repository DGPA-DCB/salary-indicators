import re,json,traceback,os,html
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
for ds in [12131,12130,12132,12146]:
    try:
        j=json.loads(get(f"https://data.gov.tw/api/v2/rest/dataset/{ds}").decode("utf-8")); r=j.get("result",j)
        out[str(ds)]={"title":r.get("title"),"desc":(r.get("description") or "")[:300],"f":[(d.get("resourceDescription"),d.get("resourceFormat"),d.get("resourceDownloadUrl")) for d in (r.get("distribution") or [])][:6]}
        for d in (r.get("distribution") or [])[:2]:
            try:
                b=get(d.get("resourceDownloadUrl")); out[str(ds)].setdefault("samples",[]).append([len(b),b[:6000].decode("utf-8-sig","replace")])
            except Exception as e: out[str(ds)].setdefault("samples",[]).append([repr(e)[:120]])
    except Exception as e: out["err"].append([ds,repr(e)[:100]])
try:
    p=get("https://www.nta.gov.tw/multiplehtml/1617").decode("utf-8","replace")
    out["nta1617"]=[(html.unescape(h),re.sub(r"<[^>]+>","",t).strip()[:60]) for h,t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',p,re.S) if "舉借" in t]
except Exception as e: out["err"].append(["nta",repr(e)[:100]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
