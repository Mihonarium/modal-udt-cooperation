"""V4 tournament on named games and the 600 random games."""
import json
from modal import *
from v3 import V3
from v4 import V4
from run import GAMES, G, analysis, rand_game

SUBS = {"V4": dict(), "V4-gated": dict(gate=True), "V4-probe2": dict(probe=2), "V4-exploitlast": dict(order="coop-neutral-exploit")}
PDS = [G(f"PD{T}/{R}/{P}/{S}", (["C","D"],)*2, [[(R,R),(S,T)],[(T,S),(P,P)]])
       for (T,R,P,S) in [(3,2,1,0),(5,3,1,0),(4,3,2,1),(10,3,1,0),(3,2,0,-1),(101,100,1,0)]]

def opponents(g, an, X, Xr):
    o = {"self": X, "rev-copy": Xr, "UDT": ModalUDT("UDT", default=lambda gg, r: an["maxmin_act"][r]),
         "V3-B": V3("V3-B", order="exploit-last"), "FB": FairBot(), "PB": PrudentBot()}
    return o

def match(g, an, ctx, X, Y, seat, top):
    A, B = (X, Y) if seat == 0 else (Y, X)
    r, c, s = play(g, A, B, ctx, N=120)
    return dict(outcome=f"{g.acts[0][r]},{g.acts[1][c]}", payoff=list(g.U[(r, c)]), stab=s,
                below=g.U[(r, c)][seat] < an["maxmin_val"][seat], pareto=(r, c) in an["pareto"],
                miss=bool(top) and g.U[(r, c)] != g.U[top[0]])

def setup(g):
    an = analysis(g)
    if g.name.startswith("PD"): an["target"], an["maxmin_act"] = (0, 0), (1, 1)
    outs = list(g.U); top = [o for o in outs if all(g.U[o][k] >= g.U[p][k] for p in outs for k in (0, 1))]
    return an, Ctx(g, an["target"], an["maxmin_act"]), top

named, lines = [], []
for g in PDS + GAMES[1:]:
    an, ctx, top = setup(g)
    for s, kw in SUBS.items():
        X, Xr = V4(s, **kw), V4(s + "-rev", rev=True, **kw)
        cells = []
        for on, Y in opponents(g, an, X, Xr).items():
            res = [match(g, an, ctx, X, Y, seat, top) for seat in ((0,) if on == "self" else (0, 1))]
            named += [dict(game=g.name, sub=s, opp=on, seat=i, **r) for i, r in enumerate(res)]
            cells.append("/".join(r["outcome"] + ("!" if r["below"] else "") for r in res))
        for a in range(g.n(1)):
            r = match(g, an, ctx, X, Const(a, f"Const{a}"), 0, top)
            named.append(dict(game=g.name, sub=s, opp=f"Const[{g.acts[1][a]}]", seat=0, **r))
            cells.append(f"{g.acts[1][a]}:{r['outcome']}" + ("!" if r["below"] else ""))
        lines.append(f"| {g.name} | {s} | " + " | ".join(cells) + " |")
hdr = "| game | sub | self | rev-copy | UDT | V3-B | FB | PB | vs each constant bot |"
open("v4_tables.txt", "w").write(hdr + "\n" + "\n".join(lines) + "\n")
print(hdr); print("\n".join(l for l in lines if "| V4 |" in l))

stats = {}; ntop = 0
for n in (2, 3):
    for seed in range(1000, 1300):
        g = rand_game(f"r{n}-{seed}", n, seed); an, ctx, top = setup(g); ntop += bool(top)
        for s, kw in SUBS.items():
            X, Xr = V4(s, **kw), V4(s + "-rev", rev=True, **kw)
            opps = opponents(g, an, X, Xr)
            for a in range(g.n(1 - 0)): opps[f"Const{a}"] = Const(a, f"Const{a}")
            for on, Y in opps.items():
                seats = (0,) if on == "self" else ((0,) if on.startswith("Const") and g.n(0) != g.n(1) else (0, 1))
                for seat in seats:
                    r = match(g, an, ctx, X, Y, seat, top)
                    key = (s, "const" if on.startswith("Const") else on)
                    d = stats.setdefault(key, dict(n=0, pareto=0, below=0, miss=0))
                    d["n"] += 1; d["pareto"] += r["pareto"]; d["below"] += r["below"]; d["miss"] += r["miss"]
out = ["games with an outcome best for both: %d of 600" % ntop,
       f"{'sub':15s} {'opp':9s} {'n':>5} {'Pareto':>7} {'below own maxmin':>17} {'miss both-best':>15}"]
for (s, o), d in stats.items():
    out.append(f"{s:15s} {o:9s} {d['n']:5d} {d['pareto']:7d} {d['below']:17d} {d['miss']:15d}")
open("sweep_v4.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))
print("max stab", max(r["stab"] for r in named), "named below-maxmin:", sum(r["below"] for r in named))
json.dump(named, open("v4_results.json", "w"), indent=1)
