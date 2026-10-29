import re,json,sys,subprocess,os,traceback
out={"err":[]}
def sec(name,fn):
    try: fn()
    except Exception: out["err"].append([name,traceback.format_exc()[-800:]])
def s0():
    src=open('scripts/dgbas_fetch.py').read().split('log={"run"')[0]; exec(src,globals())
sec("exec",s0)
def s1():
    page=get("https://www.dgbas.gov.tw/News_Content.aspx?n=3602&s=236591").decode("utf-8","replace")
    out["titles"]={}
    for f in re.findall(r'href="([^"]+\.ods)"',page):
        try:
            rows=ods_rows(get(f)); out["titles"][f.rsplit("/",1)[1]]=[" ".join(c for c in r if c)[:80] for r in rows if any(r)][:3]
        except Exception as e: out["titles"][f]=repr(e)[:80]
    pdfs=re.findall(r'href="([^"]+\.pdf)"',page); out["pdfs"]=pdfs
    os.makedirs("/tmp/p",exist_ok=True)
    for u in pdfs[:3]:
        b=get(u); open("/tmp/p/x.pdf","wb").write(b)
        t=subprocess.run(["pdftotext","-layout","/tmp/p/x.pdf","-"],capture_output=True,text=True).stdout
        lines=[l.strip() for l in t.splitlines() if re.search(r"每人GDP|每人國內生產毛額|消費者物價|重要經濟指標|經濟成長率",l)]
        out.setdefault("pdf_hits",{})[u.rsplit("/",1)[1]]=lines[:40]
sec("gdp",s1)
def s2():
    page=get("https://www.dgbas.gov.tw/News_Content.aspx?n=3602&s=236785").decode("utf-8","replace")
    fs=re.findall(r'href="([^"]+\.(?:ods|pdf))"',page); out["aug_files"]=fs
    for f in [x for x in fs if x.endswith(".ods")][:4]:
        rows=ods_rows(get(f)); out.setdefault("aug",{})[f.rsplit("/",1)[1]]=[[c for c in r if c][:10] for r in rows if any(r)][:14]
sec("aug",s2)
json.dump(out,open("opendata/dgbas/probe.json","w"),ensure_ascii=False,indent=1)
