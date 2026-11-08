"""Grounded bounded V5 (grounded_v5.py): copies, stones, foreign reciprocators, non-halting programs, disagreement."""
import time, sys
from run import G, rand_game
from v5 import fair_point
from grounded_v5 import *

ok = True
def check(label, cond, detail=""):
    global ok; ok &= bool(cond); print(f"  [{'OK' if cond else 'FAIL'}] {label} {detail}")
def show(game, X, Y, npub=1, n=400, fuel=2000, seconds=2.0):
    fx, fy, ev, fail = match(game, X, Y, npub, n, fuel=fuel, seconds=seconds)
    print(f"    row {fx}  col {fy}  EV=({ev[0]:.2f},{ev[1]:.2f}){'  failures ' + str(fail) if fail else ''}")
    return fx, fy, ev, fail
t0 = time.time(); sys.setrecursionlimit(20000)
print("PD 5/3/1/0")
g = G("PD", (["C", "D"],) * 2, [[(3, 3), (0, 5)], [(5, 0), (1, 1)]])
R0, C1 = v5g(0), v5g(1)
fx, fy, ev, f = show(g, R0, C1); check("copies cooperate", fx.get("C", 0) > 0.97 and fy.get("C", 0) > 0.97)
fx, fy, ev, f = show(g, R0, const_stone("C")); check("vs CooperateBot: defect", fx.get("D", 0) == 1)
fx, fy, ev, f = show(g, R0, const_stone("D")); check("vs DefectBot: defect", fx.get("D", 0) == 1)
fx, fy, ev, f = show(g, R0, eps_fairbot("C", "C", "D")); check("vs a FairBot written in different code (eps-grounded, copies my action): cooperate", fx.get("C", 0) > 0.9 and fy.get("C", 0) > 0.9)
fx, fy, ev, f = show(g, R0, LOOP, n=20, seconds=0.2); check("vs a program that never halts: time limit, defect (except the eps grounding)", fx.get("D", 0) >= 0.9, f"(failures = the loop's own runs: {f})")
fx, fy, ev, f = show(g, R0, CRASH, n=50); check("vs a program that crashes: defect (except the eps grounding)", fx.get("D", 0) >= 0.9)
print("Chicken (paper's matrix)")
g = G("Chicken", (["Sw", "DS"],) * 2, [[(0, 0), (-1, 5)], [(5, -1), (-100, -100)]])
R0, C1 = v5g(0, npub=2), v5g(1, npub=2)
fx, fy, ev, f = show(g, R0, C1, npub=2, n=200); check("copies: coin, with ~1% crashes from sampling noise (ideal 2,2)", ev[0] > 0.5 and ev[1] > 0.5, f"EV {ev}")
fx, fy, ev, f = show(g, R0, const_stone("DS", 2), npub=2); check("vs never-swerve: swerve where the coin says so, else 0.90; stone < 2 over both draws", ev[1] < 2, f"stone EV {ev[1]:.2f}")
fx, fy, ev, f = show(g, R0, const_stone("Sw", 2), npub=2); check("vs always-swerve: exploit", fx.get("DS", 0) > 0.9)
fx, fy, ev, f = show(g, R0, mix_stone("DS", "Sw", 0.5, 2), npub=2); check("vs private 50/50 mix: read from its table, mix <= 2", ev[1] <= 2, f"mix EV {ev[1]:.2f}")
print("Ultimatum 0..10")
n = 10; rows = [[((n - o, o) if o >= t else (0, 0)) for t in range(n + 2)] for o in range(n + 1)]
g = G("Ultimatum", ([f"o{o}" for o in range(n + 1)], [f"t{t}" for t in range(n + 2)]), rows)
R0, C1 = v5g(0, m=24), v5g(1, m=24)
fx, fy, ev, f = show(g, R0, C1, n=100); check("copies: 5/5", abs(ev[0] - 5) < 0.3 and abs(ev[1] - 5) < 0.3)
fx, fy, ev, f = show(g, const_stone("o4"), C1, n=200); check("stone offering 4: offerer < 5", ev[0] < 5, f"offerer EV {ev[0]:.2f}")
G4, G5 = v5g(0, fair="ult4", m=24), v5g(1, fair="ult5", m=24)
fx, fy, ev, f = show(g, G4, G5, n=100); check("offerer thinks 4 is fair, responder 5: they settle, both > 3 (bounded_v5 gave 0, 0)", ev[0] > 3 and ev[1] > 3, f"EV {ev}")
print("Random 2x2 games, copies")
hit = 0; N = 12
for seed in range(1000, 1000 + N):
    gg = rand_game(f"r2-{seed}", 2, seed); R0, C1 = v5g(0, npub=4), v5g(1, npub=4)
    fx, fy, ev, f = match(gg, R0, C1, npub=4, n=80); uv = fair_point(gg, 4)[2]
    hit += abs(ev[0] - uv[0]) < 0.5 and abs(ev[1] - uv[1]) < 0.5
check(f"copies within 0.5 of the fair point: {hit}/{N}", hit >= N - 2)
print(f"done in {time.time()-t0:.0f}s"); print("ALL OK" if ok else "SOME FAILED")
