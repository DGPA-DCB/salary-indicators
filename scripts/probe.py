import re,json,traceback,os,html
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
def links(u,pat):
    p=get(u).decode("utf-8","replace")
    return [(html.unescape(h),re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",t)).strip()[:70]) for h,t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',p,re.S) if re.search(pat,t)]
for k,u in {"sitemap":"https://www.dgbas.gov.tw/sitemap.aspx","home":"https://www.dgbas.gov.tw/"}.items():
    try: out[k]=links(u,r"決算|預算")
    except Exception: out["err"].append([k,traceback.format_exc()[-200:]])
# 追到「決算」頁
try:
    cands=[h for h,t in out.get("sitemap",[])+out.get("home",[]) if "決算" in t]
    for h in cands[:4]:
        u=h if h.startswith("http") else "https://www.dgbas.gov.tw/"+h.lstrip("/")
        out["page:"+u]=links(u,r"特別|決算")[:60]
except Exception: out["err"].append(["follow",traceback.format_exc()[-200:]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
