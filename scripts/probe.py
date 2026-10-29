import re,json,traceback,os,subprocess,tempfile
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
B="https://service.mof.gov.tw/public/Data/statistic/Year_Fin/114%E9%9B%BB%E5%AD%90%E6%9B%B8/htm/"
for n in [32030,32060,31010]:
    try:
        b=get(B+f"{n}.pdf"); fn=tempfile.mktemp(suffix=".pdf"); open(fn,"wb").write(b)
        t=subprocess.run(["pdftotext","-layout",fn,"-"],capture_output=True,text=True).stdout
        out[str(n)]=t[:9000]
    except Exception as e: out["err"].append([n,repr(e)[:100]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
