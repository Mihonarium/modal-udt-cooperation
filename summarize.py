import json, sys
R = json.load(open("results.json"))
games = [r["game"] for r in R if "analysis" in r]
out = []
for g in games:
    meta = next(r for r in R if r.get("game") == g and "analysis" in r)
    recs = [r for r in R if r["game"] == g and "row" in r]
    out.append(f"\n### {g}\nmatrix (row,col payoffs): " + "; ".join(f"{k}:{tuple(v)}" for k, v in meta["matrix"].items()))
    out.append("Nash: %s; max-sum target (FB/PB): %s; maxmin action (FB/PB/UDT fallback): %s" % (meta["analysis"]["nash"], meta["analysis"]["target"], meta["analysis"]["maxmin_act"]))
    out.append("\n| row \\ col | outcome (payoffs) [tags] |\n|---|---|")
    for r in recs:
        out.append(f"| {r['row']} vs {r['col']} | {r['outcome']} {tuple(r['payoff'])} [{', '.join(r['tags'])}] |")
open("tables.md", "w").write("\n".join(out))
