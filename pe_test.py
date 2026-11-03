"""Tests for the self-contained bots (pe_bot.py, pe_env.py). Every action below is a separate program run.
1. Unbounded-budget bots reproduce the exact GL (idealised PA) outcomes among FB, PB, V4, CB, DB.
2. Soundness audit on a sample of match systems (every axiom true of the actual outputs and derivability).
3. Budget 0: FairBot_0 and PrudentBot_0 defect in self-play; V4_0 cooperates with FB_1 (Sigma1 route).
4. Unexploitability: no proof-based bot plays C while its opponent plays D.
5. Source analysis: a program the bot cannot read gets no Unf axiom, so FairBot defects against it."""
import pe_env as E
import pe_run as R
import modal, v4

def play(X, Y):
    a, ia = E.run(X, Y); b, ib = E.run(Y, X)
    assert a and b, (ia, ib)
    return a + b

def test_unbounded_matches_gl():
    g = modal.Game("PD", (["C", "D"],) * 2, {(0, 0): (2, 2), (0, 1): (0, 3), (1, 0): (3, 0), (1, 1): (1, 1)})
    ctx = modal.Ctx(g, (0, 0), (1, 1))
    ctx.consts = {0: modal.Const(0, "CB"), 1: modal.Const(1, "DB")}
    I = {"FB": modal.FairBot(), "PB": modal.PrudentBot(), "V4": v4.V4("V4"), "CB": ctx.consts[0], "DB": ctx.consts[1]}
    P = {"FB": E.fairbot(E.INF), "PB": E.prudentbot(E.INF), "V4": E.v4bot(E.INF), "CB": E.CB, "DB": E.DB}
    bad = []
    for x in P:
        for y in P:
            got = play(P[x], P[y])
            r, c, _ = modal.play(g, I[x], I[y], ctx)
            if got != "CD"[r] + "CD"[c]: bad.append((x, y, got, (r, c)))
    assert not bad, bad

def test_audit_sample():
    R._audit_init()
    P = R.population()
    act = {}
    for x, y in [("FB1", "FB1"), ("PB2", "FB3"), ("V4_2", "V4_2"), ("V4_1", "PBinf"), ("PB0", "CB")]:
        _, _, _, fails, _, _ = R.audit_job((x, y, act))
        assert fails == [], (x, y, fails)

def test_budget_zero():
    for mk in (E.fairbot, E.prudentbot):
        assert play(mk(0), mk(0)) == "DD"
        assert play(mk(0), E.fairbot(E.INF)) == "DD"
    assert play(E.v4bot(0), E.fairbot(1)) == "CC"
    assert play(E.v4bot(1), E.fairbot(1)) == "DD"

def test_unexploitable():
    P = [E.fairbot(1), E.prudentbot(2), E.v4bot(2), E.fairbot(E.INF), E.CB, E.DB]
    for X in P[:4]:
        for Y in P:
            assert play(X, Y) != "CD"

def test_unreadable_opponent():
    odd = E.fairbot(2) + "\n"          # behaves exactly like FairBot_2, but is not the exact form the bot reads
    a, _ = E.run(E.fairbot(2), odd)
    assert a == "D"

if __name__ == "__main__":
    for t in (test_unreadable_opponent, test_budget_zero, test_unexploitable, test_audit_sample,
              test_unbounded_matches_gl):
        t(); print(t.__name__, "OK", flush=True)
