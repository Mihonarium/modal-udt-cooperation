"""Height-by-height trace: which formulas a match system can derive with necessitation height <= h.
Shows where the Loebian fixed point and the cooperation statements enter. Output: trace_bounded.txt."""
import bounded as B

PAIRS = [(B.fairbot(1), B.fairbot(1)), (B.fairbot(0), B.fairbot(0)), (B.prudentbot(2), B.prudentbot(2)),
         (B.v4bot(2), B.v4bot(2)), (B.v4bot(1), B.v4bot(1)), (B.fairbot(1), B.fairbot(B.INF))]

def main():
    out = []
    for X, Y in PAIRS:
        L = B.lang("PD", X, Y, 0); S = B.system(L)
        a, b = B.play("PD", X, Y)
        out.append(f"== {B.name_of(X)} vs {B.name_of(Y)}: {'CD'[a]}{'CD'[b]}")
        seen = set()
        for h in range(4):
            for t in (0, 1):
                new = [c for c in S.level(t, h) if c not in seen and
                       (B.box_free(c) or (c[0] == "fp" and c[3] in (0, 1)))]
                seen |= set(new)
                for c in sorted(new, key=B.show):
                    out.append(f"  height {h} theory {'T0' if t == 0 else 'T1 (T0+Con)'}: {B.show(c)}")
    open("trace_bounded.txt", "w").write("\n".join(out) + "\n")
    print("\n".join(out))

if __name__ == "__main__":
    main()
