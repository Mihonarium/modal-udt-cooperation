# Modal UDT vs Kelvin's claim (2026-11-03, saved by main from the study agent's summary; code and tables in this directory)

Verdict: Kelvin is right only for identical copies in the PD; the claim fails "much as FairBot and PrudentBot do" and in other games.

Checks: own exact evaluator by Kripke levels reproduces every outcome in arXiv:1401.5577 (FB/PB/CB/DB, PB defecting against
CB from PA+2, PB with a PA probe losing self-cooperation) and matches the literal box definition on 5,880 pairings. Read
directly: arXiv:1401.5577, 1602.04184. Via a summarising web tool only: Fallenstein's modal UDT post, Slepnev's post,
orthonormal's two bargaining items. Spurious-counterfactual results: search summaries only.

Results (computed exactly unless marked proven), modal UDT searching utilities best to worst with ">= u":
- PD (6 payoff sets): vs itself cooperates; vs FairBot or PrudentBot both defect; exploits CooperateBot; vs a copy with a
  different action order both defect. PROVEN: never gets less than its maxmin payoff (never suckered).
- Stag Hunt: copies reach (S,S). Chicken: both swerve.
- Battle of the Sexes and coordination games: action labels decide the outcome; copies with different orders
  mis-coordinate at (0,0), even when one outcome is best for both.
- 600 random 2x2/3x3 games: identical copies miss an outcome best for both players in 71 of the 188 games that have one;
  cause: a spurious "I won't play a" proof at the lowest levels.

Caveats: cooperation only between copies of one exact spec; by 1401.5577 Thm 4.10 it cannot cooperate with FairBot while
exploiting CooperateBot. With ">= u" the fallback never fires (worst-utility check always provable); Fallenstein's "= u"
version can be suckered, including by FairBot when its fallback is C. Bounded version open: Critch's bounded Löb covers
FairBot-style agents only; no bounded analysis of modal UDT found.

## Correction (re-check at Kelvin's request)
Thm 4.10 verbatim: "Any modal agent X of rank 0 such that PA |- [X(FB)=C] must also have PA |- [X(CB)=C]." PrudentBot is rank 1, so
the theorem does not explain UDT vs PrudentBot; the earlier justification was wrong. The defection is still real
(trace_pb.py, hand-derived): at L1 UDT's first check "D -> I get T" passes vacuously, UDT plays D; PrudentBot/FairBot need
UDT=C at every lower level, so they defect from L2 on; UDT settles on D (worst utility) from L4. Stable outcome D,D.
In self-play both copies defect at L1, so "D -> T" fails for both at L2 and they settle on C,C. Encodings checked
against the paper (PrudentBot's PA+1 probe; u-order best to worst, C before D).

## Version 3 (tiered checks), tested at Kelvin's request (tables v3_tables.txt, sweep_v3.txt; code v3.py, trace_v3.py)
- V3-A (spec: exploit checks in PA+1, interleaved): defects vs FairBot/PrudentBot/original UDT in all 6 PDs; PA+1 checks are
  vacuous at L0 and L1, so the temptation check fires earlier. Cooperates with itself and reversed copy; defects vs DefectBot.
- V3-C/V3-D (exploit checks as "Con(PA) and PA proves"): cooperate with original UDT, itself, copy; still defect vs FB/PB.
- V3-B (exploit checks only after all cooperative/neutral checks, PA+1): cooperates with FairBot, PrudentBot, itself, reversed
  copy; defects vs DefectBot; in all 6 PDs. But in the PD its exploit check is dead code (after the always-provable
  "D gives >= 1"), so it reduces to "cooperate iff PA proves C -> they C": cooperates with CooperateBot. Consistent with
  Thm 4.10 (rank-0 agent provably cooperating with FB must cooperate with CB); matching PrudentBot needs a third-party probe.
- Other games: Stag Hunt S,S; Chicken Sw,Sw among themselves but exploit FB/PB; BoS/coordination still mis-coordinate vs
  reversed copy.
- Never suckered (proven with a maxmin floor; without it V3-B was suckered once).
- Copies missing a Pareto-best outcome (188/600 games have one): V3-B 24 (13%), V3-A 20, V3-C 21, V3-D 20, original 71 (38%).
