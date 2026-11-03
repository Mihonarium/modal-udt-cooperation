from modal import *
from v3 import V3
from run import rand_game, analysis, label
subs = {"V3-A": dict(xform="PA+1"), "V3-B": dict(order="exploit-last"), "V3-C": dict(xform="conPA"), "V3-D": dict(xform="conPA1")}
st = {}; ntop = 0; exploit_dead = 0
for n in (2, 3):
    for seed in range(1000, 1300):
        g = rand_game(f"r{n}-{seed}", n, seed); an = analysis(g); ctx = Ctx(g, an["target"], an["maxmin_act"])
        outs = list(g.U); top = [o for o in outs if all(g.U[o][k] >= g.U[p][k] for p in outs for k in (0, 1))]
        ntop += bool(top)
        U0 = ModalUDT("UDT", default=lambda gg, r: an["maxmin_act"][r])
        for s, kw in subs.items():
            X = V3(s, **kw); Xr = V3(s + "r", rev=True, **kw)
            for oname, Y in (("self", X), ("revcopy", Xr), ("UDT", U0), ("FB", FairBot()), ("PB", PrudentBot())):
                for seat in ((0,) if oname == "self" else (0, 1)):
                    A, B = (X, Y) if seat == 0 else (Y, X)
                    r, c, _ = play(g, A, B, ctx, N=120)
                    d = st.setdefault((s, oname), dict(n=0, pareto=0, sucker=0, miss=0))
                    d["n"] += 1; d["pareto"] += (r, c) in an["pareto"]
                    d["sucker"] += g.U[(r, c)][seat] < an["maxmin_val"][seat]
                    d["miss"] += bool(top) and g.U[(r, c)] != g.U[top[0]]
print("games with a both-best outcome:", ntop, "(of 600)")
print(f"{'sub':6s} {'opp':8s} {'n':>5} {'Pareto':>7} {'V3 below maxmin':>16} {'miss both-best':>15}")
for (s, o), d in st.items():
    print(f"{s:6s} {o:8s} {d['n']:5d} {d['pareto']:7d} {d['sucker']:16d} {d['miss']:15d}")
