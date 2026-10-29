import re,json,traceback,html,os,subprocess,tempfile
os.makedirs('opendata/probe',exist_ok=True)
out={"err":[]}
try:
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src)
except Exception: out['err'].append(['exec',traceback.format_exc()[-800:]])
B="https://service.mof.gov.tw/public/Data/statistic/Year_Fin/114%E9%9B%BB%E5%AD%90%E6%9B%B8/htm/"
for n in list(range(32000,32200,10))+[31010,31020,31030,33010,33020,33030,33040]:
    try:
        b=get(B+f"{n}.pdf")
        if b[:4]!=b"%PDF": continue
        fn=tempfile.mktemp(suffix=".pdf"); open(fn,"wb").write(b)
        t=subprocess.run(["pdftotext","-layout",fn,"-"],capture_output=True,text=True).stdout
        head=[l.strip() for l in t.splitlines() if l.strip()][:6]
        hit=[l.strip()[:160] for l in t.splitlines() if re.search(r"舉借|決算",l)][:12]
        out[str(n)]={"head":head,"hit":hit,"len":len(t)}
    except Exception as e: out["err"].append([n,repr(e)[:100]])
json.dump(out,open("opendata/probe/out.json","w"),ensure_ascii=False,indent=1)
