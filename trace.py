import sys
from modal import *
from run import rand_game, analysis, GAMES

def show(g, X, Y, ctx, L=12):
    seq, s = play(g, X, Y, ctx, N=60, trace=True)
    print(f"{g.name}: {X.name} (row) vs {Y.name} (col), by level:",
          " ".join(f"{n}:{g.acts[0][a]},{g.acts[1][b]}" for n, (a, b) in enumerate(seq[:L])), f"| stable from {s}")

def misses(limit=3):
    found = 0
    for n in (2, 3):
        for seed in range(1000, 1300):
            g = rand_game(f"r{n}-{seed}", n, seed); an = analysis(g)
            outs = list(g.U)
            top = [o for o in outs if all(g.U[o][k] >= g.U[p][k] for p in outs for k in (0, 1))]
            if not top: continue
            ctx = Ctx(g, an["target"], an["maxmin_act"])
            U = ModalUDT("UDT", default=lambda gg, r: an["maxmin_act"][r])
            r, c, s = play(g, U, U, ctx)
            if g.U[(r, c)] != g.U[top[0]]:
                print(g.name, {f"{g.acts[0][i]},{g.acts[1][j]}": g.U[(i, j)] for (i, j) in g.U}, "top", top)
                show(g, U, U, ctx); found += 1
                if found >= limit: return

if __name__ == "__main__":
    misses()
    G = {g.name: g for g in GAMES}
    for gn, a, b in [("PD", "UDT", "FB"), ("PD", "UDT", "UDT"), ("PD", "UDT", "UDT-revorder"), ("PD", "UDT-exact", "UDT-revorder"),
                     ("CoordRanked", "UDT", "UDT-revorder"), ("BoS", "UDT", "UDT")]:
        g = G[gn]; an = analysis(g); ctx = Ctx(g, an["target"], an["maxmin_act"])
        fb = lambda gg, r: an["maxmin_act"][r]
        mk = {"UDT": ModalUDT("UDT", default=fb), "UDT-exact": ModalUDT("UDT-exact", default=fb, exact=True),
              "UDT-revorder": ModalUDT("UDT-revorder", default=fb, action_order=lambda n: list(range(n))[::-1]),
              "FB": FairBot()}
        X = mk[a]; Y = mk[b] if b != a else X
        show(g, X, Y, ctx)
