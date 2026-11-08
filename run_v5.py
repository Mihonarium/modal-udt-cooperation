"""V5 tournament: named games and random games, against copies, FairBot/PrudentBot aimed at the fair
point, constant bots, and the "threatener sweep": every pure commitment the opponent could make,
checking that the committed opponent gets at most V5's fair payoff for it in expectation.
Outputs v5_tables.txt, sweep_v5.txt, v5_results.json.   python3 run_v5.py [n_random_per_size]"""
import json, sys, time
from rmodal import *
from v5 import V5R as V5, fair_point, maxmin_val
from run import G, rand_game, analysis

NR = int(sys.argv[1]) if len(sys.argv) > 1 else 100
RND = R(npub=4, k=1, m=10)

def PD(T, R_, P, S): return G(f"PD{T}/{R_}/{P}/{S}", (["C", "D"],) * 2, [[(R_, R_), (S, T)], [(T, S), (P, P)]])
NAMED = [PD(5, 3, 1, 0), PD(3, 2, 1, 0), PD(4, 3, 2, 1), PD(3, 2, 0, -1), PD(10, 3, 1, 0),
         G("StagHunt", (["S", "H"],) * 2, [[(4, 4), (0, 3)], [(3, 0), (3, 3)]]),
         G("Chicken", (["Sw", "DS"],) * 2, [[(0, 0), (-1, 5)], [(5, -1), (-100, -100)]]),
         G("Chicken-mild", (["Sw", "St"],) * 2, [[(3, 3), (1, 4)], [(4, 1), (0, 0)]]),
         G("BoS", (["A", "B"],) * 2, [[(2, 1), (0, 0)], [(0, 0), (1, 2)]]),
         G("Coord", (["A", "B"],) * 2, [[(1, 1), (0, 0)], [(0, 0), (1, 1)]]),
         G("CoordRanked", (["A", "B"],) * 2, [[(2, 2), (0, 0)], [(0, 0), (1, 1)]]),
         G("MatchingPennies", (["H", "T"],) * 2, [[(1, -1), (-1, 1)], [(-1, 1), (1, -1)]])]

def fmt(d, acts): return " ".join(f"{a}:{x:.2f}" for a, x in zip(acts, d) if x)

def run_game(g, rnd, sweep_rows, verbose):
    ctx = RCtx(g, rnd)
    pr, pc, uv, desc = fair_point(g, rnd.npub)
    an = analysis(g)
    X = V5(); Xc = V5("V5'")
    FB = RFairBot((pr, pc), an["maxmin_act"], "FB-F"); PB = RPrudentBot((pr, pc), an["maxmin_act"], "PB-F")
    rec = dict(game=g.name, fair=desc, fair_payoff=uv, maxmin=an["maxmin_val"], rows=[])
    def cell(A, B, seat):
        X_, Y_ = (A, B) if seat == 0 else (B, A)
        px, py, s, ev = rplay(g, X_, Y_, ctx, N=60)
        dx, dy = dist(g, px, rnd, 0), dist(g, py, rnd, 1)
        me = ev[seat]; below = me < an["maxmin_val"][seat] - 1e-9
        r = dict(opp=B.name, seat=seat, row=fmt(dx, g.acts[0]), col=fmt(dy, g.acts[1]), ev=ev, stab=s, below=below)
        rec["rows"].append(r); return r
    opp = [("copy", Xc, (0,)), ("FB-F", FB, (0, 1)), ("PB-F", PB, (0, 1))]
    for a in range(g.n(1)): opp.append((f"col-const {g.acts[1][a]}", RConst(a, f"Const{g.acts[1][a]}"), (0,)))
    for a in range(g.n(0)): opp.append((f"row-const {g.acts[0][a]}", RConst(a, f"Const{g.acts[0][a]}"), (1,)))
    for name, B, seats in opp:
        for seat in seats:
            r = cell(X, B, seat)
            if verbose:
                print(f"  {g.name:14s} V5 in seat {seat} vs {name:14s} row[{r['row']}] col[{r['col']}] EV=({r['ev'][0]:.2f},{r['ev'][1]:.2f}){' BELOW-MAXMIN' if r['below'] else ''}")
    # threatener sweep: the opponent commits to each pure action; its payoff must stay <= its fair payoff.
    # (A commitment that is a function of the public draw is handled per r_pub by the same checks, so pure
    # commitments cover public mixes; private mixes are read only at the coarse resolution k, see v5.py.)
    for seat in (0, 1):
        for a in range(g.n(1 - seat)):
            r = cell(X, RConst(a, f"Commit{a}"), seat)
            opp_ev, my_ev = r["ev"][1 - seat], r["ev"][seat]
            vF = uv[1 - seat]; uF = uv[seat]
            # what the committer would get if V5 simply best-responded
            best_resp = max(range(g.n(seat)), key=lambda x: g.u(seat, x, a))
            v_if_give = g.u(1 - seat, a, best_resp)
            sweep_rows.append(dict(game=g.name, seat=seat, commit=g.acts[1 - seat][a], opp_ev=opp_ev, fair=vF,
                                   v_if_give=v_if_give, my_ev=my_ev, my_fair=uF, my_maxmin=an["maxmin_val"][seat],
                                   threat=v_if_give > vF + 1e-9, ok=opp_ev <= vF + 1e-9))
    return rec

t0 = time.time()
records, sweep = [], []
print("Named games (V5 fair point = discretised Nash bargaining solution, disagreement = maxmin values)")
for g in NAMED:
    pr, pc, uv, desc = fair_point(g, RND.npub)
    print(f"{g.name}: fair point {desc} -> payoffs {uv}")
    records.append(run_game(g, RND, sweep, verbose=True))
lines = ["| game | fair point | opp | seat | row play | col play | EV | below own maxmin |"]
for rec in records:
    for r in rec["rows"]:
        lines.append(f"| {rec['game']} | {rec['fair']} {rec['fair_payoff']} | {r['opp']} | {r['seat']} | {r['row']} | {r['col']} | ({r['ev'][0]:.2f},{r['ev'][1]:.2f}) | {'YES' if r['below'] else ''} |")
open("v5_tables.txt", "w").write("\n".join(lines) + "\n")

print(f"\nRandom games ({NR} per size, 2x2 and 3x3)")
stats = dict(n=0, copy_pareto=0, copy_top_games=0, copy_top_miss=0, copy_at_fair=0,
             fb_coop=0, pb_coop=0, below=0, cells=0)
for n in (2, 3):
    for seed in range(1000, 1000 + NR):
        g = rand_game(f"r{n}-{seed}", n, seed)
        an = analysis(g); outs = list(g.U)
        top = [o for o in outs if all(g.U[o][k] >= g.U[p][k] for p in outs for k in (0, 1))]
        rec = run_game(g, RND, sweep, verbose=False); records.append(rec)
        pr, pc, uv, desc = fair_point(g, RND.npub)
        stats["n"] += 1
        for r in rec["rows"]:
            stats["cells"] += 1; stats["below"] += r["below"]
            if r["opp"] == "V5'":
                ev = tuple(r["ev"]); stats["copy_at_fair"] += (abs(ev[0] - uv[0]) < 1e-9 and abs(ev[1] - uv[1]) < 1e-9)
                # Pareto: expected payoff not strictly dominated by any pure outcome
                stats["copy_pareto"] += not any(g.U[p][0] >= ev[0] + 1e-9 and g.U[p][1] >= ev[1] + 1e-9 for p in outs)
                if top:
                    stats["copy_top_games"] += 1; stats["copy_top_miss"] += tuple(r["ev"]) != tuple(map(float, g.U[top[0]]))
            if r["opp"] == "FB-F": stats["fb_coop"] += abs(r["ev"][0] - uv[0]) < 1e-9 and abs(r["ev"][1] - uv[1]) < 1e-9
            if r["opp"] == "PB-F": stats["pb_coop"] += abs(r["ev"][0] - uv[0]) < 1e-9 and abs(r["ev"][1] - uv[1]) < 1e-9
threats = [s for s in sweep if s["threat"]]
out = [f"random games: {stats['n']}",
       f"copies reach exactly the fair point: {stats['copy_at_fair']} / {stats['n']}",
       f"copies' expected payoff is Pareto-undominated by every pure outcome: {stats['copy_pareto']} / {stats['n']}",
       f"copies miss an outcome best for both players: {stats['copy_top_miss']} / {stats['copy_top_games']} games that have one",
       f"V5 reaches the fair point with FairBot-F (both seats): {stats['fb_coop']} / {2*stats['n']}; with PrudentBot-F: {stats['pb_coop']} / {2*stats['n']}",
       f"cells where V5 is below its own maxmin (tier C giving in, by design): {stats['below']} / {stats['cells']}",
       "",
       f"threatener sweep over all games (named + random), every pure commitment of the opponent in both seats: {len(sweep)} commitments",
       f"  commitments that are threats (committer would get more than its fair payoff if V5 gave in): {len(threats)}",
       f"  committer's expected payoff <= its fair payoff: {sum(s['ok'] for s in sweep)} / {len(sweep)}   (threats only: {sum(s['ok'] for s in threats)} / {len(threats)})",
       f"  V5's expected payoff below its maxmin against a threat: {sum(s['my_ev'] < s['my_maxmin'] - 1e-9 for s in threats)} / {len(threats)}",
       f"  V5's expected payoff below its maxmin against a non-threat commitment: {sum(s['my_ev'] < s['my_maxmin'] - 1e-9 for s in sweep if not s['threat'])}"]
bad = [s for s in sweep if not s["ok"]]
if bad: out += ["  FAILURES:"] + [f"    {s}" for s in bad[:20]]
print("\n" + "\n".join(out))
open("sweep_v5.txt", "w").write("\n".join(out) + "\n")
json.dump(dict(records=records, sweep=sweep), open("v5_results.json", "w"), indent=1, default=str)
print(f"\n{time.time()-t0:.0f}s")
