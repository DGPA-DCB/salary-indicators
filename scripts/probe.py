import re,json,traceback,os,subprocess,tempfile
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
for y in [105,107,109]:
    u=f"https://service.mof.gov.tw/public/Data/statistic/Year_Fin/{y}%E9%9B%BB%E5%AD%90%E6%9B%B8/htm/%E6%8F%90%E8%A6%81%E5%88%86%E6%9E%90%E5%8F%8A%E5%B0%88%E8%BC%89.pdf"
    try:
        b=get(u); fn=tempfile.mktemp(suffix=".pdf"); open(fn,"wb").write(b)
        t=subprocess.run(["pdftotext","-layout",fn,"-"],capture_output=True,text=True).stdout
        i=t.find("舉借、還本及餘額"); out[str(y)]=t[i-200:i+2600] if i>0 else "no table"
    except Exception as e: out["err"].append([y,repr(e)[:100]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
