"""比對 parse_raw.py 結果與彙整表現值，產出差異清單與可直接送 ArtifactData batch 的寫入檔。
用法：python3 scripts/compare_raw.py <parsed.json> <table匯出資料夾> <out_dir> <今天YYYY-MM-DD>
規則：
- 已有決算數採決算數：P/S/T/V/Q 之決算值若與表值不同 → 改為決算值（kind rev，紅字）。
- 預算數（W–Z 及 P/Q 的預算案）只在該年尚無決算值且表值不同時更新；有決算者不以預算數覆蓋。
- 表值文字含「預測」「未查證」且新值為官方數 → 改黑字（kind ver）。
- 數值相同只補註解（不改 red/hist）。"""
import json, os, sys, glob, re
parsed, exp, out, today = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
P = json.load(open(parsed, encoding="utf-8"))
COLS = {"P": "P", "Q_audit": "Q", "S": "S", "T": "T", "V": "V", "W": "W", "X": "X", "Y": "Y", "Z": "Z"}
NAME = {"P": "人事費占歲出比率-中央", "Q": "人事費占歲出比率-地方", "S": "餘絀-中央政府總預算", "T": "餘絀-各級政府", "V": "餘絀占GDP比率", "W": "中央政府債務舉借(含不列債限)", "X": "列入債限", "Y": "歲出(列入債限部分)", "Z": "列入債限占歲出比率"}
def tv(v):
    if v is None: return None
    s = str(v).replace(",", "").split("\n")[0].strip()
    try: return float(s)
    except: return None
def same(a, b, col=None):
    if a is None or b is None: return False
    if col == "Z" and abs(round(a, 1) - round(b, 1)) <= 0.051 and abs(a - b) < 0.1: return True  # 比率欄原表取1位小數
    return abs(a - b) <= (0.005 if abs(b) < 100 else 1.0)
writes, diffs = [], []
docs = {}
for f in glob.glob(os.path.join(exp, "table", "y*.json")):
    w = json.load(open(f, encoding="utf-8")); d = w.get("data", w); docs[d["year"]] = (d, w.get("version"), f)
for key, col in COLS.items():
    for ys, e in (P.get(key) or {}).items():
        y = int(ys)
        if y not in docs: continue
        d, ver, f = docs[y]; cur = d["cells"].get(col); curv = tv(cur); new = e["value"]; basis = e.get("basis", "")
        is_final = "決算" in basis
        txt = str(cur) if cur is not None else ""
        if same(curv, new, col):
            note = f"已核對（自動）：{basis}{new}，與表值相符。{e.get('detail','')} 來源：{e.get('source','')}"
            d.setdefault("comments", {}).setdefault(col, "")
            if "已核對（自動）" not in d["comments"][col]:
                d["comments"][col] = (d["comments"][col] + "\n" if d["comments"][col] else "") + note; d["_changed"] = True
            diffs.append({"year": y, "col": col, "table": cur, "new": new, "basis": basis, "result": "相符"}); continue
        if e.get("truncated"):  # 報告以「億餘元」表述，尾數捨去；差1以內視為相符
            if curv is not None and abs(curv - new) <= 1: diffs.append({"year": y, "col": col, "table": cur, "new": new, "basis": basis, "result": "相符（億餘元）"}); continue
        if col in "WXYZ":
            # 115.10.30 決定：W–Z 一律預算數（國庫署），表頭註明，不於儲存格加註；數字不同即更新（黑字）
            newcell = int(new) if col != "Z" else new
            if same(curv, new, col):
                diffs.append({"year": y, "col": col, "table": cur, "new": new, "basis": basis, "result": "相符"}); continue
            note = f"依國庫署「中央政府各年度債務舉借概況」預算數更新：{NAME[col]} {y}年 {new}。{e.get('detail','')} 來源：{e.get('source','')}"
            d["cells"][col] = newcell; d.setdefault("red", {}).pop(col, None)
            d.setdefault("comments", {})[col] = f"原值：{cur}\n" + note
            d.setdefault("hist", []).append({"d": today, "col": col, "old": cur, "new": newcell, "kind": "ver", "note": note}); d["_changed"] = True
            diffs.append({"year": y, "col": col, "table": cur, "new": newcell, "basis": basis, "result": "更新"}); continue
        if not is_final:
            if col in "WXYZ" and y >= 115:
                diffs.append({"year": y, "col": col, "table": cur, "new": new, "basis": basis, "result": "當年度以後之預算數（可能含追加預算案），待承辦人確認後再寫入"}); continue
            # 預算案數不覆蓋法定預算；預算數僅在表值為空、預測、未查證或同為預算數時更新
            if "預算案" in basis and "法定" in txt:
                diffs.append({"year": y, "col": col, "table": cur, "new": new, "basis": basis, "result": "表為法定預算，預算案數不覆蓋"}); continue
            if cur is not None and not re.search(r"預測|預算|未查證|資料不足", txt): 
                diffs.append({"year": y, "col": col, "table": cur, "new": new, "basis": basis, "result": "不同口徑，未更新（表為決算？）"}); continue
        newcell = new if is_final else f"{new:,.2f}\n(預算數)" if isinstance(new, float) and col in "WXYZ" and not float(new).is_integer() else (f"{int(new):,}\n(預算數)" if not is_final else new)
        if is_final and isinstance(new, float) and new.is_integer() and col in "STWXY": newcell = int(new)
        kind = "ver" if re.search(r"預測|未查證|資料不足|預算", txt) else "rev"
        note = f"依自動下載之官方資料更新：{NAME[col]} {y}年 {basis} {new}。{e.get('detail','')} 來源：{e.get('source','')}"
        d["cells"][col] = newcell
        if kind == "rev": d.setdefault("red", {})[col] = today
        else: d.setdefault("red", {}).pop(col, None)
        d.setdefault("comments", {})[col] = f"原值：{cur}\n" + note
        d.setdefault("hist", []).append({"d": today, "col": col, "old": cur, "new": newcell, "kind": kind, "note": note})
        d["_changed"] = True
        diffs.append({"year": y, "col": col, "table": cur, "new": newcell, "basis": basis, "result": "更新"})
# ---- 主計總處：D/E/F/H/J/K/L/M ----
DGN = {"D": "經濟成長率", "E": "CPI年增率", "F": "每人GDP(美元)", "H": "每人GDP(元)", "J": "總薪資", "K": "總薪資年增率", "L": "經常性薪資", "M": "經常性薪資年增率"}
def fmt(col, v):
    return f"{int(v):,}" if col in "FHJL" else f"{v:.2f}"
for col in "DEFHJKLM":
    for ys, e in (P.get("DG_" + col) or {}).items():
        y = int(ys)
        if y not in docs: continue
        d, ver, f = docs[y]; cur = d["cells"].get(col); new = e["value"]; basis = e["basis"]
        if isinstance(cur, dict): continue  # 自動計算欄（K/M 年增率）不覆蓋
        txt = str(cur) if cur is not None else ""; curv = tv(cur)
        if basis in ("累計平均", "累計年增率"):
            yy, m = e["ym"]
            newcell = f"{fmt(col,new)}\n({yy}年1月-{m}月平均)" if basis == "累計平均" else f"{fmt(col,new)}\n({yy}年1-{m}月與上年同期比較)"
            if re.search(r"年平均|預測", txt) and not re.search(r"1月-|1-\d+月", txt): 
                diffs.append({"year": y, "col": col, "table": cur, "new": newcell, "basis": basis, "result": "表為年值，累計數不覆蓋"}); continue
            kind = "ver"
        elif basis == "預測值":
            if cur is not None and not re.search(r"預測", txt):
                diffs.append({"year": y, "col": col, "table": cur, "new": new, "basis": basis, "result": "表非預測值，不以預測覆蓋"}); continue
            rest = txt.split("\n", 1)[1] if "\n" in txt else "(預測值)"
            newcell = f"{fmt(col,new)}\n{rest}"; kind = "fc"
        else:  # 年資料（統計值）
            newcell = int(new) if col in "FHJL" else new; kind = "rev" if cur is not None and not re.search(r"預測|未查證|預估", txt) else "ver"
        if same(curv, new):
            if (basis in ("累計平均", "累計年增率")) and not re.search(rf"1月-{e['ym'][1]}月|1-{e['ym'][1]}月", txt):
                pass  # 同值但期間不同（罕見），照常更新
            else:
                note = f"已核對（自動）：主計總處{basis}{fmt(col,new)}，與表值相符。{e.get('detail','')} 來源：{e.get('source','')}"
                d.setdefault("comments", {}).setdefault(col, "")
                if "已核對（自動）" not in d["comments"][col]:
                    d["comments"][col] = (d["comments"][col] + "\n" if d["comments"][col] else "") + note; d["_changed"] = True
                diffs.append({"year": y, "col": col, "table": cur, "new": new, "basis": basis, "result": "相符"}); continue
        note = f"依主計總處新聞稿附表更新：{DGN[col]} {y}年 {basis} {fmt(col,new)}。{e.get('detail','')} 來源：{e.get('source','')}"
        d["cells"][col] = newcell
        if kind == "rev": d.setdefault("red", {})[col] = today
        else: d.setdefault("red", {}).pop(col, None)
        d.setdefault("comments", {})[col] = f"原值：{cur}\n" + note
        d.setdefault("hist", []).append({"d": today, "col": col, "old": cur, "new": newcell, "kind": kind, "note": note})
        d["_changed"] = True
        diffs.append({"year": y, "col": col, "table": cur, "new": newcell, "basis": basis, "result": "更新"})
for y, (d, ver, f) in docs.items():
    if d.pop("_changed", False):
        p = os.path.join(out, f"y{y:03d}.json"); json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
        writes.append({"op": "set", "collection": "table", "doc_id": f"y{y:03d}", "if_version": ver, "file_path": os.path.abspath(p)})
json.dump(writes, open(os.path.join(out, "writes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(diffs, open(os.path.join(out, "diffs.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
upd = [x for x in diffs if x["result"] == "更新"]
print(f"比對 {len(diffs)} 格：更新 {len(upd)}，相符 {sum(1 for x in diffs if x['result']=='相符')}，其他 {len(diffs)-len(upd)-sum(1 for x in diffs if x['result']=='相符')}")
for x in upd: print(" ", x)
