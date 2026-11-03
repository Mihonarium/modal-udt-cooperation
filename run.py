"""Self-play and cross-play of modal UDT variants against FB, PB, constant bots, on several games."""
import json, random, sys
from modal import *

def G(name, acts, rows):
    U = {(i, j): rows[i][j] for i in range(len(acts[0])) for j in range(len(acts[1]))}
    return Game(name, acts, U)

def rand_game(name, n, seed):
    rng = random.Random(seed)
    acts = ([f"r{i}" for i in range(n)], [f"c{j}" for j in range(n)])
    rows = [[(rng.randint(0, 9), rng.randint(0, 9)) for j in range(n)] for i in range(n)]
    return G(name, acts, rows)

GAMES = [
    G("PD", (["C", "D"],) * 2, [[(2, 2), (0, 3)], [(3, 0), (1, 1)]]),
    G("StagHunt", (["S", "H"],) * 2, [[(4, 4), (0, 3)], [(3, 0), (3, 3)]]),
    G("Chicken", (["Sw", "St"],) * 2, [[(3, 3), (1, 4)], [(4, 1), (0, 0)]]),
    G("BoS", (["A", "B"],) * 2, [[(2, 1), (0, 0)], [(0, 0), (1, 2)]]),
    G("Coord", (["A", "B"],) * 2, [[(1, 1), (0, 0)], [(0, 0), (1, 1)]]),
    G("CoordRanked", (["A", "B"],) * 2, [[(2, 2), (0, 0)], [(0, 0), (1, 1)]]),
    rand_game("Rand2x2-s1", 2, 1), rand_game("Rand2x2-s2", 2, 2),
    rand_game("Rand3x3-s3", 3, 3), rand_game("Rand3x3-s4", 3, 4),
]

def analysis(g):
    R, Cn = range(g.n(0)), range(g.n(1))
    outs = [(i, j) for i in R for j in Cn]
    U = g.U
    pareto = {o for o in outs if not any(all(U[p][k] >= U[o][k] for k in (0, 1)) and U[p] != U[o] for p in outs)}
    nash = {(i, j) for (i, j) in outs if U[(i, j)][0] == max(U[(a, j)][0] for a in R)
            and U[(i, j)][1] == max(U[(i, b)][1] for b in Cn)}
    maxmin_val = (max(min(U[(i, j)][0] for j in Cn) for i in R), max(min(U[(i, j)][1] for i in R) for j in Cn))
    maxmin_act = (max(R, key=lambda i: (min(U[(i, j)][0] for j in Cn), -i)),
                  max(Cn, key=lambda j: (min(U[(i, j)][1] for i in R), -j)))
    target = max(outs, key=lambda o: (U[o][0] + U[o][1], -outs.index(o)))
    return dict(pareto=pareto, nash=nash, maxmin_val=maxmin_val, maxmin_act=maxmin_act, target=target)

def label(g, an, o):
    U = g.U[o]
    tags = []
    if o in an["pareto"]: tags.append("Pareto")
    else: tags.append("dominated")
    if o in an["nash"]: tags.append("Nash")
    if o == an["target"]: tags.append("max-sum")
    for k, who in ((0, "row"), (1, "col")):
        if U[k] < an["maxmin_val"][k]: tags.append(f"{who}-exploited")
    return tags

def udt_variants(an):
    fb = lambda g, role: an["maxmin_act"][role]
    rev = lambda n: list(range(n))[::-1]
    return [
        ModalUDT("UDT", default=fb),                         # Kelvin's: >=u, util-major, PA, maxmin default
        ModalUDT("UDT-exact", default=fb, exact=True),       # Fallenstein: "implies outcome == u"
        ModalUDT("UDT-revorder", default=fb, action_order=rev),
        ModalUDT("UDT-actmajor", default=fb, order="action-major"),
        ModalUDT("UDT-chicken", default=fb, chicken=True),
        ModalUDT("UDT-strat", default=fb, strat=True),
    ] + [ModalUDT(f"UDT-def{a}", default=a) for a in range(max(g_n for g_n in an["sizes"]))]

def main(N=80):
    results = []
    for g in GAMES:
        an = analysis(g)
        an["sizes"] = (g.n(0), g.n(1))
        ctx = Ctx(g, coop_target=an["target"], fallback=an["maxmin_act"])
        udts = udt_variants(an)
        others = [FairBot(), PrudentBot()]
        consts = {}
        # constant bots per role are just Const(a); name CB = plays its part of target, DB = its fallback
        def const_agents(role):
            out = []
            for a in range(g.n(role)):
                nm = f"Const[{g.acts[role][a]}]"
                if a == an["target"][role]: nm += "=CB"
                if a == an["maxmin_act"][role]: nm += "=DB"
                out.append(Const(a, nm))
            return out
        ctx.consts = {}
        pool_row = udts + others + const_agents(0)
        pool_col = udts + others + const_agents(1)
        for X in pool_row:
            for Y in pool_col:
                if not (X in udts or Y in udts):
                    if not (isinstance(X, (FairBot, PrudentBot)) and isinstance(Y, (FairBot, PrudentBot))):
                        continue
                # helper constant bots in ctx (for PB's probe) must not collide with names
                if (g.n(0), g.n(1)) != (2, 2) and isinstance(Y, Const) and Y.a >= g.n(1): continue
                r, c, s = play(g, X, Y, ctx, N=N)
                o = (r, c)
                results.append(dict(game=g.name, row=X.name, col=Y.name,
                                    outcome=f"{g.acts[0][r]},{g.acts[1][c]}", payoff=list(g.U[o]),
                                    tags=label(g, an, o), stab=s))
        an_s = {k: (sorted(v) if isinstance(v, set) else v) for k, v in an.items()}
        results.append(dict(game=g.name, analysis={k: str(v) for k, v in an_s.items()},
                            matrix={f"{g.acts[0][i]},{g.acts[1][j]}": g.U[(i, j)] for (i, j) in g.U}))
    json.dump(results, open("results.json", "w"), indent=1)
    return results

if __name__ == "__main__":
    res = main()
    print(len(res), "records; max stabilisation level", max(r.get("stab", 0) for r in res))
