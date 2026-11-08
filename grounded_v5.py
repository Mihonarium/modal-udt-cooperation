"""Grounded bounded V5: a runnable program that handles ARBITRARY opponent programs by simulation.

Bots are Python source text defining  act(me, opp, r_pub, rng, game) -> action name  where `me` and `opp` are the
two source strings, r_pub the public draw, rng the bot's private random source and game the payoff matrix.  A bot
may run another bot's source with run(src, its_opp, r_pub, rng, game).  Every run burns fuel; when the fuel is
gone the run raises and the caller treats the opponent as unknown.

The regress problem (I simulate you simulating me ...) is solved as in Oesterheld, "Robust program equilibrium"
(2019): with probability eps per decision the agent acts WITHOUT simulating (it plays its part of the fair point),
so the chain of nested simulations ends with probability 1 and has expected depth 1/eps.  That is the private
random source doing the job the Löbian proof did for the idealised agent.

V5G, per decision:
  ground   with probability eps play F(r_pub); otherwise:
  stone    if the opponent's source is a commitment table, read it exactly (tiers A-D of bounded_v5 on the table);
  A        for each opponent action b that could be exploited for more than u_F: run the opponent K_A times against
           the constant agent that punishes b; if it plays b every time, play the best response;
  B        run the opponent once against me; if it plays its part of F, play my part of F;
  C        otherwise take the sampled action a as the opponent's commitment and apply the give-in rule: best-respond
           if that leaves the opponent at or below v_F, else give in with probability p (largest grid value keeping
           the committer strictly below v_F) and refuse otherwise;
  D        if the opponent cannot be run (fuel exhausted, error, bad output), maxmin.
Against a stone the result is exact; against a program the single sample makes the response a random variable
whose expectation is what the tables report (Monte Carlo over tapes).  Expected work per decision is geometric in
(1 - eps), since each simulation level grounds with probability eps and each level runs the opponent against me
once (the probes against constant agents do not recurse).
"""
import json, random
from v5 import fair_point, maxmin_val
from run import G

class Exhausted(Exception): pass
FUEL = [0]

def run(src, its_opp, r_pub, rng, game):
    """Execute bot `src` in the seat opposite to the caller.  Burns one unit of fuel."""
    FUEL[0] -= 1
    if FUEL[0] <= 0: raise Exhausted()
    if src not in _CODE:
        ns = {"run": run, "json": json, "fair_point": fair_point, "maxmin_val": maxmin_val}
        exec(compile(src, "<bot>", "exec"), ns)
        _CODE[src] = ns["act"]
    return _CODE[src](src, its_opp, r_pub, rng, game)
_CODE = {}

def stone_src(table):
    """Commitment: table[r_pub] is a list of action names, one drawn uniformly by the private source."""
    return f"TABLE = {json.dumps(table)}\ndef act(me, opp, r_pub, rng, game):\n    row = TABLE[r_pub % len(TABLE)]\n    return row[rng.randrange(len(row))]\n"
def const_stone(a, npub=1): return stone_src([[a]] * npub)
def mix_stone(x, y, p, npub=1, m=20): return stone_src([[x] * round(p * m) + [y] * (m - round(p * m))] * npub)

V5G_TEMPLATE = '''# V5G: grounded bounded V5.  fair=%(fair)s eps=%(eps)r m=%(m)d ka=%(ka)d
EPS, M, KA, FAIR = %(eps)r, %(m)d, %(ka)d, %(fair)r
def _fair(game, npub):
    if FAIR == "nbs": return fair_point(game, npub)
    o = int(FAIR[3:]); n = game.n(0) - 1
    return (lambda p: o), (lambda p: o), (float(n - o), float(o)), "offer %%d" %% o
def act(me, opp, r_pub, rng, game):
    role = ROLE
    nA, nB = game.n(role), game.n(1 - role)
    acts, oacts = game.acts[role], game.acts[1 - role]
    U = lambda a, b: game.u(role, a, b); V = lambda a, b: game.u(1 - role, b, a)
    pr, pc, uv, _ = _fair(game, NPUB)
    myF, opF = (pr, pc) if role == 0 else (pc, pr); uF, vF = uv[role], uv[1 - role]
    mm = max(range(nA), key=lambda x: (min(U(x, b) for b in range(nB)), x == myF(0), -x))
    def respond(qs):
        # qs[p'] = the opponent's action distribution at public draw p'.  Where it is exactly its part of F I play
        # mine; elsewhere I best-respond when that leaves it at or below v_F, else give in with probability p and
        # refuse otherwise, p the largest grid value keeping its expectation OVER ALL DRAWS strictly below v_F.
        plan = {}
        for p2, q in qs.items():
            if q[opF(p2)] == 1: plan[p2] = ("F", V(myF(p2), opF(p2)), None); continue
            myev = lambda x: sum(q[b] * U(x, b) for b in range(nB)); opev = lambda x: sum(q[b] * V(x, b) for b in range(nB))
            a_star = max(range(nA), key=lambda x: (myev(x), x == myF(p2), -x))
            a_ref = min(range(nA), key=lambda x: (opev(x), -myev(x), x != myF(p2), x))
            plan[p2] = ("mix", a_star, a_ref, opev(a_star), opev(a_ref))
        def total(j):
            t = 0.0
            for v in plan.values():
                t += v[1] if v[0] == "F" else (j / M) * v[3] + (1 - j / M) * v[4]
            return t / len(plan)
        if total(M) <= vF + 1e-12: j = M
        else:
            ok = [j for j in range(M + 1) if total(j) < vF - 1e-12]; j = max(ok) if ok else 0
        v = plan[r_pub]
        if v[0] == "F": return acts[myF(r_pub)]
        return acts[v[1]] if rng.randrange(M) < j else acts[v[2]]
    def exploitable(reads):    # reads[p'] = list of actions the opponent played against the punisher of b, at p'
        for b in sorted(range(nB), key=lambda b: -max(U(x, b) for x in range(nA))):
            a = max(range(nA), key=lambda x: (U(x, b), -x))
            if U(a, b) <= uF: continue
            if all(x == oacts[b] for p2 in reads for x in reads[p2](b, a)): return acts[a]
        return None
    if opp.startswith("TABLE = "):                                        # a commitment table: read it exactly
        tab = json.loads(opp.splitlines()[0][8:])
        qs = {p2: [tab[p2 %% len(tab)].count(oacts[b]) / len(tab[p2 %% len(tab)]) for b in range(nB)] for p2 in range(NPUB)}
        e = exploitable({p2: (lambda b, a, p2=p2: [oacts[b]] if qs[p2][b] == 1 else [None]) for p2 in range(NPUB)})
        return e if e is not None else respond(qs)
    if rng.random() < EPS: return acts[myF(r_pub)]                       # ground: act without simulating
    try:
        def probe(p2):
            def f(b, a):
                punisher = "TABLE = " + json.dumps([[acts[a]]] * NPUB) + "\\n"   # a commitment table: read in one step
                out = []
                for _ in range(KA):
                    x = run(opp, punisher, p2, rng, game); out.append(x)
                    if x != oacts[b]: break
                return out
            return f
        sample = [None]
        def against_me():                                                  # one sample of it against me (recursive)
            if sample[0] is None: sample[0] = run(opp, me, r_pub, rng, game)
            return sample[0]
        # A: exploitable only if it plays b against the punisher AND against me (swerving against a stone is not
        # swerving against an agent); the probes come first because they do not recurse
        e = exploitable({p2: (lambda bb, a, p2=p2: probe(p2)(bb, a) + [against_me()] if all(x == oacts[bb] for x in probe(p2)(bb, a)) else [None]) for p2 in range(NPUB)})
        if e is not None: return e
        if against_me() not in oacts: return acts[mm]
        b = oacts.index(against_me())
        return respond({p2: [1.0 if x == b else 0.0 for x in range(nB)] for p2 in range(NPUB)})
    except Exception:
        return acts[mm]                                                   # D: cannot run the opponent
'''
def v5g(role, npub=1, fair="nbs", eps=0.05, m=20, ka=60):
    return (V5G_TEMPLATE % dict(fair=fair, eps=eps, m=m, ka=ka)).replace("ROLE", str(role)).replace("NPUB", str(npub))

# a reciprocator written in different code: Oesterheld's epsilon-grounded FairBot aimed at a target action
def eps_fairbot(target_me, target_opp, fallback, eps=0.1):
    return f'''def act(me, opp, r_pub, rng, game):
    if rng.random() < {eps!r}: return {target_me!r}
    try:
        return {target_me!r} if run(opp, me, r_pub, rng, game) == {target_opp!r} else {fallback!r}
    except Exception:
        return {fallback!r}
'''
LOOP = "def act(me, opp, r_pub, rng, game):\n    while True: pass\n"          # never halts
CRASH = "def act(me, opp, r_pub, rng, game):\n    return 1/0\n"

import signal
def _alarm(signum, frame): raise Exhausted()
def timed_run(src, opp, r_pub, rng, game, fuel, seconds):
    """A top-level run with a fuel budget (counts nested runs) and a wall-clock limit (catches loops)."""
    FUEL[0] = fuel
    signal.signal(signal.SIGALRM, _alarm); signal.setitimer(signal.ITIMER_REAL, seconds)
    try: return run(src, opp, r_pub, rng, game)
    except Exception: return None
    finally: signal.setitimer(signal.ITIMER_REAL, 0)

def play_once(game, X, Y, r_pub, seed, fuel=20000, seconds=2.0):
    rx, ry = random.Random(seed * 2 + 1), random.Random(seed * 2 + 2)
    return timed_run(X, Y, r_pub, rx, game, fuel, seconds), timed_run(Y, X, r_pub, ry, game, fuel, seconds)

def match(game, X, Y, npub=1, n=400, seed0=0, fuel=20000, seconds=2.0):
    """Monte Carlo over tapes: returns (row action freqs, col action freqs, expected payoffs, failures)."""
    fx, fy = {}, {}; tot = [0.0, 0.0]; cnt = 0; fail = 0
    for i in range(n):
        p = i % npub
        ax, ay = play_once(game, X, Y, p, seed0 + i, fuel, seconds)
        if ax in game.acts[0]: fx[ax] = fx.get(ax, 0) + 1
        if ay in game.acts[1]: fy[ay] = fy.get(ay, 0) + 1
        if ax not in game.acts[0] or ay not in game.acts[1]: fail += 1; continue
        u = game.U[(game.acts[0].index(ax), game.acts[1].index(ay))]; tot[0] += u[0]; tot[1] += u[1]; cnt += 1
    k = max(cnt, 1); nx, ny = max(sum(fx.values()), 1), max(sum(fy.values()), 1)
    return ({a: round(v / nx, 3) for a, v in fx.items()}, {a: round(v / ny, 3) for a, v in fy.items()}, (tot[0] / k, tot[1] / k), fail)
