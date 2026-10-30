"""彙整 GitHub 自動下載之官方原始資料，算出彙整表各欄可直接比對之數值。
用法：python3 scripts/parse_raw.py <out.json>
輸出 {"P":{年:{...}},"Q_audit":{年:{...}},"S":{年:{...}},"T":..,"V":..,"W":..,"sources":[...]}；
每筆含 value、basis（決算/預算案/法定預算）、source（檔案路徑或網址）、detail。只做計算與整理，不寫資料庫。"""
import json, os, re, sys, glob, unicodedata
R = {"P": {}, "Q_audit": {}, "S": {}, "sources": []}
def num(s):
    try: return float(str(s).replace(",", "").strip())
    except: return None
# ---- P：中央總決算／總預算 歲出用途別（開放資料 XML）----
for d in sorted(glob.glob("raw/*")):
    name = os.path.basename(d); m = re.match(r"(\d{3})_(總決算|總預算案|總預算)_", name)
    if not m: continue
    y, kind = int(m.group(1)), m.group(2)
    for f in glob.glob(d + "/*.xml"):
        s = open(f, encoding="utf-8-sig", errors="replace").read()
        if "人事費" not in s or "用途" not in os.path.basename(f) + name: continue
        rows = re.split(r"<[^>]*(?:_row|報表資料列)>", s)
        for row in rows[1:3]:
            tags = dict(re.findall(r"<([^/>]+)>([^<]*)</\1>", row))
            nm = tags.get("科目_名稱") or tags.get("名稱") or ""
            if "合" not in nm or "計" not in nm: continue
            p = num(tags.get("經常支出_人事費")); t = num(tags.get("合計"))
            if p and t:
                unit = "千元" if kind != "總決算" else "元"
                basis = "決算" if kind == "總決算" else "預算案"
                if y not in R["P"] or basis == "決算":
                    R["P"][y] = {"value": round(p / t * 100, 2), "raw": round(p / t * 100, 4), "personnel": p, "total": t, "unit": unit, "basis": basis, "source": f}
            break
# ---- Q（決算）：審計部年報擷取文字「總計／合計」列最後一欄 ----
for d in sorted(glob.glob("opendata/audit/*_直轄市及縣市")):
    y = int(os.path.basename(d)[:3]); f = d + "/excerpt.txt"
    if not os.path.exists(f): continue
    tx = open(f, encoding="utf-8").read()
    m = re.search(r"\n\s*(?:總\s*計|合\s*計)\s+([\d,\s\.－-]+?)(\d{1,2}\.\d{2})\s*\n", tx)
    m2 = re.search(r"占(?:地方)?歲出決算淨額之平均比率為\s*(\d{1,2}\.\d{2})", tx) or re.search(r"占\s*(\d{1,2}\.\d{2})％", tx)
    v = m.group(2) if m else (m2.group(1) if m2 else None)
    if v: R["Q_audit"][y] = {"value": float(v), "basis": "決算", "source": f, "detail": "地方政府人事費負擔情形概況彙計表 總計列（人事費決算數占地方歲出決算淨額比率）"}
# ---- S：中央政府總決算審定餘絀（審計部報告擷取）----
for d in sorted(glob.glob("opendata/audit_central/*")):
    if not os.path.basename(d).isdigit(): continue
    y = int(os.path.basename(d)); f = d + "/excerpt.txt"
    if not os.path.exists(f): continue
    tx = unicodedata.normalize("NFKC", open(f, encoding="utf-8").read()).replace("\n", "")
    m = re.search(r"歲入歲出相抵[，,]?審定(?:歲入歲出)?(賸餘|差短)為?([\d,]+)億", tx)
    if m:
        v = num(m.group(2)) * (1 if m.group(1) == "賸餘" else -1)
        R["S"][y] = {"value": v, "basis": "決算審定", "truncated": True, "source": f, "detail": m.group(0)[:60]}
# ---- T/V：財政統計年報（若已下載並解析）----
for f in glob.glob("opendata/fiscal/yearbook_table1-1*.json"):
    R.update(json.load(open(f, encoding="utf-8")))
# 國庫署開放資料「中央政府各年度債務舉借概況」（預算數：列入債限、不列入債限、歲出；99年起，逐年更新）→ 取代年報提要之預算數
for f in glob.glob("raw/國庫署_債務舉借概況/*.csv"):
    for line in open(f, encoding="utf-8-sig").read().splitlines()[1:]:
        c = line.split(",")
        if len(c) < 5 or not c[0].strip().isdigit(): continue
        y = int(c[0]); inc, exc, exp = (float(c[1]) / 100, float(c[2]) / 100, float(c[3]) / 100)
        src = "https://data.gov.tw/dataset/12131"
        if (R.get("X", {}).get(y) or {}).get("basis") == "決算": 
            R.setdefault("W", {})[y] = {"value": round(inc + exc), "basis": "預算數", "unit": "億元", "source": src, "detail": f"國庫署：列入債限{inc:,.1f}＋不列入債限{exc:,.1f}"}; continue
        R.setdefault("W", {})[y] = {"value": round(inc + exc), "basis": "預算數", "unit": "億元", "source": src, "detail": f"國庫署：列入債限{inc:,.1f}＋不列入債限{exc:,.1f}"}
        R.setdefault("X", {})[y] = {"value": round(inc), "basis": "預算數", "unit": "億元", "source": src, "detail": "國庫署：當年度舉借債務數列入債限"}
        R.setdefault("Y", {})[y] = {"value": round(exp), "basis": "預算數", "unit": "億元", "source": src, "detail": "國庫署：支歲出預算數"}
        R.setdefault("Z", {})[y] = {"value": round(inc / exp * 100, 2), "basis": "預算數", "unit": "%", "source": src, "detail": f"{inc:,.1f}÷{exp:,.1f}"}
# 歷年年報之決算審定舉借數（101–107 年）優先於預算數
if os.path.exists("opendata/fiscal/debt_final.json"):
    DF = json.load(open("opendata/fiscal/debt_final.json", encoding="utf-8"))
    for k in "WXZ":
        for y, v in DF.get(k, {}).items(): R.setdefault(k, {})[int(y)] = v
# ---- W–Z 決算：總預算「債務之舉借」「歲出」決算數（主計總處總決算收支簡明表 XML）＋國庫署年底實際舉債數 ----
# 規則：列入債限舉借(X)之預算數若等於總預算舉借預算數（即列入債限之特別預算無舉借），X 決算＝總預算舉借決算數；
#       歲出(Y)之預算數若等於總預算歲出預算數（無列入債限之特別預算歲出），Y 決算＝總預算歲出決算數；Z＝X/Y（X 決算為 0 時 Z＝0，不需 Y）。
#       W（含不列入債限）決算：特別決算多為跨年度合併決算，無法逐年拆分；改採國庫署開放資料「1年以上公共債務明細表(實際數)」12月底之中央「當年度實際舉債數」。
yb = {}
for f in glob.glob("opendata/fiscal/yearbook_table1-1*.json"): yb = json.load(open(f, encoding="utf-8"))
for d in sorted(glob.glob("raw/*_總決算_*收支簡明*")):
    y = int(os.path.basename(d)[:3])
    for f in glob.glob(d + "/*.xml"):
        s = open(f, encoding="utf-8-sig", errors="replace").read()
        rows = dict((re.sub(r"^\([一二三四五]\)", "", a.strip()), (num(b), num(c))) for a, b, c in re.findall(r"<項目>(.*?)</項目>\s*<預算數>(.*?)</預算數>\s*<決算數>(.*?)</決算數>", s, re.S))
        if "債務之舉借" not in rows or "歲出" not in rows: continue
        jb, jf = rows["債務之舉借"]; ob, of = rows["歲出"]
        jb, jf, ob, of = [None if v is None else v / 1e8 for v in (jb, jf, ob, of)]
        xb = (yb.get("X") or {}).get(str(y), {}).get("value"); ybud = (yb.get("Y") or {}).get(str(y), {}).get("value")
        R.setdefault("X", {}); R.setdefault("Y", {}); R.setdefault("Z", {})
        if xb is None or abs(xb - jb) <= 1:
            R["X"][y] = {"value": round(jf), "basis": "決算", "unit": "億元", "source": f, "detail": f"總預算債務之舉借決算數{jf:,.1f}億元（預算數{jb:,.1f}；列入債限之特別預算無舉借）"}
            if ybud is None or abs(ybud - ob) <= 1:
                R["Y"][y] = {"value": round(of), "basis": "決算", "unit": "億元", "source": f, "detail": f"總預算歲出決算數{of:,.1f}億元（無列入債限之特別預算歲出）"}
                R["Z"][y] = {"value": (0 if round(jf) == 0 else round(jf / of * 100, 2)), "basis": "決算", "unit": "%", "source": f, "detail": f"{jf:,.1f}÷{of:,.1f}"}
            elif round(jf) == 0:
                R["Z"][y] = {"value": 0, "basis": "決算", "unit": "%", "source": f, "detail": "列入債限舉借決算數為0，比率為0（歲出含列入債限之特別預算，決算數未拆分，Y 欄維持預算數）"}
        else:
            R.setdefault("notes", []).append(f"{y}年 列入債限舉借預算數{xb}與總預算舉借預算數{jb:,.1f}不同，含特別預算，X 決算未自動計算")
for f in sorted(glob.glob("opendata/nta/D3-16F_*.csv")):
    ym = os.path.basename(f)[7:-4]
    if not ym.endswith("12"): continue
    y = int(ym[:-2])
    for line in open(f, encoding="utf-8-sig").read().splitlines()[1:]:
        c = line.split(",")
        if len(c) > 3 and c[2] == "中央":
            R.setdefault("W", {})[y] = {"value": round(float(c[3])), "basis": "決算（國庫署年底實際數）", "unit": "億元", "source": "https://data.gov.tw/dataset/30955", "detail": f"{y}年12月底中央當年度實際舉債數{float(c[3]):,.1f}億元"}
# ---- 主計總處新聞稿附表：D/E/F/H（年資料＋預測）、J/L（年平均）、J/K/L/M（本年累計）----
f = "opendata/dgbas/latest.json"
if os.path.exists(f):
    G = json.load(open(f, encoding="utf-8")); fc = G.get("forecast", {}); wg = G.get("wages", {})
    src = fc.get("pdf") or fc.get("source", "")
    for ys, a in (fc.get("annual") or {}).items():
        y = int(ys); flag = a.get("flag", "")
        basis = "預測值" if flag == "f" else ("初步統計" if flag == "p" else "主計總處統計")
        for col, k in (("D", "growth"), ("E", "cpi"), ("F", "gdp_usd"), ("H", "gdp_twd")):
            R.setdefault("DG_" + col, {})[y] = {"value": a[k], "basis": basis, "source": src, "detail": f"重要經濟指標表 {y}年{'('+flag+')' if flag else ''}"}
    wsrc = wg.get("source", "")
    for ys, a in (wg.get("annual") or {}).items():
        R.setdefault("DG_L", {})[int(ys)] = {"value": a["regular"], "basis": "年平均", "source": wsrc, "detail": "薪資新聞稿表1"}
    for ys, v in (wg.get("annual_total") or {}).items():
        R.setdefault("DG_J", {})[int(ys)] = {"value": v, "basis": "年平均", "source": wsrc, "detail": "薪資新聞稿表2 年累計÷12"}
    yt = wg.get("ytd"); tt = wg.get("ytd_total")
    if yt:
        y, m = yt["year"], yt["to_month"]
        R.setdefault("DG_L", {})[y] = {"value": yt["regular"], "basis": "累計平均", "ym": [y, m], "source": wsrc, "detail": f"表1 {y}年1至{m}月"}
        R.setdefault("DG_M", {})[y] = {"value": yt["regular_yoy"], "basis": "累計年增率", "ym": [y, m], "source": wsrc, "detail": f"表1 {y}年1至{m}月"}
    if tt:
        y, m = tt["year"], tt["to_month"]
        R.setdefault("DG_J", {})[y] = {"value": tt["avg"], "basis": "累計平均", "ym": [y, m], "source": wsrc, "detail": (f"表2 {y}年累計{tt['cum']:,}÷{m}" if tt.get('prev_cum') else f"新聞稿：{tt.get('text','')}")}
        R.setdefault("DG_K", {})[y] = {"value": tt["yoy"], "basis": "累計年增率", "ym": [y, m], "source": wsrc, "detail": (f"表2 {y}年累計{tt['cum']:,}／{y-1}年同期{tt['prev_cum']:,}" if tt.get('prev_cum') else f"新聞稿：{tt.get('text','')}")}
json.dump(R, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print({k: (len(v) if isinstance(v, dict) else v) for k, v in R.items()})
