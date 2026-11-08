"""Scenario checks for V5 (see v5.py).  Python 3, no dependencies."""
import time
from rmodal import *
from v5 import V5, fair_point
from run import G

def PD(T=5, R=3, P=1, S=0): return G(f"PD{T}/{R}/{P}/{S}", (["C", "D"],) * 2, [[(R, R), (S, T)], [(T, S), (P, P)]])
CHICKEN = G("Chicken", (["Sw", "DS"],) * 2, [[(0, 0), (-1, 5)], [(5, -1), (-100, -100)]])   # the paper's matrix
def ultimatum(n=10):
    """Normal form: row = offerer chooses the offer o in 0..n to the responder (keeps n-o); col = responder chooses a threshold t in 0..n+1
    (accept iff o >= t; t = n+1 rejects everything).  A mix over thresholds = any monotone acceptance rule."""
    rows = [[((n - o, o) if o >= t else (0, 0)) for t in range(n + 2)] for o in range(n + 1)]
    return G(f"Ultimatum{n}", ([f"o{o}" for o in range(n + 1)], [f"t{t}" for t in range(n + 2)]), rows)

ok = True
def check(label, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"  [{'OK' if cond else 'FAIL'}] {label} {detail}")

def show(g, X, Y, ctx, N=80):
    px, py, s, ev = rplay(g, X, Y, ctx, N=N)
    dx, dy = dist(g, px, ctx.rnd, 0), dist(g, py, ctx.rnd, 1)
    fmt = lambda d, acts: " ".join(f"{a}:{x:.2f}" for a, x in zip(acts, d) if x)
    print(f"    {X.name:>12} vs {Y.name:<12} row[{fmt(dx, g.acts[0])}] col[{fmt(dy, g.acts[1])}]  EV=({ev[0]:.2f},{ev[1]:.2f}) stab={s}")
    return px, py, ev, dx, dy

t0 = time.time()
# ---------- PD: reproduce PrudentBot's row ----------
print("PD")
rnd = R(npub=4, k=1, m=10)
for g in [PD(), PD(3, 2, 1, 0), PD(4, 3, 2, 1), PD(3, 2, 0, -1)]:
    ctx = RCtx(g, rnd)
    pr, pc, uv, desc = fair_point(g, rnd.npub)
    check(f"{g.name} fair point is (C,C)", desc == "(0, 0)", desc)
    V = V5(); V2 = V5("V5'")
    const = lambda p: 0
    FB = RFairBot((const, const), (1, 1)); PB = RPrudentBot((const, const), (1, 1), "PB")
    CB, DB = RConst(0, "CB"), RConst(1, "DB")
    exp = {"V5'": "CC", "FB": "CC", "PB": "CC", "CB": "DC", "DB": "DD"}
    for Y in [V2, FB, PB, CB, DB]:
        px, py, ev, dx, dy = show(g, V, Y, ctx)
        got = "CD"[max(range(2), key=lambda a: dx[a])] + "CD"[max(range(2), key=lambda b: dy[b])]
        check(f"{g.name} V5 vs {Y.name}: {got}", got == exp[Y.name] and max(dx) == 1 and max(dy) == 1, f"expected {exp[Y.name]}")
    # column seat too
    px, py, ev, dx, dy = show(g, PB, V, ctx)
    check(f"{g.name} PB vs V5 (col seat): CC", dx[0] == 1 and dy[0] == 1)
    px, py, ev, dx, dy = show(g, CB, V, ctx)
    check(f"{g.name} CB vs V5 (col seat): CD", dx[0] == 1 and dy[1] == 1)

# ---------- Chicken: fair point via public coin; threat response ----------
print("Chicken (paper's matrix)")
g = CHICKEN; rnd = R(npub=2, k=1, m=20); ctx = RCtx(g, rnd)
pr, pc, uv, desc = fair_point(g, rnd.npub)
print("    fair point:", desc, uv)
check("fair payoff is (2,2) from a 50/50 coin over (Sw,DS)/(DS,Sw)", uv == (2.0, 2.0))
V = V5(); V2 = V5("V5'")
px, py, ev, dx, dy = show(g, V, V2, ctx)
check("copies: EV (2,2), never crash", ev == (2.0, 2.0) and all(g.U[(px[r], py[r])] != (-100, -100) for r in px))
DS = RConst(1, "DontSwerveBot"); SW = RConst(0, "SwerveBot")
px, py, ev, dx, dy = show(g, V, DS, ctx)
p_swerve = dx[0]
check("vs DontSwerveBot: swerve with p just below 102/105 = 0.971", 0.9 < p_swerve < 102 / 105, f"p={p_swerve:.3f}")
check("vs DontSwerveBot: the threatener gets < 2 (fair)", ev[1] < 2, f"opp EV={ev[1]:.2f} (would get 5 if we always gave in)")
px, py, ev, dx, dy = show(g, V, SW, ctx)
check("vs SwerveBot: exploit (always DS, get 5)", dx[1] == 1 and ev[0] == 5)
# mixed threatener at the coarse resolution k: detected and answered per sigma
rnd4 = R(npub=2, k=4, m=20); ctx4 = RCtx(g, rnd4)
mix = RPolicy(lambda p, c, f: 1 if c < 2 else 0, "Mix50")   # DS with prob 1/2 using its coarse private draw
V = V5()
px, py, ev, dx, dy = show(g, V, mix, ctx4)
check("vs private 50/50 mix (k=4): mix gets <= 2", ev[1] <= 2, f"opp EV={ev[1]:.2f}; always-swerve would give it 2.5")

# ---------- Ultimatum ----------
print("Ultimatum (offers 0..10)")
g = ultimatum(); rnd = R(npub=1, k=1, m=24); ctx = RCtx(g, rnd)
pr, pc, uv, desc = fair_point(g, rnd.npub)
check("fair point is the 5/5 split", uv == (5, 5), desc)
V = V5(); V2 = V5("V5'")
px, py, ev, dx, dy = show(g, V, V2, ctx)
check("copies split 5/5", ev == (5.0, 5.0))
for o in (4, 1, 7):
    offer = RConst(o, f"Offer{o}")
    px, py, ev, dx, dy = show(g, offer, V, ctx)
    acc = sum(dy[t] for t in range(o + 1))
    if o < 5:
        thr = 5 / (10 - o)
        check(f"stone offering {o}: accept with p just below {thr:.3f}, offerer gets < 5", thr - 1 / rnd.m - 1e-9 <= acc < thr and ev[0] < 5,
              f"p={acc:.3f} offerer EV={ev[0]:.2f} responder EV={ev[1]:.2f}")
    else:
        check(f"stone offering {o}: accept always", acc == 1)

# ---------- Different notions of fairness ----------
print("Different notions of fairness")
def fair_at(share, n):
    def fp(g, npub):
        o = share; return (lambda p: o), (lambda p: o), (float(o), float(n - o)), f"offer {o}"
    return fp
# (i) the paper's 51% vs 50% number: a responder who thinks 50/50 is fair, against a committed offer of 49 of 100
g = ultimatum(100); rnd = R(npub=1, k=1, m=100); ctx = RCtx(g, rnd)
even = V5("V5-wants50", fair=fair_at(50, 100), read="pure")   # reads pure commitments only: 101 actions
px, py, ev, dx, dy = show(g, RConst(49, "Offer49"), even, ctx)
acc = sum(dy[t] for t in range(50))
check("responder (fair=50/50) vs committed offer of 49: accepts 98%, offerer gets < 50", acc == 0.98 and ev[0] < 50,
      f"accept rate {acc:.3f}, EV {ev}")
# (ii) two V5s with different notions, both reactive: offerer thinks 4 of 10 is fair, responder thinks 5
g = ultimatum(); rnd = R(npub=1, k=1, m=12); ctx = RCtx(g, rnd)
greedy = V5("V5-fair4", fair=fair_at(4, 10), kmax=4); even = V5("V5-fair5", fair=fair_at(5, 10), kmax=4)
px, py, ev, dx, dy = show(g, greedy, even, ctx, N=60)
print("    (no fixed point: offer 4 -> accept 9/12 -> offer 5 -> accept all -> offer 4 ...; the chain freezes at a point of the cycle)")
check("V5(fair=4) offering to V5(fair=5): evaluates (the pair cycles; see README)", True, f"EV {ev}")
print(f"done in {time.time()-t0:.0f}s")
print("ALL OK" if ok else "SOME FAILED")
