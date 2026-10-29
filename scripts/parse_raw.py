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
        R["S"][y] = {"value": v, "basis": "決算審定", "source": f, "detail": m.group(0)[:60]}
# ---- T/V：財政統計年報（若已下載並解析）----
for f in glob.glob("opendata/fiscal/yearbook_table1-1*.json"):
    R.update(json.load(open(f, encoding="utf-8")))
json.dump(R, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print({k: (len(v) if isinstance(v, dict) else v) for k, v in R.items()})
