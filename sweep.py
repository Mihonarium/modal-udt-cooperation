"""Random-game sweep: how often do modal UDT pairings land on Pareto / Nash / exploited outcomes."""
import json, random
from modal import *
from run import rand_game, analysis, label

def variants(an):
    fb = lambda g, role: an["maxmin_act"][role]
    rev = lambda n: list(range(n))[::-1]
    return {"UDT": ModalUDT("UDT", default=fb),
            "UDT-exact": ModalUDT("UDT-exact", default=fb, exact=True),
            "UDT-exact-def0": ModalUDT("UDT-exact-def0", default=0, exact=True),
            "UDT-exact-deflast": ModalUDT("UDT-exact-deflast", default=lambda g, r: g.n(r) - 1, exact=True),
            "UDT-revorder": ModalUDT("UDT-revorder", default=fb, action_order=rev),
            "UDT-chicken": ModalUDT("UDT-chicken", default=fb, chicken=True),
            "UDT-strat": ModalUDT("UDT-strat", default=fb, strat=True),
            "FB": FairBot(), "PB": PrudentBot()}

PAIRS = [("UDT", "UDT"), ("UDT-exact", "UDT-exact"), ("UDT-exact-def0", "UDT-exact-def0"),
         ("UDT-exact-deflast", "UDT-exact-deflast"), ("UDT-strat", "UDT-strat"), ("UDT-chicken", "UDT-chicken"),
         ("UDT", "UDT-revorder"), ("UDT", "UDT-exact"), ("UDT", "UDT-strat"), ("UDT", "FB"), ("FB", "UDT"),
         ("UDT", "PB"), ("FB", "FB"), ("PB", "PB")]
stats = {p: {"n": 0, "Pareto": 0, "Nash": 0, "max-sum": 0, "row-exploited": 0, "col-exploited": 0,
             "best_for_both_missed": 0} for p in PAIRS}
maxstab = 0
for n in (2, 3):
    for seed in range(1000, 1300):
        g = rand_game(f"r{n}-{seed}", n, seed)
        an = analysis(g); ctx = Ctx(g, an["target"], an["maxmin_act"])
        V = variants(an)
        # does a single outcome weakly beat every other for both players?
        outs = list(g.U)
        top = [o for o in outs if all(g.U[o][k] >= g.U[p][k] for p in outs for k in (0, 1))]
        for (a, b) in PAIRS:
            r, c, s = play(g, V[a], V[b], ctx, N=120)
            maxstab = max(maxstab, s)
            t = label(g, an, (r, c)); st = stats[(a, b)]; st["n"] += 1
            for k in ("Pareto", "Nash", "max-sum", "row-exploited", "col-exploited"):
                st[k] += k in t
            st["best_for_both_missed"] += bool(top) and (r, c) not in top and g.U[(r, c)] != g.U[top[0]]
        stats.setdefault("_games_with_top", {"n": 0}); stats["_games_with_top"]["n"] += bool(top)
print("max stabilisation level:", maxstab)
print(f"{'pair':28s} {'n':>4} {'Pareto':>7} {'Nash':>6} {'maxsum':>7} {'rowExpl':>8} {'colExpl':>8} {'missTop':>8}")
for p in PAIRS:
    s = stats[p]
    print(f"{p[0]+' vs '+p[1]:28s} {s['n']:4d} {s['Pareto']:7d} {s['Nash']:6d} {s['max-sum']:7d} {s['row-exploited']:8d} {s['col-exploited']:8d} {s['best_for_both_missed']:8d}")
print("games with an outcome best for both players:", stats["_games_with_top"]["n"])
json.dump({" vs ".join(k) if isinstance(k, tuple) else k: v for k, v in stats.items()}, open("sweep.json", "w"), indent=1)
