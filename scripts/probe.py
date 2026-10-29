import re,json,traceback,html
src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
out={"err":[]}
def sec(n,fn):
    try: out[n]=fn()
    except Exception: out["err"].append([n,traceback.format_exc()[-600:]])
def links(u):
    p=get(u).decode("utf-8","replace")
    return [(html.unescape(h),re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",t)).strip()[:80]) for h,t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',p,re.S) if re.search(r"債|舉借|決算|統計",t)]
sec("mof_debt",lambda: links("https://www.mof.gov.tw/debt/multiplehtml/658c411c30dd4400a4517ad5e6d803ef"))
sec("mof_debt_home",lambda: links("https://www.mof.gov.tw/debt/"))
sec("nta_debt",lambda: links("https://www.nta.gov.tw/"))
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
