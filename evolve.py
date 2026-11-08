"""Selection dynamics on the round-robin payoff matrix (tournament.json).

A[i][j] = agent i's normalised payoff against agent j, averaged over both seats (and over the chosen games).
  (1) Replicator dynamics: x_i' = x_i * f_i / mean(f), f_i = sum_j A[i][j] x_j.  Fitness is the normalised payoff in
      [0, 1] (a Chicken crash is 0), so a type that only crashes dies out in one generation.  Run from the uniform
      start and from many random initial compositions (Dirichlet), report the endpoints and their basins.
  (2) Wright-Fisher with a finite population and a small mutation rate: the long-run average composition, which
      exposes neutral drift (a type that ties with the resident at every match can drift in).
  (3) Invasion analysis: for every monomorphic population, which mutants strictly invade, which are neutral, and
      whether the resident is an ESS.
python3 evolve.py [tournament.json]
"""
import json, random, sys
from collections import Counter

def load(path="tournament.json"):
    d = json.load(open(path)); return d

def matrix(d, games, names, lo_hi):
    """A[i][j]: i's normalised payoff vs j, mean over seats and games."""
    n = len(names); A = [[0.0] * n for _ in range(n)]; cnt = [[0] * n for _ in range(n)]
    for g in games:
        res = d["results"][g]; (lo0, lo1), (hi0, hi1) = lo_hi[g]
        for i, xi in enumerate(names):
            for j, yj in enumerate(names):
                ev = res[xi][yj]
                if ev[0] is None: continue
                A[i][j] += (ev[0] - lo0) / ((hi0 - lo0) or 1); cnt[i][j] += 1          # i row vs j col
                A[j][i] += (ev[1] - lo1) / ((hi1 - lo1) or 1); cnt[j][i] += 1          # j col vs i row -> j's payoff
    return [[A[i][j] / cnt[i][j] if cnt[i][j] else 0.0 for j in range(n)] for i in range(n)]

def replicator(A, x, gens=3000, tol=1e-12):
    n = len(x)
    for t in range(gens):
        f = [sum(A[i][j] * x[j] for j in range(n)) for i in range(n)]
        fbar = sum(x[i] * f[i] for i in range(n))
        if fbar <= 0: break
        nx = [x[i] * f[i] / fbar for i in range(n)]
        s = sum(nx); nx = [v / s for v in nx]
        if max(abs(nx[i] - x[i]) for i in range(n)) < tol: x = nx; break
        x = nx
    return x, t + 1

def wright_fisher(A, N=200, mu=0.005, gens=20000, seed=0, burn=2000):
    rng = random.Random(seed); n = len(A)
    pop = [rng.randrange(n) for _ in range(N)]; acc = [0.0] * n
    for t in range(gens):
        c = Counter(pop); x = [c[i] / N for i in range(n)]
        f = [sum(A[i][j] * x[j] for j in range(n)) for i in range(n)]
        w = [x[i] * f[i] for i in range(n)]
        if sum(w) <= 0: w = x
        pop = rng.choices(range(n), weights=w, k=N)
        pop = [rng.randrange(n) if rng.random() < mu else p for p in pop]
        if t >= burn:
            for p in pop: acc[p] += 1
    tot = sum(acc); return [a / tot for a in acc]

def invasion(A, names, eps=1e-9):
    n = len(names); out = []
    for i in range(n):
        res = A[i][i]
        strict = [names[j] for j in range(n) if j != i and A[j][i] > res + eps]
        neutral = [names[j] for j in range(n) if j != i and abs(A[j][i] - res) <= eps]
        # ESS: no strict invader, and every neutral mutant does worse against itself than the resident does against it
        ess = not strict and all(A[i][j] > A[j][j] + eps for j in range(n) if j != i and abs(A[j][i] - res) <= eps)
        out.append((names[i], res, strict, neutral, ess))
    return out

def fmt_x(x, names, thr=0.005):
    return ", ".join(f"{names[i]} {x[i]:.2f}" for i in sorted(range(len(x)), key=lambda i: -x[i]) if x[i] >= thr)

def analyse(d, games, names, lo_hi, label, n_init=400, seed=1):
    A = matrix(d, games, names, lo_hi); n = len(names); lines = [f"=== {label} ({len(games)} games) ==="]
    # average payoff = round-robin score
    lines.append("round-robin score (mean over opponents incl. self): " + fmt_x([sum(r) / n for r in A], names, thr=-1))
    x0 = [1 / n] * n; x, T = replicator(A, x0)
    lines.append(f"replicator from the uniform start ({T} generations): {fmt_x(x, names)}")
    rng = random.Random(seed); ends = Counter(); surv = Counter()
    for _ in range(n_init):
        x0 = [rng.gammavariate(0.5, 1) for _ in range(n)]; s = sum(x0); x0 = [v / s for v in x0]
        x, _ = replicator(A, x0)
        key = tuple(sorted(names[i] for i in range(n) if x[i] >= 0.01)); ends[key] += 1
        for i in range(n):
            if x[i] >= 0.01: surv[names[i]] += x[i]
    lines.append(f"endpoints from {n_init} random initial compositions (types with share >= 1%):")
    for key, c in ends.most_common(8): lines.append(f"  {100*c/n_init:5.1f}%  {{{', '.join(key)}}}")
    lines.append("mean final share across random starts: " + fmt_x([surv[nm] / n_init for nm in names], names))
    wf = wright_fisher(A, seed=seed)
    lines.append("Wright-Fisher N=200, mutation 0.5%, long-run average composition: " + fmt_x(wf, names, thr=0.02))
    lines.append("invasion analysis (resident -> strict invaders | neutral mutants | ESS?):")
    for nm, res, strict, neutral, ess in invasion(A, names):
        lines.append(f"  {nm:14s} self {res:.3f}  invaded by: {', '.join(strict) or '-'}  | neutral: {', '.join(neutral) or '-'}  | {'ESS' if ess else 'not ESS'}")
    return "\n".join(lines), A

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "tournament.json"
    d = load(path); games = d["games"]; names = list(d["results"][games[0]].keys())
    # recover payoff ranges from the game definitions
    import tournament as T
    from run import rand_game
    gdefs = {g.name: g for g in T.NAMED}
    for g in games:
        if g.startswith("r"): gdefs[g] = rand_game(g, int(g[1]), int(g.split("-")[1]))
    lo_hi = {g: ((min(u[0] for u in gdefs[g].U.values()), min(u[1] for u in gdefs[g].U.values())),
                 (max(u[0] for u in gdefs[g].U.values()), max(u[1] for u in gdefs[g].U.values()))) for g in games}
    out = []; mats = {}
    for label, sel in [("all games", games), ("named games", [g for g in games if not g[0] == "r"]),
                       ("random games", [g for g in games if g[0] == "r"]),
                       ("PD5/3/1/0", ["PD5/3/1/0"]), ("Chicken", ["Chicken"]), ("Chicken-mild", ["Chicken-mild"]),
                       ("BoS", ["BoS"]), ("StagHunt", ["StagHunt"])]:
        txt, A = analyse(d, sel, names, lo_hi, label); out.append(txt); mats[label] = A
    txt = "\n\n".join(out); print(txt); open("evolve.txt", "w").write(txt + "\n")
    json.dump(dict(names=names, matrices=mats), open("evolve.json", "w"))

if __name__ == "__main__":
    main()
