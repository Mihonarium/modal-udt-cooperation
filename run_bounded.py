"""Bounded tournament on the PD: FairBot_k, PrudentBot_k, V4_k for k in 0..4 and inf, CooperateBot, DefectBot.
Every pairing is a real run of the two programs on each other's source. Also audits soundness: every axiom of
every match system used is checked to be true of the programs' actual outputs.
Writes bounded_results.json and bounded_tables.txt."""
import json, sys, time
from multiprocessing import Pool
import bounded as B

BUDGETS = [0, 1, 2, 3, 4, B.INF]
def population():
    P = []
    for mk in (B.fairbot, B.prudentbot, B.v4bot):
        for k in BUDGETS: P.append(mk(k))
    return P + [B.CB, B.DB]

def job(pair):
    X, Y = pair
    P = population()                      # registers names in this process
    t = time.time()
    B.SYSTEMS.clear()                     # one match at a time: bounded memory per worker
    a, b = B.play("PD", X, Y)
    fails = B.audit(B.lang("PD", X, Y, 0))
    B.SYSTEMS.clear()
    return B.name_of(X), B.name_of(Y), "CD"[a] + "CD"[b], fails, round(time.time() - t, 1)

def main(procs=4):
    P = population()
    pairs = [(X, Y) for X in P for Y in P]
    out = {}
    t0 = time.time()
    with Pool(procs, maxtasksperchild=20) as pool:
        for x, y, o, fails, dt in pool.imap_unordered(job, pairs, chunksize=1):
            out[(x, y)] = dict(outcome=o, audit_failures=fails, seconds=dt)
            if fails: print("AUDIT FAILURE", x, y, fails[:3], flush=True)
    names = [B.name_of(X) for X in P]
    lines = [f"Bounded PD tournament (row player's action first; {len(pairs)} runs, "
             f"{time.time() - t0:.0f}s wall). Budget = necessitation height in BPC.", ""]
    w = 6
    lines.append(" " * 7 + "".join(n.rjust(w) for n in names))
    for x in names:
        lines.append(x.ljust(7) + "".join(out[(x, y)]["outcome"].rjust(w) for y in names))
    nfail = sum(len(v["audit_failures"]) for v in out.values())
    sucker = [(x, y) for (x, y), v in out.items() if v["outcome"] == "CD" and x not in ("CB",)]
    lines += ["", f"soundness audit: {nfail} false axioms over all {len(pairs)} match systems",
              f"row bot (other than CB) cooperates while the opponent defects: {sucker or 'never'}"]
    open("bounded_tables.txt", "w").write("\n".join(lines) + "\n")
    json.dump({f"{x} vs {y}": v for (x, y), v in out.items()}, open("bounded_results.json", "w"), indent=1)
    print("\n".join(lines))

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
