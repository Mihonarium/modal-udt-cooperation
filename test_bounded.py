"""Tests for bounded.py (runnable bounded bots in the calculus BPC).
1. Unbounded-budget BPC bots reproduce the exact GL (idealised PA) outcomes among FB, PB, V4, CB, DB.
2. Soundness audit: every axiom of the match systems is true of the programs' actual outputs.
3. Budget behaviour: budget-0 bots defect in self-play; V4_0 still cooperates with FB_1 (Sigma1 route).
4. Unexploitability: no proof-based bot plays C while its opponent plays D."""
import bounded as B
import modal, v4

def gl_reference():
    g = modal.Game("PD", (["C", "D"],) * 2, {(0, 0): (2, 2), (0, 1): (0, 3), (1, 0): (3, 0), (1, 1): (1, 1)})
    ctx = modal.Ctx(g, (0, 0), (1, 1))
    ctx.consts = {0: modal.Const(0, "CB"), 1: modal.Const(1, "DB")}
    I = {"FB": modal.FairBot(), "PB": modal.PrudentBot(), "V4": v4.V4("V4"), "CB": ctx.consts[0], "DB": ctx.consts[1]}
    return g, ctx, I

def test_unbounded_matches_gl():
    g, ctx, I = gl_reference()
    P = {"FB": B.fairbot(B.INF), "PB": B.prudentbot(B.INF), "V4": B.v4bot(B.INF), "CB": B.CB, "DB": B.DB}
    bad = []
    for x in P:
        for y in P:
            got = B.play("PD", P[x], P[y])
            r, c, _ = modal.play(g, I[x], I[y], ctx)
            if got != (r, c): bad.append((x, y, got, (r, c)))
    assert not bad, bad

def test_audit_sample():
    pairs = [(B.fairbot(1), B.fairbot(1)), (B.prudentbot(2), B.fairbot(3)), (B.v4bot(2), B.v4bot(2)),
             (B.v4bot(1), B.prudentbot(B.INF)), (B.prudentbot(0), B.CB)]
    for X, Y in pairs:
        B.play("PD", X, Y)
        assert B.audit(B.lang("PD", X, Y, 0)) == [], (B.name_of(X), B.name_of(Y))

def test_budget_zero():
    for mk in (B.fairbot, B.prudentbot, B.v4bot):
        X = mk(0)
        assert B.play("PD", X, X) == (1, 1)
    for mk in (B.fairbot, B.prudentbot):
        assert B.play("PD", mk(0), B.fairbot(B.INF)) == (1, 1)
    # V4's check "if I cooperate, they cooperate" is provable at height 0 against FairBot with budget >= 1
    # (Sigma1: V4's cooperation, if it happens, is provable at height 1). No Loeb step is needed.
    assert B.play("PD", B.v4bot(0), B.fairbot(1)) == (0, 0)
    assert B.play("PD", B.v4bot(1), B.fairbot(1)) == (1, 1)

def test_unexploitable():
    P = [B.fairbot(1), B.prudentbot(2), B.v4bot(2), B.fairbot(B.INF), B.CB, B.DB]
    for X in P[:4]:
        for Y in P:
            assert B.play("PD", X, Y) != (0, 1), (B.name_of(X), B.name_of(Y))

if __name__ == "__main__":
    for t in (test_unbounded_matches_gl, test_audit_sample, test_budget_zero, test_unexploitable):
        t(); print(t.__name__, "OK", flush=True)
