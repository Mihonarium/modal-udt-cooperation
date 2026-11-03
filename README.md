# Modal UDT and program equilibrium: can a payoff-reading agent cooperate like PrudentBot?

A small, exact study of agents that read each other's source code, in the framework of Bárász, Christiano,
Fallenstein, Herreshoff, LaVictoire and Yudkowsky, "Robust Cooperation in the Prisoner's Dilemma: Program
Equilibrium via Provability Logic" ([arXiv:1401.5577](https://arxiv.org/abs/1401.5577)).

The question: can an agent that takes the **payoff matrix as input** and searches outcomes from best to worst
("modal UDT") cooperate with FairBot, PrudentBot and itself, avoid exploitation by DefectBot, and work in general
two-player games?

**Two kinds of agent in this repo.** Everything up to "What this does and does not settle" is about
IDEALISED agents: formulas of provability logic whose boxes mean unbounded provability in PA. They are
evaluated exactly (below); they are not programs and cannot be run. Runnable bounded bots, real programs that
read the opponent's source and search for proofs within a budget, are in the section "Bounded agents".

## How the evaluation works (idealised agents)

Agents are formulas of provability logic (GL): "play a if PA proves φ", where φ talks about the opponent's action.
Such agents have unique fixed points, and their joint play can be computed **exactly** by evaluating along the
Kripke chain of GL: level n "sees" all levels below it, `Box_k φ` (provability in PA+k) is true at level n iff φ is
true at every level m with k ≤ m < n. Every closed formula is eventually constant along the chain, and that value is
its truth value in the standard model. `modal.py` implements this; no proof search is needed.

Checks: `test_paper.py` reproduces the paper's outcomes (FairBot/PrudentBot/CooperateBot/DefectBot, PrudentBot vs
CooperateBot from PA+2, PrudentBot with a PA probe losing self-cooperation); `test_naive.py` checks the evaluator
against the literal definition on 5,880 pairings.

## Results (idealised agents)

**Greedy modal UDT** (check "if I play a, I get at least u" for u from best to worst):
- Prisoner's Dilemma: cooperates with an identical copy; **defects against FairBot and PrudentBot**; exploits
  CooperateBot; defects against a copy that orders actions differently. Never gets less than its maxmin.
- Why it defects against PrudentBot: its first check, "if I defect I get the temptation payoff", passes vacuously
  at level 1 (it has never defected below level 1), so it defects once; PrudentBot and FairBot need its cooperation
  at every lower level, so they defect from then on (`trace_pb.py`).

**Version 3**, tiered checks (`v3.py`). Label each outcome (my payoff u, theirs v) with maxmins m_me, m_opp:
cooperative if u ≥ m_me, v ≥ m_opp and one is strictly better; exploitative if v < m_opp; neutral otherwise.
- V3-A (exploit checks in PA+1, interleaved by utility): fails; PA+1 checks are vacuous at levels 0 and 1, so the
  greedy defection fires even earlier.
- **V3-B** (all cooperative and neutral checks first, in PA, best u to worst; then exploitative checks in PA+1;
  checks below my maxmin dropped; fallback = maxmin action): cooperates with FairBot, PrudentBot and itself, and
  defects against DefectBot, in all 6 PD payoff sets tried. But in the PD its exploit check never runs, so it
  reduces to a FairBot variant and also cooperates with CooperateBot. That matches the paper's Thm 4.10: "Any modal
  agent X of rank 0 such that PA⊢[X(FB)=C] must also have PA⊢[X(CB)=C]." Exploiting CooperateBot needs a probe like
  PrudentBot's (how does the opponent play against DefectBot).
- Other games: Stag Hunt reaches (S,S); Chicken (Sw,Sw) among these agents, though they take advantage of FairBot
  and PrudentBot; **Battle of the Sexes and coordination games mis-coordinate** when two copies order equally good
  actions differently. Over 600 random 2x2/3x3 games, copies miss an outcome that is best for both players in 13% of
  the games that have one (V3-B), against 38% for greedy modal UDT.
- Never suckered: no version ever gets below its own maxmin (guaranteed by dropping checks below it).

**Version 4**, V3 plus a probe read off the payoffs (`v4.py`). It is rank 1: it asks how the opponent plays
against a third agent, which the paper's Thm 4.10 makes necessary for an agent that exploits CooperateBot.
- For each cooperative outcome o = (a, b) with my payoff u, let a_ex(b) be my best response to b, and Ex_b the
  constant agent that plays it.
- Cooperative check: PA proves "if I play a, I get at least u", AND PA+1 proves "the opponent does not play b
  against Ex_b". The probe is skipped when a is already a best response to b (nothing to exploit).
- Then exploitative checks, in PA+1: "if I play a, I get at least u". Then neutral checks, in PA.
- Checks below my maxmin are dropped; the fallback is the maxmin action.
- In the PD this is exactly PrudentBot's test: cooperate if PA proves my cooperation brings theirs, and PA+1
  proves they defect against DefectBot.

Results:
- **PD, all 6 payoff sets, both seats: V4 reproduces PrudentBot's whole row**: C,C with FairBot, PrudentBot,
  itself, a copy with a different action order, and V3-B; D,D with DefectBot and with greedy modal UDT; and it
  exploits CooperateBot (D,C), from PA+2 on, as PrudentBot does (`test_v4.py`, `trace_v4.txt`).
- The variants (probe in PA+2, exploit checks gated on a failed probe, exploit checks last) give the same PD row.
- Other games: Stag Hunt (S,S) with everyone; Chicken (Sw,Sw) with itself, V3-B and greedy UDT, while it takes
  advantage of FairBot and PrudentBot; **Battle of the Sexes and coordination games still mis-coordinate** with a
  copy that orders equally good actions differently (`v4_tables.txt`).
- 600 random 2x2/3x3 games (`sweep_v4.txt`): never below its own maxmin against any opponent (0 cases; guaranteed
  by the floor). Two copies miss an outcome that is best for both players in 22 of the 188 games that have one
  (12%), against 13% for V3-B and 38% for greedy modal UDT.

## What this does and does not settle (idealised agents)

- In the unbounded modal setting, a payoff-reading agent can get FairBot-style cooperation in the PD if exploitative
  checks are tried last (V3-B), and PrudentBot's full behaviour if it also probes the opponent against the
  constant exploiter its payoffs define (V4). In the PD, V4 then behaves like PrudentBot.
- **Equilibrium selection is unsolved**: in games with several good outcomes, the result depends on how each agent
  orders them. A shared ordering (for example the Nash bargaining solution, with ties broken by something both can
  compute) is the natural next step; it is not tested here.
- The bounded case: see "Bounded agents" below (theory with PROVEN/ARGUED/OPEN labels, and runnable bots in a
  small exact proof system, which is not Peano Arithmetic).

Sources on modal UDT write-ups (Fallenstein, Slepnev, orthonormal) were seen only through summaries, not read directly.

## Bounded agents

> **Correction (2026-11-03): the tournament below breaks the program-equilibrium rules.** In program equilibrium
> each program receives only the opponent's source and returns an action. Here the bots instead call a primitive
> `prove(...)` supplied by `bounded.py`: the library builds one BPC system per match (`lang` canonicalises the pair
> of sources, `SYSTEMS` caches it), and both bots query that same environment-supplied object. That is an oracle
> outside the rules. The results below are kept, but they only show cooperation among bots that **share one
> prover supplied by the environment**; they do not show that self-contained programs cooperate.
> The rebuilt version that follows the rules is in "Self-contained bots" below.

Question: can FairBot, PrudentBot and V4 be written as real programs that search for proofs up to a budget k,
as in Critch, "Parametric Bounded Löb's Theorem and Robust Cooperation of Bounded Agents"
([arXiv:1602.04184](https://arxiv.org/abs/1602.04184), read directly), and do idealised agents cooperate with them?

**Short answer.**
- Idealised vs bounded: an idealised agent treats any bounded (always-halting) bot as the constant bot that plays
  the bot's actual moves (PROVEN, below). So idealised FairBot cooperates with FairBot_k exactly when FairBot_k
  cooperates with it, which by Critch's bounded Löb happens for every large enough k (ARGUED; the threshold is not
  computed by anyone). Idealised PrudentBot cooperates with a bounded bot iff the bot cooperates with it and defects
  against DefectBot.
- A faithful implementation (bots searching Peano Arithmetic proofs by length in characters) is not runnable:
  the Löbian cooperation proof is far longer than any exhaustive search can reach (ARGUED below). What runs here
  is a weaker but exact substitute: bots are real programs, read the opponent's source and search a small formal
  system completely up to a budget; the budget counts nested necessitations, not characters. Differences are
  listed under "How this differs from Critch".

### Theory

Notation: □φ "PA proves φ"; □_k φ "PA proves φ with a proof of at most k characters"; FB_k, PB_k, V4_k are
FairBot, PrudentBot and V4 with every "PA proves" replaced by "a proof of at most k characters is found".
Critch's Properties 1-4 (implication distribution with constant overhead, quantifier distribution with lg k
overhead, bounded necessitation and bounded inner necessitation with an expansion function E) are assumptions
about the proof system that he states with proof sketches only; everything ARGUED below inherits them.

1. **Bounded vs bounded (Critch's theorems).** PROVEN in arXiv:1602.04184 under Properties 1-4:
   - Thm 3 (parametric bounded Löb): if f is computable with f(k) ≻ E(O(lg k)) and
     ⊢ ∀k (□_{f(k)} p(k) → p(k)), then ⊢ ∀k > k̂, p(k) for some k̂.
   - FB_k vs FB_k cooperates for all k > k̂ (Sec. 6, p(k) = "FB_k(FB_k) = C").
   - Thm 4: if E(O(lg k)) ≺ k, f satisfies E(O(lg k)) ≺ f(k) ≺ k, and G(ℓ) > 6 f(2ℓ), then any two G-fair agents
     A_m, B_n (⊢ □_{m+G(len Opp)}[Opp(A_m) = C] → A_m(Opp) = C) cooperate for all m, n above a threshold r.
     Note the budget must grow with the opponent's code length (G); fixed budgets are not covered.
   - OPEN: the size of k̂ and r for any concrete proof system; behaviour below them (cooperation need not be
     monotone in k, since a different k is a different sentence).
   - PB_k is not G-fair (its cooperation also needs the probe). ARGUED: the probe "PA+1 proves X(DB) ≠ C" has a
     PA+1 proof of length c + O(lg j) for X = FB_j, PB_j, V4_j ("X(DB) = C would need a PA proof that DB cooperates;
     PA proves DB defects; PA is consistent"), so for budgets above that the probe holds outright and the
     Critch argument goes through with p = mutual cooperation. Not checked by anyone else.

2. **Idealised vs bounded.**
   - Collapse lemma, PROVEN (standard): if X always halts (every bounded proof searcher does), the sentence
     "X(Y) = a" is decided by PA: PA proves it when true (Σ1-completeness, the run is a finite computation) and
     proves its negation when false (the run halts with another action). PA is sound, so within any box,
     "X(Y) = a" can be replaced by ⊤ or ⊥ according to X's actual move. Hence an idealised agent plays against X
     exactly as against the constant bot that plays X's actual moves (against it and against any probe).
   - Consequences, PROVEN: idealised FB(X) = C iff X(FB) = C. Idealised PB(X) = C iff X(PB) = C and X(DB) = D
     (PA+1 proves "X(DB) = D" iff it is true). Idealised V4 vs X: the existing evaluator with X replaced by
     constants.
   - So everything hinges on what the bounded bot does against the idealised one. FB vs FB_k: let
     q_k := "FB_k(FB) = C". Then ⊢ q_k ↔ □_k □q_k. ARGUED: ⊢ ∀k (□_{f(k)} q_k → q_k) whenever
     E(f(k)) + O(lg k) < k eventually (from □_{f(k)} q_k: bounded inner necessitation gives □_{E f(k)}□_{f(k)} q_k;
     the uniform short proof of □_{f}φ → □φ and implication distribution give □_{E f(k)+O(lg k)} □q_k, which is
     q_k). Thm 3 then gives q_k for all k > k̂, and with it FB(FB_k) = C. Equivalently: idealised FB is G-fair for
     every G, so Thm 4's argument applies with an unbounded budget on its side. Cooperation for small k fails
     trivially (no proof that short exists): PROVEN. The same argument with the probe (item 1) covers idealised PB
     vs PB_k and idealised PB vs V4_k (ARGUED).
   - So the answer to "can idealised agents cooperate with bounded ones" is yes, for budgets above an unknown
     threshold; the idealised side is never the obstacle, because it simply mirrors.

3. **Payoff-reading agents (V4_k) and short spurious proofs.**
   - Floor, PROVEN (soundness of PA, PA+1): a check that fires is a real proof of "I play a → my payoff ≥ u" and
     the bot then plays a, so its payoff is ≥ u ≥ its maxmin; the fallback is the maxmin action. V4_k is never
     suckered, for every k.
   - Vacuous passes, PROVEN harmless: a check "⊢_k V4_k(X) = a → ..." can pass vacuously through a short proof of
     V4_k(X) ≠ a. But if it is the first check to pass, V4_k plays a, contradicting a sound proof; so a vacuous pass
     can only happen to a check after the one that fires, and never changes the action. (In the idealised
     Kripke evaluation the same thing shows up as greedy UDT's level-1 artefact.)
   - Order of checks in the PD, PROVEN: every check after the cooperative one (exploit in PA+1, neutral, fallback)
     plays D, so the order among them cannot matter; below its cooperation threshold V4_k simply defects through the
     trivially provable neutral check "D → payoff ≥ P".
   - Cooperation without Löb, ARGUED for PA (computed in BPC): V4's cooperative check is an implication, "if I
     cooperate, the opponent cooperates". Against FB_m, if V4_k cooperates then a proof of that fact of length about
     E(k) exists (bounded Σ1-completeness, as in Critch's Property 4). So when m exceeds that length, the implication
     has a short uniform proof and no Löbian fixed point is needed. The budgets must be ordered the right way: FairBot
     must out-budget V4.
   - New failure mode with several cooperative outcomes, ARGUED/OPEN: a lower-ranked cooperative check whose proof
     is shorter can fire at budgets where the better outcome's Löbian proof is not yet within reach, so equilibrium
     selection becomes budget dependent. Not tested here (PD only).

### Was a faithful implementation possible?

No, not for PA with proof length in characters. A FairBot_k that enumerates PA proofs of ≤ k symbols runs in
time |Σ|^k. The shortest proof of "FB_k(FB_k) = C" contains the diagonal (fixed-point) construction for the bots,
the Gödel encoding of the bounded provability predicate and Critch's argument; any written-out version is at least
thousands of symbols (ARGUED, rough estimate; no one has computed it). Exhaustive search stops at k ≈ 10-15,
where such bots would find no proof about another bot's behaviour (ARGUED) and so defect against everyone,
CooperateBot possibly included. Lean is not available here and was not installed; no existing bounded prover for this
setting was found.

### What was built (`bounded.py`)

- **Bots are programs.** A bot is source text, for example FairBot with budget 2:
  `C if prove(0, 2, opp(self) == C)` / `D otherwise`; PrudentBot adds `and prove(1, 2, opp(CONST_D) != C)`;
  V4 is `V4 budget=2 probe=1`, which reads the payoff matrix at run time and builds its checks as in `v4.py`.
  `bounded.act(game, X_source, Y_source, role)` runs bot X against bot Y and returns its action.
- **The formal system, BPC** (a "bounded provability calculus", one per match, built from the two sources):
  propositional formulas over action atoms [X|Y=a] ("program X outputs a against Y"), box atoms
  Box_n^t φ ("φ has a derivation of height ≤ n", t = 0 base theory, t = 1 base plus consistency, the analogue of
  PA+1) and Löb-shaped fixed points ψ ↔ (Box_g ψ → T), T a joint action of the match.
  Axioms: Unf (a bot's action is what its decision list returns, read off its source); FP (the fixed points);
  Mono, Incl, Four (Box_n ψ → Box_{n+1} Box_n ψ), FPBox/KFP (distribution through the fixed points), Ent (boxes are
  closed under propositional consequence of box-free contents), Sigma1 and UnfBox (a box-positive condition that
  holds is provable), and in theory 1, Con (the base system proves no contradiction).
  Rules: propositional consequence (free) and necessitation (height + 1). Height = number of nested
  necessitations; this is the budget k.
- **Genuine search, no answers added.** No axiom states any bot's output; Unf only says how a bot's output
  depends on what is provable. Each axiom is a true statement
  about the programs and the calculus; `bounded.audit` re-checks every axiom of every match system against the
  bots' actual outputs and the actual derivability relation, and the tournament audits all 400 systems. The
  fixed points are only definitions; cooperation, where it happens, is derived by the search from them (Löb's
  argument, found by the solver, not supplied).
- **Exact and complete for BPC.** With necessitation restricted to the finitely many formulas that occur in boxes,
  the set of derivable formulas at each height is finite; it is computed exactly with a small DPLL solver
  (propositional consequence) layered by height. So "budget k" means: every BPC proof of height ≤ k is
  considered.

### How this differs from Critch

1. Budget = necessitation height, not characters. Propositional reasoning is free. As a result the cooperation
   thresholds are tiny (the Löb argument needs one or two nested necessitations), whereas Critch's k̂ is the
   character length of a Löb proof in PA.
2. BPC is not arithmetic. It has no diagonal lemma, only the Löb-shaped fixed points for the joint actions of
   the match, and necessitation only for formulas that occur in boxes. Proofs outside that fragment do not exist
   in BPC, so a BPC bot is weaker than a PA bot with the same "budget" idea.
3. The facts PA would prove about provability (distribution, inner necessitation, Σ1-completeness, consistency of
   the base system for theory 1) are axioms here, at zero cost, because they are true of BPC; in PA they are
   theorems with length costs (Critch's E and c).
4. Program semantics is the Unf axiom: the system reads the decision list off the source. V4's payoff analysis is
   executed when unfolding, not proved.
5. Each match has its own system, generated by the two sources (probes against constant bots get their own
   sub-systems). A bot's "PA" is therefore the system of its current match.
6. Idealised PA agents cannot be placed inside BPC (their box means PA-provability). The "inf" budget bots below
   are unbounded BPC bots, which are computable because the system is finite; they reproduce the exact GL
   outcomes for FB, PB, V4, CB, DB (`test_bounded.py`).

### Tournament with a shared, environment-supplied prover (`run_bounded.py`, `bounded_tables.txt`, `bounded_results.json`)

These results are under the shared-prover setup described in the correction at the top of this section.

Row bot's action first. Budget = necessitation height in BPC; "inf" = unbounded BPC search (computable here).

```
Bounded PD tournament (row player's action first; 400 runs, 2464s wall). Budget = necessitation height in BPC.

          FB0   FB1   FB2   FB3   FB4 FBinf   PB0   PB1   PB2   PB3   PB4 PBinf  V4_0  V4_1  V4_2  V4_3  V4_4V4_inf    CB    DB
FB0        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    CC    DD
FB1        DD    CC    CC    CC    CC    CC    DD    DD    DD    DD    DD    DD    CC    DD    DD    DD    DD    DD    CC    DD
FB2        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FB3        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FB4        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FBinf      DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
PB0        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
PB1        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
PB2        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PB3        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PB4        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PBinf      DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_0       DD    CC    CC    CC    CC    CC    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
V4_1       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DC    DD
V4_2       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_3       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_4       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_inf     DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
CB         CC    CC    CC    CC    CC    CC    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CC    CD
DB         DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD

soundness audit: 0 false axioms over all 400 match systems
row bot (other than CB) cooperates while the opponent defects: never
```

What the table shows (all computed; thresholds are in BPC's height measure, not characters):
- Bounded vs bounded: FB_k and FB_m cooperate iff k, m ≥ 1 (the Löb argument needs one necessitation, see
  `trace_bounded.txt`). PrudentBot needs one more, for the probe: PB_k and PB_m cooperate iff k, m ≥ 2, and
  FB_k with PB_m iff both ≥ 2. V4_k and V4_m cooperate iff both ≥ 1 and one is ≥ 2; PB_k with V4_m iff k ≥ 2,
  m ≥ 1. Budget 0 cooperates only with CooperateBot (FairBot) or with FairBot_{≥1} (V4, next point).
- Budgets interact and smaller can be better. V4_0 cooperates with FB_1 but V4_1 does not. V4's check "if I
  cooperate, FairBot cooperates" is provable without Löb whenever FairBot's budget exceeds the height needed to
  verify V4's own cooperation (Sigma1). So FairBot must out-budget V4, which echoes Critch's requirement that the
  budget grow with the opponent (G-fairness).
- Idealised (unbounded BPC) vs bounded: FB_inf cooperates with FB_k (k ≥ 1), PB_k (k ≥ 2) and every V4_k;
  PB_inf with FB_k, PB_k (k ≥ 2) and V4_k (k ≥ 1); V4_inf with FB_k, PB_k (k ≥ 2) and V4_k (k ≥ 1). Below those
  budgets both sides defect. In every case the unbounded side just mirrors (collapse lemma).
- PrudentBot_k and V4_k exploit CooperateBot at every budget, including 0 (the probe fails because CooperateBot does
  cooperate with DefectBot). FairBot_k cooperates with it. Everyone defects with DefectBot.
- No proof-based bot ever played C against D (soundness). The audit found 0 false axioms in all 400 match systems,
  and the unbounded bots match the exact GL evaluator on all 25 pairings of FB, PB, V4, CB, DB.
- Not tested: other games, other payoff sets, larger budgets (K = 4 is the largest finite index in the language;
  everything is constant from k = 2 on).

Run: `python3 test_bounded.py && python3 run_bounded.py 10 && python3 trace_bounded.py` (Python 3, no
dependencies; the tournament takes about 2.7 CPU-hours (41 min wall with 4 workers) of CPU, run at low priority).

## Self-contained bots (program-equilibrium rules)

Rules (Kelvin, 2026-11-03): each bot receives only the opponent's source code; a bot may carry its own prover in
its own source, "but then that is all". The environment gives each program the other's source string and reads
back an action.

**What was built** (`pe_bot.py`, `pe_env.py`, `pe_run.py`, `pe_test.py`):
- **One source string per bot.** `pe_env.make_bot(spec)` produces `CODE = '<text>'` / `exec(CODE)`, where the text
  is a `SPEC = ...` line (the decision list, as before: FairBot, PrudentBot or `V4 budget=k probe=1`) followed by
  the whole of `pe_bot.py`: its own copy of BPC, the SAT solver, the height-layered search, the PD payoffs and the
  source analysis. Only the Python standard library is imported. A bot gets its own source by quining
  (`SELF = "CODE = %r\nexec(CODE)\n" % CODE`); nothing tells it its own source.
- **The environment** (`pe_env.run`) starts a fresh `python3 -I -B -c <source>` per program run, writes the
  opponent's source to stdin and reads one line (C or D) from stdout; empty environment, working directory `/`,
  limits 3600 s CPU and 5 GiB address space. A match is two such runs; self-play is two separate runs of the same
  source. No cache, file or object is shared between runs; each run builds its own match system from scratch.
- **Facts about the opponent come from reading its source.** The bot recognises exactly two forms:
  `print("C")` / `print("D")` (a constant program), and the form `CODE = '<SPEC line + text>'` / `exec(CODE)`
  whose text after the SPEC line is character-for-character its own prover. For the second form it writes the
  Unf axiom itself: the opponent's action is what the opponent's decision list returns, with each `prove(t, n, F)`
  read as derivability at height n in the same calculus (true because the code is identical and deterministic and
  builds the same match system; ARGUED, and checked by the audit below). Any other source is unknown: no Unf axiom,
  so nothing about its action is provable and the proof-based bots defect against it (`pe_test.py` checks this
  for FairBot_2 against FairBot_2's source with an extra trailing newline).
- **Atoms have no roles.** The old library tagged each atom with a seat (row/column). A program here receives only
  the opponent's source, so "X's action against Y" is one computation and one atom. In self-play "my action" and
  "the opponent's action" are therefore the same atom.
- **Audit (experimenter side, not seen by bots).** `pe_run.py` rebuilds every match system from the prover text
  and checks each axiom against the actual outputs of the separate runs and the actual derivability relation.

**Tournament** (`pe_tables.txt`, `pe_results.json`; COMPUTED). Identical embedded provers, same population and
budgets as before. Row bot's action first.

```
          FB0   FB1   FB2   FB3   FB4 FBinf   PB0   PB1   PB2   PB3   PB4 PBinf  V4_0  V4_1  V4_2  V4_3  V4_4V4_inf    CB    DB
FB0        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    CC    DD
FB1        DD    CC    CC    CC    CC    CC    DD    DD    DD    DD    DD    DD    CC    DD    DD    DD    DD    DD    CC    DD
FB2        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FB3        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FB4        DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
FBinf      DD    CC    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    CC    DD
PB0        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
PB1        DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
PB2        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PB3        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PB4        DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
PBinf      DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_0       DD    CC    CC    CC    CC    CC    DD    DD    DD    DD    DD    DD    CC    DD    DD    DD    DD    DD    DC    DD
V4_1       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_2       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_3       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_4       DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
V4_inf     DD    DD    CC    CC    CC    CC    DD    DD    CC    CC    CC    CC    DD    CC    CC    CC    CC    CC    DC    DD
CB         CC    CC    CC    CC    CC    CC    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CD    CC    CD
DB         DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DD    DC    DD
```

What it shows:
- COMPUTED: 398 of 400 cells are identical to the shared-prover table. The two differences are V4_0 and V4_1 in
  self-play, DD before and CC now. Reason: without roles, V4's cooperative check "if I play C the opponent plays C"
  is, against an exact copy of itself, the tautology [X|X=C] → [X|X=C], provable at height 0; with the old
  seat-tagged atoms it was a statement about two different atoms and needed the Löb argument. V4's probe (a copy of
  V4 would not cooperate with DefectBot) is already provable at budget 0 (as in V4_0 vs FB_1), so V4_0 and V4_1
  cooperate with themselves. This is a change of language (seat-free atoms, which the rules call for), not an effect
  of separating the provers. FairBot and PrudentBot self-play are unchanged.
- COMPUTED: soundness audit, 0 false axioms among 1,013,618 axioms of the 210 match systems; no proof-based bot
  played C against D; every one of the 420 runs produced a valid action within the limits (longest 55 s, peak
  memory under 55 MB); the two separate self-play runs agree for every bot.
- PROVEN (by construction): no prover object, cache or file is shared between the two players; the only thing
  that passes between them is the opponent's source string.
- So with identical embedded provers, the cooperation results of the shared-prover version survive the move to the
  program-equilibrium rules: the shared oracle was not doing the work, the shared prover CODE is.
- Cost: 420 runs in 936 s wall and the audit in 949 s wall, 4 worker processes, run at low priority.

**Not done yet (future work).** Bots whose provers differ: (a) the same logic with a trivially different but
equivalent implementation (renamed variables, reordered code), and (b) a genuinely different sound prover (other
axioms or another budget measure). The current bots recognise only their own prover text exactly, so in case (a)
they would treat the opponent as unknown and defect (the trailing-newline test above is one instance); cooperation
there needs a bot that proves the other prover equivalent to its own, or reasons about it by other means. Not
tested yet.

Run: `python3 -B pe_test.py && python3 -B pe_run.py 4` (Python 3, no dependencies; tests about 14 min, tournament
plus audit about 31 min wall with 4 workers).

## Files

- `modal.py`: exact evaluator, FairBot, PrudentBot, constant bots, greedy modal UDT.
- `v3.py`: Version 3 variants. `v4.py`: Version 4; `test_v4.py` asserts PrudentBot's PD row; `run_v4.py`:
  V4 tournament (`v4_tables.txt`, `sweep_v4.txt`, `v4_results.json`); `trace_v4.py` -> `trace_v4.txt`. `run.py`, `run_v3.py`, `sweep*.py`: tournaments; outputs in `*.txt`, `*.json`,
  `tables.md`. `trace*.py`: level-by-level traces. `NOTES.md`: working notes with corrections.

- `bounded.py`: runnable bounded bots and the calculus BPC (parser for bot sources, exact height-bounded
  derivability with a DPLL solver, soundness audit). `test_bounded.py`: unbounded bots vs the GL evaluator, audits,
  budget-0 and unexploitability checks. `run_bounded.py` -> `bounded_tables.txt`, `bounded_results.json`.
  `trace_bounded.py` -> `trace_bounded.txt` (height at which each fact becomes derivable).
- `pe_bot.py`: the body of a self-contained bot (prover, source analysis, decision); embedded in every bot source,
  never imported. `pe_env.py`: bot sources and the environment (one fresh interpreter per run). `pe_run.py` ->
  `pe_tables.txt`, `pe_results.json` (tournament and audit). `pe_test.py`: tests for the self-contained bots.

Run: `python3 test_paper.py && python3 test_v4.py && python3 run_v4.py` (Python 3, no dependencies).
