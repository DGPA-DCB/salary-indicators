import re,json,traceback,html,os
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
def sec(n,fn):
    try: out[n]=fn()
    except Exception: out["err"].append([n,traceback.format_exc()[-400:]])
def links(u,pat=r"債|舉借|決算|統計|餘額"):
    p=get(u).decode("utf-8","replace")
    return [(html.unescape(h),re.sub(r"\s+"," ",re.sub(r"<[^>]+>","",t)).strip()[:80]) for h,t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',p,re.S) if re.search(pat,t)]
def text(u,n=3000):
    p=get(u).decode("utf-8","replace"); p=re.sub(r"<script.*?</script>|<style.*?</style>","",p,flags=re.S)
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",p))[:n]
B="https://service.mof.gov.tw/public/Data/statistic/Year_Fin/114%E9%9B%BB%E5%AD%90%E6%9B%B8/"
for c in ["htm/yearmenu.htm","yearmenu.htm","index.htm","htm/index.htm","htm/menu.htm","htm/yearmenu.html"]:
    sec("yb_"+c,lambda c=c: links(B+c,r"."))
sec("yb_dir",lambda: text(B,2000))
sec("yb_htm_dir",lambda: text(B+"htm/",2000))
sec("nta_news",lambda: text("https://www.nta.gov.tw/singlehtml/1617?cntId=de83153e99c24aedac59b3a6c05923fc",4000))
sec("nta_1617_links",lambda: links("https://www.nta.gov.tw/multiplehtml/1617",r"."))
sec("mof_stat",lambda: links("https://www.mof.gov.tw/multiplehtml/1065",r"年報|月報|債務"))
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
