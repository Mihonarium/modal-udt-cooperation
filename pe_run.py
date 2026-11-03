"""Program-equilibrium tournament on the PD with self-contained bots (pe_bot.py embedded in each source).

Every bot run is a separate fresh interpreter that receives only the opponent's source (pe_env.run).
A match X vs Y is two runs: X on Y's source and Y on X's source (self-play: two separate runs of X on X).
Afterwards the experimenter audits soundness: for each pair {X, Y} the match system that both bots build is
rebuilt here from the prover text, and every axiom is checked against the programs' actual outputs (from the
runs) and the actual derivability relation. The audit is outside the game; no bot sees it.
Writes pe_results.json and pe_tables.txt."""
import json, resource, sys, time
from multiprocessing import Pool
import pe_env as E

BUDGETS = [0, 1, 2, 3, 4, E.INF]
def population():
    P = {}
    for tag, mk in (("FB", E.fairbot), ("PB", E.prudentbot), ("V4_", E.v4bot)):
        for k in BUDGETS: P[f"{tag}{E.idx(k)}"] = mk(k)
    P["CB"], P["DB"] = E.CB, E.DB
    return P

def run_job(job):
    x, y, seat = job
    P = population()
    act, info = E.run(P[x], P[y])
    return x, y, seat, act, info

# ---- audit (experimenter side)
NS = None
def _audit_init():
    global NS
    resource.setrlimit(resource.RLIMIT_AS, (E.MEM_LIMIT, E.MEM_LIMIT))
    NS = {"__name__": "pe_audit", "CODE": "SPEC = 'D otherwise'\n" + E.BODY}
    exec(NS["CODE"], NS)                     # a copy of the prover, for the experimenter's audit only

def audit_job(job):
    x, y, outcomes = job
    P = population()
    ns = NS
    tok = {n: ns["token"](s) for n, s in P.items()}
    act = {(tok[a], tok[b]): o for (a, b), o in outcomes.items()}
    extra = {}
    def atom_true(f):
        _, X, Y, a = f
        if (X, Y) not in act:                  # an atom outside the tournament: run it
            o, _ = E.run(ns["SRC"][X], ns["SRC"][Y]); act[(X, Y)] = E.outcome(o); extra[f"{ns['name'](X)} vs {ns['name'](Y)}"] = o
        return act[(X, Y)] == ns["ACTS"][a]
    def truth(f):
        k = f[0]
        if k == "top": return True
        if k == "bot": return False
        if k == "atom": return atom_true(f)
        if k == "box": return ns["system"](f[2]).member(f[1], f[3], f[4])
        if k == "fp": return (not ns["system"](f[1]).member(0, f[3], f)) or truth(f[2])
        if k == "not": return not truth(f[1])
        if k == "and": return all(truth(g) for g in f[1:])
        if k == "or": return any(truth(g) for g in f[1:])
        raise ValueError(f)
    t = time.time()
    ns["SYSTEMS"].clear()
    for n, tk in tok.items(): ns["NAMES"][tk] = n
    S = ns["system"](ns["lang"](tok[x], tok[y]))
    fails = [(name, ns["show"](f)) for name, f in S.axioms[1] if not truth(f)]
    n_ax = len(S.axioms[1])
    ns["SYSTEMS"].clear()
    return x, y, n_ax, fails, extra, round(time.time() - t, 1)

def main(procs=4):
    P = population()
    names = list(P)
    jobs = [(x, y, 0) for x in names for y in names] + [(x, x, 1) for x in names]
    runs = {}
    t0 = time.time()
    with Pool(procs) as pool:
        for x, y, seat, act, info in pool.imap_unordered(run_job, jobs, chunksize=1):
            runs[(x, y, seat)] = dict(action=act, **info)
            if act is None: print("NO VALID ACTION", x, y, info, flush=True)
    t_runs = time.time() - t0
    act = {(x, y): E.outcome(runs[(x, y, 0)]["action"]) for x in names for y in names}
    disagree = [x for x in names if runs[(x, x, 0)]["action"] != runs[(x, x, 1)]["action"]]
    pairs = [(x, y) for i, x in enumerate(names) for y in names[i:]]
    audits = {}
    t1 = time.time()
    with Pool(procs, initializer=_audit_init, maxtasksperchild=10) as pool:
        for x, y, n_ax, fails, extra, dt in pool.imap_unordered(audit_job, [(x, y, act) for x, y in pairs],
                                                                chunksize=1):
            audits[(x, y)] = dict(axioms=n_ax, failures=fails, extra_runs=extra, seconds=dt)
            if fails: print("AUDIT FAILURE", x, y, fails[:3], flush=True)
    t_audit = time.time() - t1
    cell = lambda x, y: act[(x, y)] + (act[(y, x)] if x != y else E.outcome(runs[(x, x, 1)]["action"]))
    lines = [f"Program-equilibrium PD tournament: self-contained bots, identical embedded provers "
             f"(row bot's action first; {len(jobs)} separate program runs, {t_runs:.0f}s wall; "
             f"audit {t_audit:.0f}s wall).", "Budget = necessitation height in the BPC each bot carries.", ""]
    w = 6
    lines.append(" " * 7 + "".join(n.rjust(w) for n in names))
    for x in names:
        lines.append(x.ljust(7) + "".join(cell(x, y).rjust(w) for y in names))
    nfail = sum(len(v["failures"]) for v in audits.values())
    nax = sum(v["axioms"] for v in audits.values())
    sucker = [(x, y) for x in names for y in names if cell(x, y) == "CD" and x != "CB"]
    invalid = [(k, v["returncode"]) for k, v in runs.items() if v["action"] is None]
    lines += ["", f"soundness audit: {nfail} false axioms among {nax} axioms of {len(pairs)} match systems",
              f"row bot (other than CB) cooperates while the opponent defects: {sucker or 'never'}",
              f"runs without a valid action (timeout, memory, crash): {invalid or 'none'}",
              f"self-play: the two separate runs disagree for: {disagree or 'no bot'}",
              f"longest single run (wall) {max(v['seconds'] for v in runs.values())}s "
              f"(limits: {E.CPU_LIMIT}s CPU, {E.MEM_LIMIT >> 30} GiB address space per run)"]
    try:
        old = json.load(open("bounded_results.json"))
        diff = [(x, y, old[f"{x} vs {y}"]["outcome"], cell(x, y)) for x in names for y in names
                if old[f"{x} vs {y}"]["outcome"] != cell(x, y)]
        lines.append("differences from the shared-prover table (bounded_tables.txt), (row, col, old, new): "
                     + (str(diff) if diff else "none"))
    except FileNotFoundError:
        pass
    open("pe_tables.txt", "w").write("\n".join(lines) + "\n")
    json.dump({"runs": {f"{x} vs {y}" + (" (second seat)" if s else ""): v for (x, y, s), v in runs.items()},
               "audit": {f"{x} / {y}": v for (x, y), v in audits.items()}},
              open("pe_results.json", "w"), indent=1, default=str)
    print("\n".join(lines))

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
