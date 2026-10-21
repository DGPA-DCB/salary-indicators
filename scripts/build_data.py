"""由儀表板資料庫匯出檔產生公開網站用的 data.json（去除內部註記）。
用法：python3 scripts/build_data.py <匯出目錄> <輸出 data.json> [查核日期YYYY-MM-DD]
<匯出目錄> 內含 indicators/*.json 與 table/*.json（ArtifactData list 的 out_dir 輸出）。"""
import json, glob, os, re, sys, datetime

src, out = sys.argv[1], sys.argv[2]
last_check = sys.argv[3] if len(sys.argv) > 3 else None

def load(p):
    d = json.load(open(p, encoding="utf-8"))
    return d.get("data", d) if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict) else d

INTERNAL = re.compile(r"原值|原表|表內")
def clean(t):
    t = re.sub(r"^原值：[^\n]*\n?", "", t or "")
    parts = re.split(r"(?<=。)", t)
    return "".join(p for p in parts if not INTERNAL.search(p)).strip()

inds = []
for f in glob.glob(os.path.join(src, "indicators", "*.json")):
    d = load(f); d["id"] = os.path.basename(f)[:-5]
    d.pop("updatedBy", None)
    if INTERNAL.search(d.get("note") or ""):
        d["note"] = clean(d["note"])
    inds.append(d)
inds.sort(key=lambda d: d.get("order", 0))

rows, notes = [], {"lines": [], "todo": []}
for f in glob.glob(os.path.join(src, "table", "*.json")):
    d = load(f)
    if os.path.basename(f) == "notes.json":
        notes = {"lines": d.get("lines", []), "todo": []}   # 待確認事項屬內部資料，不公開
        continue
    if not isinstance(d.get("year"), int):
        continue
    d["comments"] = {k: clean(v) for k, v in (d.get("comments") or {}).items() if clean(v)}
    for h in d.get("hist") or []:
        h["note"] = clean(h.get("note") or "")
    rows.append(d)
rows.sort(key=lambda d: d["year"])

asof = max([d.get("updatedAt", "")[:10] for d in inds if d.get("updatedAt")] or [datetime.date.today().isoformat()])
data = {"asof": asof, "lastCheck": last_check, "indicators": inds, "rows": rows, "notes": notes}
json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"wrote {out}: {len(inds)} indicators, {len(rows)} rows, asof {asof}")
