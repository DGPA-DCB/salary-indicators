import re,json,traceback,os,html
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
def links(u,pat=r"."):
    p=get(u).decode("utf-8","replace")
    return [(html.unescape(h),re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",t)).strip()[:90]) for h,t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',p,re.S) if re.search(pat,t) or re.search(pat,h)]
try:
    out["special"]=links("https://www.dgbas.gov.tw/News.aspx?n=1751&sms=10748",r"News_Content|決算")[:80]
    out["total"]=links("https://www.dgbas.gov.tw/News.aspx?n=3831&sms=11520",r"News_Content")[:30]
    first=[h for h,t in out["special"] if "News_Content" in h][:2]
    for h in first:
        u="https://www.dgbas.gov.tw/"+h.replace("&amp;","&").lstrip("/")
        out["sp:"+u]=links(u,r"\.(pdf|ods|xlsx?|xml|zip)")[:60]
except Exception: out["err"].append(["sp",traceback.format_exc()[-300:]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
