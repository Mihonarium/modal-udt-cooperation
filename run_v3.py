import json, sys
from modal import *
from v3 import V3
from run import GAMES, G, analysis, label, rand_game
SUBS = [("V3-A", dict(xform="PA+1", order="interleave")),     # literal spec
        ("V3-B", dict(xform="PA+1", order="exploit-last")),
        ("V3-C", dict(xform="conPA", order="interleave")),
        ("V3-D", dict(xform="conPA1", order="interleave"))]
PDS = [G(f"PD{T}/{R}/{P}/{S}", (["C","D"],)*2, [[(R,R),(S,T)],[(T,S),(P,P)]])
       for (T,R,P,S) in [(3,2,1,0),(5,3,1,0),(4,3,2,1),(10,3,1,0),(3,2,0,-1),(101,100,1,0)]]
def pool(g, an):
    fb = lambda gg, r: an["maxmin_act"][r]
    return {"UDT": ModalUDT("UDT", default=fb), "FB": FairBot(), "PB": PrudentBot()}
def const_name(g, an, role, a):
    nm = f"Const[{g.acts[role][a]}]"
    if a == an["target"][role]: nm += "=CB"
    if a == an["maxmin_act"][role]: nm += "=DB"
    return nm
def tourney(games, out):
    for g in games:
        an = analysis(g)
        if g.name.startswith("PD"): an["target"], an["maxmin_act"] = (0, 0), (1, 1)   # FB/PB use C,C and D in every PD
        ctx = Ctx(g, an["target"], an["maxmin_act"])
        for sname, kw in SUBS:
            X = V3(sname, **kw); Xr = V3(sname + "-rev", rev=True, **kw)
            opps = dict(pool(g, an)); opps["self"] = X; opps["rev-copy"] = Xr
            for r in range(g.n(1)): opps[const_name(g, an, 1, r)] = Const(r, const_name(g, an, 1, r))
            for oname, Y in opps.items():
                for seat in (0, 1):
                    if seat == 1 and (oname == "self" or oname.startswith("Const")): continue
                    if seat == 1 and isinstance(Y, Const): continue
                    A, B = (X, Y) if seat == 0 else (Y, X)
                    r, c, s = play(g, A, B, ctx, N=120)
                    me = (r, c)[seat]; mine = g.U[(r, c)][seat]
                    out.append(dict(game=g.name, sub=sname, opp=oname, seat=seat, outcome=f"{g.acts[0][r]},{g.acts[1][c]}",
                                    payoff=list(g.U[(r, c)]), mine=mine, tags=label(g, an, (r, c)), stab=s,
                                    below_maxmin=mine < an["maxmin_val"][seat]))
out = []
tourney(PDS + GAMES[1:], out)
json.dump(out, open("v3_results.json", "w"), indent=1)
# compact table: per game x opponent, row seat (and col seat in brackets if different)
for sname, _ in SUBS:
    print("\n##", sname)
    games = []
    for r in out:
        if r["game"] not in games: games.append(r["game"])
    opps = []
    for r in out:
        if r["opp"] not in opps and not r["opp"].startswith("Const"): opps.append(r["opp"])
    print("| game | " + " | ".join(opps) + " | vs DB | vs CB |"); print("|---" * (len(opps) + 3) + "|")
    for gname in games:
        cells = []
        R = [r for r in out if r["game"] == gname and r["sub"] == sname]
        for o in opps:
            a = [r for r in R if r["opp"] == o]
            s = "/".join(f"{r['outcome']}" for r in a)
            if any(r["below_maxmin"] for r in a): s += " !SUCKER"
            cells.append(s)
        for tag in ("=DB", "=CB"):
            a = [r for r in R if r["opp"].startswith("Const") and tag in r["opp"]]
            cells.append(" ".join(r["outcome"] + (" !SUCKER" if r["below_maxmin"] else "") for r in a))
        print(f"| {gname} | " + " | ".join(cells) + " |")
print("\nmax stab", max(r["stab"] for r in out), "; any V3 below own maxmin:", sum(r["below_maxmin"] for r in out))
