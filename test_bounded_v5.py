"""Bounded V5 (bounded_v5.py): the scenario checks of test_v5.py, on runnable programs."""
import time
from run import G, rand_game, analysis
from v5 import fair_point
from bounded_v5 import *

ok = True
def check(label, cond, detail=""):
    global ok; ok &= bool(cond); print(f"  [{'OK' if cond else 'FAIL'}] {label} {detail}")
def show(g, X, Y):
    tx, ty, ev = match(g, X, Y)
    print(f"    row {dist(g, tx, 0)}  col {dist(g, ty, 1)}  EV=({ev[0]:.2f},{ev[1]:.2f})")
    return tx, ty, ev

t0 = time.time()
print("PD (5/3/1/0), npub=1, m=4")
g = G("PD", (["C", "D"],) * 2, [[(3, 3), (0, 5)], [(5, 0), (1, 1)]])
V = v5b(budget=1, npub=1, m=4); V0 = v5b(budget=0, npub=1, m=4)
for Y, exp in [(V, "CC"), (const_stone("C", 1, 4), "DC"), (const_stone("D", 1, 4), "DD"), (V0, "DD")]:
    tx, ty, ev = show(g, V, Y)
    got = "CD"[tx[0][0]] + "CD"[ty[0][0]]
    check(f"V5B_1 vs {'copy' if Y == V else ('V5B_0' if Y == V0 else Y[:20])}: {got}", got == exp, f"expected {exp}")
print("Chicken (paper's matrix), npub=2, m=20")
g = G("Chicken", (["Sw", "DS"],) * 2, [[(0, 0), (-1, 5)], [(5, -1), (-100, -100)]])
V = v5b(budget=1, npub=2, m=20); V2 = v5b(budget=2, npub=2, m=20)
tx, ty, ev = show(g, V, V2); check("copies (budgets 1, 2): coin, EV (2,2)", ev == (2.0, 2.0))
tx, ty, ev = show(g, V, const_stone("DS", 2, 20)); check("vs never-swerve stone: swerve 0.95, stone < 2", dist(g, tx, 0)["Sw"] == 0.95 and ev[1] < 2, f"stone EV {ev[1]:.2f}")
tx, ty, ev = show(g, V, const_stone("Sw", 2, 20)); check("vs always-swerve stone: exploit, 5", ev[0] == 5)
tx, ty, ev = show(g, V, mix_stone("DS", "Sw", 10, 2, 20)); check("vs private 50/50 mix: read exactly, mix gets <= 2", ev[1] <= 2, f"mix EV {ev[1]:.2f}")
print("Ultimatum 0..10, npub=1, m=24")
n = 10; rows = [[((n - o, o) if o >= t else (0, 0)) for t in range(n + 2)] for o in range(n + 1)]
g = G("Ultimatum", ([f"o{o}" for o in range(n + 1)], [f"t{t}" for t in range(n + 2)]), rows)
V = v5b(budget=1, npub=1, m=24)
tx, ty, ev = show(g, V, V); check("copies: 5/5", ev == (5.0, 5.0))
tx, ty, ev = show(g, const_stone("o4", 1, 24), V); acc = sum(x for a, x in dist(g, ty, 1).items() if int(a[1:]) <= 4)
check("stone offering 4: accepted 19/24, offerer < 5", abs(acc - 19 / 24) < 1e-3 and ev[0] < 5, f"p={acc:.3f} offerer EV {ev[0]:.2f}")
g4 = v5b(fair="ult4", budget=1, npub=1, m=24); g5 = v5b(fair="ult5", budget=1, npub=1, m=24)
tx, ty, ev = show(g, g4, g5); check("V5B(fair=4) vs V5B(fair=5): no Löb, no reading -> maxmin (documented limit)", True, f"EV {ev}")
print("Random games, copies, npub=4, m=4")
hit = 0; N = 30
for seed in range(1000, 1000 + N):
    gg = rand_game(f"r2-{seed}", 2, seed); V = v5b(budget=1, npub=4, m=4)
    tx, ty, ev = match(gg, V, V); uv = fair_point(gg, 4)[2]
    hit += abs(ev[0] - uv[0]) < 1e-9 and abs(ev[1] - uv[1]) < 1e-9
check(f"copies at the fair point: {hit}/{N}", hit == N)
print(f"done in {time.time()-t0:.0f}s"); print("ALL OK" if ok else "SOME FAILED")
