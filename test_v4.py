"""V4 must reproduce PrudentBot's whole PD row, in every PD payoff set, from both seats."""
from modal import *
from v3 import V3
from v4 import V4
from run import G

PDS = [(3, 2, 1, 0), (5, 3, 1, 0), (4, 3, 2, 1), (10, 3, 1, 0), (3, 2, 0, -1), (101, 100, 1, 0)]
VARIANTS = {"V4": dict(), "V4-gated": dict(gate=True), "V4-probe2": dict(probe=2),
            "V4-exploitlast": dict(order="coop-neutral-exploit")}

def row(g, X, ctx):
    opps = {"FB": FairBot(), "PB": PrudentBot(), "self": X, "DB": Const(1, "DB"), "CB": Const(0, "CB"),
            "V3-B": V3("V3-B", order="exploit-last"), "UDT": ModalUDT("UDT", default=1)}
    out = {}
    for k, Y in opps.items():
        r1, c1, _ = play(g, X, Y, ctx, N=120)
        r2, c2, _ = play(g, Y, X, ctx, N=120)
        out[k] = ("CD"[r1] + "CD"[c1], "CD"[c2] + "CD"[r2])   # (me, them) from each seat
    return out

def check(verbose=True):
    ok_all = {}
    for (T, R, P, S) in PDS:
        g = G(f"PD{T}/{R}/{P}/{S}", (["C", "D"],) * 2, [[(R, R), (S, T)], [(T, S), (P, P)]])
        ctx = Ctx(g, (0, 0), (1, 1))
        pb = row(g, PrudentBot(), ctx)
        for name, kw in VARIANTS.items():
            got = row(g, V4(name, **kw), ctx)
            ok = got == pb
            ok_all.setdefault(name, True); ok_all[name] &= ok
            if verbose and (not ok or (T, R, P, S) == PDS[0]):
                print(g.name, name, "OK" if ok else "MISMATCH", got, "\n   PB row:", pb)
    return ok_all

def test_v4_matches_prudentbot_row():
    assert check(verbose=False)["V4"]

if __name__ == "__main__":
    res = check()
    print(res)
    assert res["V4"], "V4 does not reproduce PrudentBot's row"
    print("V4 reproduces PrudentBot's PD row in all", len(PDS), "payoff sets: OK")
