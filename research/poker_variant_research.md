---
title: "Fast Probabilistic Play in Three-Card Discard-and-Reveal Hold'em"
subtitle: "Research and implementation handoff for the NO LIMIT '26 Bay Area variant"
author: "Technical strategy memorandum"
date: "6 November 2026"
geometry: margin=0.8in
fontsize: 10pt
colorlinks: true
linkcolor: NavyBlue
urlcolor: NavyBlue
toc: true
toc-depth: 2
---

# 1. Executive recommendation

Build a **small stochastic policy with a strong legal-action adapter**, three-way retained-pair comparison, selection-aware one-card opponent ranges, and a handful of tunable parameters. Train or calculate expensive quantities outside gameplay, ship them as read-only data, and make each decision using bounded feature extraction and table lookups. Use richer computation only after its worst-case cost has been measured on the supplied build box.

The central engineering target is not merely a fast average decision. The upload test uses a 1 ms allowance with no time bank, while the production clock includes request delivery and response overhead. A strategy that frequently relies on the 100 ms table bank is not a robust initial submission. Local play always supplying a bank can conceal this defect.

This memorandum proposes a design; it does **not** report a trained equilibrium, an experimentally winning bot, or a measured sub-millisecond implementation. Numerical knobs explicitly labeled as initial settings are hypotheses for testing. The starter kit, actual state schema, round logs, and tournament hardware were not supplied here. Both pasted rule documents and the live format supplied in the conversation were read.

## 1.1 The most valuable ideas, in implementation order

1. **Never lose a hand to an invalid action or stale memory.** Use `state.can`, legal raise-to bounds, actual configuration, and a phase-specific fallback.
2. **Choose among the three retained pairs using future strength, not only current made-hand category.** The second choice is which retained card to reveal. Start with a fair random reveal if there is no tested information model.
3. **Remove all known unavailable cards.** This includes all three of your originally dealt cards, every public board card, and exposed cards belonging to players who subsequently folded.
4. **After selection, model each opponent's one hidden retained card.** Conditioning on their exposed card reduces the range dimension considerably. Do not assume the hidden card is uniform: deliberate retention, revelation, and betting all select the range.
5. **Estimate equity against continuing ranges.** A player's distribution after calling your large bet is different from their distribution before the bet.
6. **Use a compact distribution over fold/check, call, small raise, large raise, and jam.** Remove illegal and clearly dominated choices before sampling. Randomization is concentrated near plausible decisions.
7. **Optimize tournament points.** Near elimination and the three-paid-place bubble, approximate ICM utility can disagree sharply with chip EV. Read actual payouts from the state.
8. **Separate learning timescales.** Inside a table, update a few shrinkage-based opponent statistics. Between uploads, tune a small parameter vector using logs and paired local tournaments. Do not carry table identities or memory across live tables.

## 1.2 What to send the coding agent immediately

Use this architecture:

```
request + memory
    -> defensive decode + incremental public-event update
    -> phase-specific legal-action mask
    -> compact features / precomputed estimates
    -> candidate action values or threshold scores
    -> conservative mixed distribution
    -> integer raise-to conversion + final validation
    -> action + bounded serialized memory
```

Start with a five-action abstraction, 10-15 global tuning parameters, and table-local Beta counts for fold-to-bet. Keep raw hand evaluation separate from equity calibration. Never evaluate all three private cards as though all three remain legal after selection. Never allow simulated opponents to choose their flop discard using the realized turn and river.

# 2. Rules, objective, and implementation constraints

## 2.1 Information sequence

Each player receives three private cards and participates in preflop betting. The flop is dealt. Every non-folded player, including all-in players, simultaneously chooses a discard and an exposed retained card. The third card remains hidden. The discard stays dead and private. Normal flop, turn, and river betting then follows. At showdown the retained pair plays as in hold'em: zero, one, or two hole cards may appear in the best five-card hand.

The selection action is an ordered pair of original indices:

$$a_{\mathrm{sel}}=(d,r),\qquad d,r\in\{0,1,2\},\quad d\ne r.$$

There are six choices. The action has zero amount. The published example is `Action("select", cards=(2, 0))`. After selection the two retained cards are in their original relative order, not necessarily exposed-card-first. Identify the exposed card by card identity using public state.

Submission order does not reveal earlier choices. The strategy at selection must condition only on information available before the simultaneous revelation. A simulator that lets later seats react to earlier selections changes the game.

## 2.2 Which supplied rules control which assumptions

The general attached rules differ from the event-specific pages. This memorandum treats the supplied getting-started guide as the more specific runtime description and the supplied format as the default competition description. The actual table configuration and organizer announcements remain authoritative.

| Item | General attachment | Event-specific supplied pages / action |
|---|---|---|
| Hand cap | 200 | Format says 250; read `state.config.hand_cap` |
| Blind increase | Every 25 hands | Format says 20; read schedule and actual level |
| Scored iterations | 10,000 | Format says at least 5,000 |
| Upload size | 100 MB | Guide says 50 MB compressed, 200 MB unpacked |
| Upload cadence | Five minutes | Guide says 30 seconds |
| Activation | Latest accepted active | Format says manually select ready; guide says accepted usually activates automatically; verify active status |
| Payouts | Variant dependent | Default 50/30/20, but guide says tables can draw different payouts |
| Timing | 1 ms | Configurable decision allowance; upload test default 1 ms, no bank |

A configuration-driven implementation avoids making strategy depend on these discrepancies. Do not infer the precise future blind amounts merely from the starting 10/20 blinds or level interval.

## 2.3 Tournament utility

For default payouts, a table result $Y$ lies in $[0,50]$. Eliminations assign place points; survivors at the cap receive ICM allocation of the unassigned places. For rounds $k=1,\ldots,6$, the final score is

$$J=\sum_{k=1}^{6}k\,\mathbb E[Y_k].$$

A round starts at build time $60+20(k-1)$ minutes. Round 6 therefore starts at minute 160, not minute 180. Result availability can lag the next start, so do not assume round $k$ feedback arrives in time for round $k+1$.

The weights total 21. Round 6 has $6/21\approx28.57\%$ of total weight, and rounds 4-6 have $15/21\approx71.43\%$. A stable early bot is valuable, but later improvements matter greatly. A missed active snapshot produces a certain zero for that round; avoid betting the submission deadline on an unvalidated rewrite.

## 2.4 Runtime facts that change algorithm selection

The supplied guide specifies Python 3.12, approved packages including eval7 and several ML libraries, no network/GPU, and a read-only non-executable bot directory. Uploaded compiled extensions cannot load. Existing installed native libraries can still provide fast operations; these are different from shipping a custom binary. Import-time models should be loaded and warmed before forking copies, but thread pools created during import do not survive normally into worker copies.

`self` and mutable globals are not a reliable table store. Any process can answer any table. Immutable imported tables are useful; learning state belongs in `memory`, initially empty at each table, with a default 64 KB cap. The guide reports that about 16 KB has no measurable transport cost in their setup, but this is not a guarantee that parsing 16 KB is free inside a 1 ms budget. Aim substantially smaller first.

No computation between decisions and no persistent files between tables are allowed. Train offline on the build machine between rounds, then upload a fixed artifact. There is no need for online SGD, a background learner, or a file-based cache in the deployed bot.

# 3. Why this variant changes ordinary hold'em strategy

## 3.1 Three-card optionality strengthens the field

Before any betting selection, there are $\binom{52}{3}=22{,}100$ unordered starting triples. Direct combinatorial calculations give:

| Property of a uniformly dealt triple | Probability |
|---|---:|
| At least one ace | 21.74% |
| Contains a repeated rank, including trips | 17.18% |
| Contains at least two cards of the same suit | 60.24% |
| All three cards have the same suit | 5.18% |

For example, the repeated-rank probability is

$$\frac{13\binom42\,48+13\binom43}{\binom{52}{3}}=0.1717647\ldots$$

These are deal probabilities, not opening frequencies or showdown equities. Their strategic lesson is that familiar two-card baselines are not automatically calibrated. Opponents also get to discard their least useful card after seeing the flop. An ordinary pair can be less dominant against this selected field than against random two-card hands.

## 3.2 The third card is an option, not an extra showdown card

Let $T$ be the initial triple, $F$ the flop, and $K$ a retained pair. If $V(K,F)$ is continuation value for that pair, a simplified preflop value has the form

$$V_{\mathrm{pre}}(T)\approx\mathbb E_F\left[\max_{K\subset T,\,|K|=2}V(K,F)\right].$$

This is generally greater than choosing the pair before seeing the flop:

$$\mathbb E_F[\max_K V(K,F)]\ge\max_K\mathbb E_F[V(K,F)].$$

The inequality is an information-option effect. It does not imply that every triple has greater equity than every two-card hand, because the opponents' opportunities and selection policies also change.

A useful approximation starts with the best two-card component and adds **nonredundant** potential from the third card: alternative high-card pairing, connected ranks, and alternate suited combinations. Counting the same draw repeatedly inflates this bonus. Three same-suit cards leave only two retained and one dead, so they do not give three playable flush cards.

## 3.3 Revealing is a signaling decision

Two actions retaining the same pair have identical showdown card strength but potentially different betting value. Exposing an ace may generate more folds from simple bots. Exposing a card that visibly completes a draw may make value extraction harder. Concealing the important pair card may make your strength less obvious. These effects depend on opponents' inference.

A deterministic rule such as “always expose the smaller rank” has an exploitable implication: except for ties, your hidden card is at least as high as the exposed one. The reverse rule is informative too. A fair random reveal among the retained pair is a defensible baseline, but it does not hide all information: the retained pair was itself selected using the flop.

## 3.4 Known dead cards are part of the information advantage

Once your own triple has been dealt, all three cards are unavailable to opponents or future community cards, including your private discard. All exposed cards remain unavailable even after their owners fold. Unknown opponent discards are also physically dead, but their identities are latent.

There is a subtle distinction: if unobserved dead cards are exchangeable under the current information, marginalizing them can leave the future board uniform over otherwise unassigned cards. If discards depend on the flop or prior actions, that exchangeability can fail. Sampling a uniformly random runout after assigning retained hands is then an approximation, not exact Bayesian inference. This matters most when a small number of crucial outs are preferentially discarded.

# 4. A precise probabilistic model

## 4.1 Information sets and latent worlds

Write $I$ for everything the bot legitimately knows: private cards, own discard, board, public exposed cards, actions, stacks, positions, and table-local statistics. A latent world $\omega$ specifies the remaining private cards, opponent discards, future community cards, and any latent opponent strategy types.

The ideal action value is

$$Q(I,a)=\mathbb E_{\omega\sim p(\omega\mid I)}[U\mid I,a,\pi_{\mathrm{future}}].$$

$U$ is terminal tournament points or an approximation to continuation points. This definition includes future betting and strategy responses. A hand's all-in equity is only one input to $Q$, not the full value of checking, calling, or raising.

A fast bot approximates both the posterior and the continuation policy. Keeping those approximations explicit helps distinguish a calculation error from an imperfect model.

## 4.2 The exact conceptual selection likelihood

Let an opponent's exposed card be $x$, hidden retained card $h$, and discard $d$. Ignoring other players momentarily, the conceptual posterior is

$$\begin{aligned}
p(h,d\mid x,F,H) &\propto p(\{x,h,d\})L_{\mathrm{pre}}(H_{\mathrm{pre}}\mid\{x,h,d\})\\
&\quad\cdot\pi_{\mathrm{sel}}(d,x\mid\{x,h,d\},F,H_{\mathrm{pre}})\\
&\quad\cdot L_{\mathrm{post}}(H_{\mathrm{post}}\mid x,h,d,F).
\end{aligned}$$

Here $H$ is observed action history. Original dealing order must also be marginalized or represented if modeling index-dependent policies such as the default selection. The formula describes the structure; it is not a recommendation to enumerate everything inside `act`.

The one-card retained range is

$$p(h\mid x,F,H)=\sum_d p(h,d\mid x,F,H).$$

For an eight-player table, these seat ranges are coupled by card exclusion, common board, and action history. Multiplying seat marginals and renormalizing only for collisions is a useful approximation, not the exact posterior in general.

## 4.3 A practical one-card range

For each active opponent, maintain nonnegative weights over at most 52 candidate card IDs:

$$w_j(h)\propto\mathbf1\{h\text{ is available}\}\exp(\theta_{t_j}^{\mathsf T}\phi(x_j,h,F,H)).$$

Possible features are: made-hand category, pair relative to board, kicker, flush-draw membership, straight-draw participation, rank strength, preflop action category, and postflop action size. This can be implemented using a small lookup table instead of exponentials.

Shrink aggressive inference toward a broad prior:

$$q_j(h)=(1-\eta_j)q_{\mathrm{broad}}(h)+\eta_jq_{\mathrm{selected}}(h).$$

The broad prior must still respect unavailable cards. It can be uniform over legal hidden cards as a deliberately weak initial model. The selected component models deliberate pair retention and revelation. Start with modest $\eta_j$ until showdowns and behavior provide evidence. A mixed prior helps avoid the catastrophic conclusion that a particular strong hand is impossible when the opponent may simply use an unexpected selection policy.

## 4.4 An implementable teacher for selection-aware ranges

Offline, construct a small family of opponent selection policies:

- Default: discard last dealt, expose first dealt.
- Made-hand-first: maximize current five-card rank with draw-aware tie-breaking.
- Draw-aware: maximize a calibrated continuation score.
- Strong-card reveal: choose the same retained pair but expose the apparently stronger card.
- Weak-card reveal: expose the apparently weaker card.
- Random reveal: choose either retained card with equal probability.

For a public flop and observed exposed card $x$, enumerate or sample legal original triples containing $x$, run each candidate selection policy using only its own legal information, and retain the samples whose exposed outcome matches $x$. Accumulate hidden-card and discard frequencies. Weight policy types by a broad population prior and later by table-local evidence.

This procedure captures both selection and revelation bias. The offline result can be distilled into coarse conditional weights indexed by board texture, exposed-card relation, and preflop action. A full exact flop-indexed tensor is unnecessary for the first build.

# 5. Equity computation and its approximations

## 5.1 Correct multiway showdown equity

For a sampled complete runout, let $R_i$ be the hero's legal seven-card hand rank, using the retained pair plus board. Let $R_* = \max_j R_j$ among eligible opponents. Define sample share

$$X=\begin{cases}0,&R_i<R_*;\\1/(1+m),&R_i=R_*\text{ and }m\text{ opponents tie hero};\\1,&R_i>R_* .\end{cases}$$

Then $e=\mathbb E[X]$ is expected pot share when there is a single pot and the indicated players reach showdown. The estimator $\hat e=M^{-1}\sum_mX_m$ is bounded between zero and one. For side pots, calculate this share separately among each pot's eligible participants.

Calling a hand “70% equity” without specifying opponent count, ranges, known dead cards, and whether those are calling ranges is incomplete. Equities versus individual opponents do not generally multiply. Shared runouts, overlapping ranges, and mutually exclusive private cards introduce dependence.

## 5.2 Why river enumeration is unusually attractive

After the river, against one opponent with one exposed card, enumerate each legal hidden card $h$, evaluate its retained pair with the board, and weight the win/tie/loss result by $q(h)$. This is exact **conditional on the assumed one-card posterior**, and needs only dozens of opponent hand evaluations. It does not require enumerating 1,326 two-card combinations.

Multiple opponents still require a joint model for exact equity. A fast approximation ignores collisions and uses seat-level probabilities of losing to hero, $l_j$, and tying hero, $t_j$. The generating polynomial

$$G(z)=\prod_j(l_j+t_jz)$$

has coefficient $c_k$ equal, under this independence approximation, to the probability that no opponent beats hero and exactly $k$ opponents tie. Expected hero share is

$$e_{\mathrm{ind}}=\sum_{k\ge0}\frac{c_k}{k+1}.$$

This handles ties correctly within that model; simply multiplying heads-up equities does not. Card collisions remain a source of error. Use the approximation only if validated, or use small legal joint samples offline to train a better correction.

## 5.3 Sampling without accidental replacement or information leakage

A simulated world must assign all visible and private cards without duplicates. A simple operational approximation draws hidden cards sequentially from weighted ranges after removing already drawn cards, then draws runout cards. However, sequential renormalization is order-dependent and is not generally a sample from a normalized product-of-ranges distribution. Randomizing seat order reduces a particular ordering artifact but does not make the sampler exact.

If the desired approximation is the product of per-seat weights conditioned on no collision, independently draw from each full marginal and reject the entire joint draw when there is a collision. That samples the specified product-conditioned distribution, but rejection has unbounded runtime. Use it offline; avoid unbounded rejection inside `act`. A bounded live fallback must be labeled approximate.

A full teacher can sample original triples and opponent discards with their selection likelihoods, then sample legal runouts from the resulting world. This is more faithful but costs more. Do not quietly mix the word “exact” with a uniform hidden-card or exchangeable-discard approximation.

## 5.4 How little a tiny Monte Carlo estimate knows

For independent bounded share samples, the standard error is at most

$$\operatorname{SE}(\hat e)\le\frac1{2\sqrt M}.$$

At 16, 64, and 256 samples this bound is 12.5, 6.25, and 3.125 percentage points. Approximate 95% intervals are nearly twice as wide. Correlated samples or a biased posterior add further limitations. Consequently, a claim that 20 or 50 trials reliably distinguish a 2-point equity edge is unfounded.

For comparing the three retained pairs, use **common random worlds**: the same opponent cards and runouts for each candidate. The estimates are correlated, often reducing variance of pairwise differences. Every world must exclude the entire original hero triple, regardless of which pair is retained.

For a fast live bot, a calibrated lookup can beat a tiny noisy simulation even if the simulation seems more sophisticated. Accuracy must be assessed at action thresholds, not only by mean equity error.

## 5.5 Draw arithmetic, with the right denominator

At selection, hero knows six card identities: three private cards and three flop cards. If no other card identities are public yet and other unavailable cards are treated as exchangeable, the marginal next card comes from 46 unknown identities. If there are $o$ useful outs among those cards, the chance to hit at least one in the next two board positions is

$$1-\frac{(46-o)(45-o)}{46\cdot45}.$$

For nine outs this is approximately 35.65%. If the discarded card is itself one of the relevant flush suit, there may be only eight such outs, not nine. After simultaneous exposure, subtract newly known public cards and revise which outs remain available. If modeling non-exchangeable hidden discards, use the posterior instead of this formula.

An out is useful only if it improves expected payoff: a flush-making card can still lose to a higher flush or a full house. Overlapping straight and flush outs must not be counted twice. The textbook “rule of four” is a rough memory aid, not a calibrated model for this variant.

# 6. Choosing the discard and exposed card

## 6.1 Factor the six-action distribution

A useful factorization is

$$\pi(d,r\mid I)=\pi_D(d\mid I)\,\pi_R(r\mid d,I).$$

There are three discard probabilities and two reveal probabilities conditional on each discard. This makes it easy to improve pair choice while preserving a simple reveal baseline. It is a parameterization of a six-action distribution, not an assumption that discard and reveal are strategically independent.

Define an approximate value $v_d$ for the retained pair after discarding $d$. A restricted softmax is

$$\pi_D(d)=\frac{\mathbf1\{v_d\ge v_{\max}-\delta\}\exp((v_d-v_{\max})/\tau_D)}{\sum_{d'}\mathbf1\{v_{d'}\ge v_{\max}-\delta\}\exp((v_{d'}-v_{\max})/\tau_D)}.$$

Here $\delta$ prevents randomization into a clearly inferior retained pair. The score units must be specified: equity percentage points, normalized chips, or expected points. Do not use the same numeric temperature interchangeably for these units. Setting $\tau_D$ very small approximates choosing the best estimate; increasing it smooths uncertain close comparisons.

## 6.2 First-build retained-pair score

For each pair, calculate a small feature vector and predict strength:

$$\begin{aligned}
v_d={}&\beta_0+\beta_{\mathrm{cat}}[\mathrm{category}]+\beta_1\,\mathrm{relative\ pair\ rank}\\
&+\beta_2\,\mathrm{kicker}+\beta_3\,\mathrm{flush\ potential}\\
&+\beta_4\,\mathrm{straight\ potential}+\beta_5\,\mathrm{nut\ potential}\\
&+\beta_6\,\mathrm{board\ interaction}.
\end{aligned}$$

Prefer fitted coefficients from offline samples over arbitrary category gaps. If fitting is not yet available, use transparent category rules plus draw bonuses, test them on a small adversarial hand suite, and label them provisional. Raw eval7 integer ranks are ordered hand codes; their numerical differences are not equity differences.

Important features include whether a pair comes from the board, whether a hole card is an overpair or top pair, how many distinct ranks complete a straight, whether an ace plays low, flush suit counts, and whether the draw is dominated by an opponent's exposed card after selection. At the selection decision, current-hand opponent exposures have not yet been published, so those features are unavailable there.

## 6.3 A concrete reason made-hand-only selection fails

Take `As Ks 7d` on `Qs Js 7c`. Keeping `As Ks` gives a nut-flush draw and a ten for a straight, with high-card possibilities; keeping `As 7d` preserves a current pair. A current five-card rank comparison selects the pair automatically. That can be the wrong continuation choice depending on ranges, future action, and stack depth. The example demonstrates why potential matters; it does not assert a universally optimal discard for every opponent model.

Conversely, keeping a superficially attractive draw while discarding a strong made hand can be wrong. The correct target is expected continuation value. Under severe time pressure, evaluate both made strength and robust draw potential rather than hard-coding “always keep a pair” or “always keep suited cards.”

## 6.4 Reveal baseline and a cautious improvement

For the chosen retained pair $(u,v)$, the simplest baseline is

$$\pi_R(u\mid d,I)=\pi_R(v\mid d,I)=\tfrac12.$$

A tunable alternative is

$$\Pr(\text{reveal }u)=\epsilon_R+(1-2\epsilon_R)\,\sigma(\gamma^{\mathsf T}\psi(u,v,F,H)),$$

where $0<\epsilon_R<1/2$. Features can measure visible pair strength, flush-suit information, straight completion information, and estimated opponent fold response. This keeps both reveals in support while allowing evidence-based bias. A probability floor alone does not guarantee strategic safety; it merely avoids a perfectly deterministic tell.

Do not mechanically reward “conceal the strongest card.” On some boards that hides value; on others it advertises a strong hidden complement by inference. Start at 50/50, measure opponent reactions, and move gradually. If every remaining player is already all-in and no meaningful betting remains, revealing one card rather than the other cannot change the current hand's showdown distribution. Pair choice still matters. Future-table learning effects are secondary and not a reason to sacrifice showdown equity.

## 6.5 The fundamental no-clairvoyance requirement

A valid offline label for pair choice uses

$$K^*(F)=\arg\max_K\mathbb E_{T,R}[V(K,F,T,R)\mid F],$$

where $T,R$ are turn and river. An invalid teacher first samples a full board and then chooses the best pair separately on that completed board. It approximates

$$\mathbb E_{T,R}[\max_K V(K,F,T,R)],$$

which is an upper bound on the first quantity and gives the player information unavailable at selection. The same restriction applies to opponents. Full-information simulation can evaluate outcomes after actions are fixed, but it must not let policies observe hidden cards or future board cards.

## 6.6 Training selection cheaply

Generate representative triples and flops; compute all three pair feature vectors; estimate each pair's value against a small family of legal opponent policies; then fit a shared pair scorer. Use the same sampled worlds to label all three candidates. Fit ranking loss or action regret, not only raw squared equity error.

A useful validation metric is

$$\mathrm{SelectionRegret}=\mathbb E[v(K^*)-v(\widehat K)].$$

A classifier that disagrees often on almost-equivalent pairs can be harmless. A model that is usually correct but sometimes discards the nuts is unacceptable. Include rare strong hands and unusual board textures in validation instead of relying only on random samples.

# 7. Betting mathematics with consistent chip accounting

## 7.1 Fix the meaning of pot and cost first

Let $P$ be the pot currently displayed before hero acts, including chips already bet by opponents. Let $C$ be the **additional** chips hero must contribute to call, capped by the relevant stack. Previous hero contributions are sunk for immediate chip-EV comparisons. Verify the supplied SDK's pot field against engine examples before using formulas.

On a river or genuinely terminal call, with no side-pot complications,

$$Q_{\mathrm{call}}=e(P+C)-C.$$

The chip-EV calling threshold is

$$e_{\mathrm{call}}=\frac C{P+C}.$$

For $P=150$ and $C=50$, the threshold is 25%. It is not $50/150$. At $e=30\%$, immediate call EV is $0.30\cdot200-50=10$ chips. At $e=20\%$ it is $-10$.

This calculation assumes no more betting, suitable equity against the actual opposing range, and correct treatment of uncalled excess. On the flop or turn, calling may lead to future costs and folds; the same formula is a terminal approximation.

## 7.2 Equity realization is a model, not a theorem

A fast nonterminal-call approximation replaces $e$ with $\widetilde e=\rho e$, where $\rho$ summarizes how much all-in equity the hand realizes under future betting. Out-of-position weak pairs, dominated draws, and multiway weak hands often warrant lower modeled realization. A simple implementation may restrict $\rho$ to $[0,1]$ as a conservative discount.

That restriction is not a universal poker fact. Implied winnings and successful future bluffs can give realized value exceeding a naive share of the current pot. Also, adding both a realization discount and an independent large “future cost” penalty can double-count the same disadvantage. Calibrate the approximation by street, position, and hand type, and use it mainly to avoid unjustified calls with fragile equity.

For raises, equity must be conditioned on the continuation branch. Do not reuse the unfiltered range equity against a range that only calls strong hands.

## 7.3 Bet EV when no bet is faced

In a heads-up terminal model, hero bets $B$ into pot $P$. Let $f_B$ be the probability the opponent folds and $e_B$ hero's equity conditional on a call. Ignoring raises,

$$Q_{\mathrm{bet}}(B)=f_BP+(1-f_B)[e_B(P+2B)-B].$$

For a zero-equity bluff, this becomes

$$Q_{\mathrm{bluff}}=f_BP-(1-f_B)B,$$

so the break-even fold probability is

$$f_B>\frac B{P+B}.$$

| Bet fraction $B/P$ | Pure-bluff break-even fold rate |
|---:|---:|
| 1/3 | 25% |
| 1/2 | 33.33% |
| 2/3 | 40% |
| 1 | 50% |
| 3/2 | 60% |

Positive bet EV compared with folding does not establish that betting is best. If checking realizes equity $e_0$, compare against $Q_{\mathrm{check}}\approx e_0P$ in the terminal model. A thin bet can be profitable yet worse than checking because the opponent folds weaker hands and calls stronger ones.

## 7.4 Raising while facing a bet

Suppose hero must call $C$, then raises by an additional increment $R$ above the current highest street contribution. Hero adds $C+R$. If one opponent calls the raise, that opponent adds $R$, making final pot $P+C+2R$. Under the same terminal, heads-up assumptions,

$$Q_{\mathrm{raise}}(R)=f_RP+(1-f_R)[e_R(P+C+2R)-(C+R)].$$

Convert this increment to the SDK's **total current-street contribution** before returning the action. If hero has already contributed $b_h$ on the street, requested total is $b_h+C+R$. Clamp only within an offered legal raise action; do not manufacture a raise when betting has not reopened.

## 7.5 Multiway continuation branches

The all-fold probability is not the average opponent fold probability. Under a provisional independence model,

$$F(B)\approx\prod_j f_j(B).$$

If each of three opponents folds 60% of the time, all fold only $0.6^3=21.6\%$. A half-pot pure bluff needs 33.33%, so that model does not justify it.

A more complete small-action evaluator sums over caller subsets $S$:

$$Q(B)=\Pr(S=\varnothing)P+\sum_{S\ne\varnothing}\Pr(S)\left[e_S\left(P+B+\sum_{j\in S}B_j\right)-B\right].$$

This schematic assumes no future raises and uses effective contributed amounts $B_j$. Unequal stacks, refunds, side pots, and range changes must be included in each branch. There are up to $2^7$ caller subsets at an eight-player table, which is unnecessary for the first live policy. Train a compact approximation or use broad categories such as “all fold / one calls / several call.”

A player already all-in cannot fold out of the main pot. Winning the active opponent's fold does not mean winning that main pot uncontested. Separate main-pot and side-pot values.

## 7.6 Bluff frequency versus bluff-to-value ratio

In the ideal heads-up river model where value bets always win when called and bluffs always lose, the fraction of bluffs among bets that makes a bluff-catcher indifferent is

$$p_{\mathrm{bluff}\mid\mathrm{bet}}=\frac B{P+2B}.$$

The corresponding ratio of bluff combinations to value combinations is

$$\frac{N_{\mathrm{bluff}}}{N_{\mathrm{value}}}=\frac B{P+B}.$$

These are different numbers. With a pot-sized bet, the bluff fraction is one third and the bluff-to-value ratio is one half. With a half-pot bet, the bluff fraction is one quarter and the ratio is one third.

This is a range-composition calculation, not a command to bluff every weak hand at that probability. If a bucket contains $V$ value combinations and $L$ eligible bluff combinations, the model calls for $V B/(P+B)$ bluff combinations in total. Choose bluff hands with useful blockers and low checking value, and cap any per-hand probability at one.

## 7.7 Minimum defense is a diagnostic, not a universal action rule

The same toy model gives a defense fraction $P/(P+B)$ against a zero-equity bluff. Applying that literally to all streets, all public-card patterns, or every player in a multiway pot is incorrect. Opponents may underbluff. An exposed card may eliminate most credible bluffs. Tournament utility may make calls with positive chip EV unprofitable in points.

Use these equations to sanity-check a model and understand incentives. They are not a substitute for selection-conditioned ranges, opponent estimates, or legal action accounting.

# 8. The recommended action distribution

## 8.1 Discrete action abstraction

Construct only the actions that are legal in the current state:

- Check when offered, otherwise fold when offered.
- Call when offered.
- Small bet/raise, initially around one third pot in an unraised pot.
- Large bet/raise, initially around three quarters pot.
- All-in when a legal raise can commit the stack.

Those sizes are initial experimental settings, not derived optimal sizes. Facing a bet, define a consistent raise increment convention, such as a fraction of the pot after calling; then convert it to raise-to total. Minimum raises, maximum raises, stack caps, and rounding can cause multiple intended sizes to become identical. Deduplicate them **before** assigning probabilities, or an action will gain accidental mass merely because several abstract sizes map to it.

An all-in call is a call, not a raise. A short all-in may fail to reopen action for other seats. Use the SDK legality result rather than coding a simplified version of the engine's reopening rule.

## 8.2 A regularized distribution over estimated values

Let $\mathcal A(I)$ be the legal candidates, $\pi_0(a\mid I)$ a baseline distribution with support on plausible actions, and $\widehat Q_a$ estimated values in one consistent unit. Solve

$$\max_{\pi}\left\{\sum_a\pi_a\widehat Q_a-\tau\,\operatorname{KL}(\pi\|\pi_0)\right\}.$$

The resulting distribution is

$$\pi(a\mid I)=\frac{\pi_0(a\mid I)\exp((\widehat Q_a-Q_{\max})/\tau)}{\sum_b\pi_0(b\mid I)\exp((\widehat Q_b-Q_{\max})/\tau)}.$$

Subtracting $Q_{\max}$ improves numerical stability. This is a useful design justification for a softmax around a baseline. It is not a Nash-equilibrium guarantee. Uniform noise over every legal action is a poor substitute: a legal 100-big-blind bluff can still be obviously terrible.

A cheaper implementation uses piecewise-linear threshold ramps and one random draw. For example, the continue probability can rise smoothly from 0 to 1 across a narrow band around the modeled call threshold. The difference between options is implementation cost; both require sensible scores and support.

## 8.3 Restrict randomization to plausible actions

Set probability to zero for physically impossible, illegal, or clearly inferior choices. Examples include folding when checking is free, an obviously losing river call against a certain superior exposed-card configuration, or a dominated selection under the intended model. Preserve bluffs that have estimated fold value; low showdown equity alone does not make an action dominated.

A candidate-support rule can retain actions with $\widehat Q_a\ge\widehat Q_{\max}-\Delta$, where $\Delta$ reflects estimation error. Model uncertainty does not justify huge random bets. It more often justifies staying near a validated baseline and avoiding irreversible stack commitments on weak evidence.

## 8.4 Conservative exploitation

Define a baseline policy $\pi_0$ and an opponent-model policy $\pi_E$. Use

$$\pi=(1-\lambda)\pi_0+\lambda\pi_E,$$

with $\lambda$ increasing slowly with relevant evidence. One illustrative shrinkage schedule is

$$\lambda(n)=\lambda_{\max}\frac n{n+k_0}.$$

For a first version, $\lambda_{\max}=0.5$ and $k_0=20$ are conservative starting hypotheses, not validated constants. Count context-relevant opportunities, not all hands. Twenty observed preflop folds do not constitute twenty observations of river fold-to-pot-bet behavior.

This mixture still can be exploited and the baseline is not a solved equilibrium. Its purpose is to prevent a tiny noisy sample from causing an extreme strategy change.

## 8.5 Small parameter vector

Keep the first tunable vector compact:

| Parameter family | Role | First tuning direction |
|---|---|---|
| Preflop entry / raise threshold | Controls initial participation | Check early busts and missed blind steals |
| Preflop third-card bonus | Values optionality | Fit against variant samples |
| Multiway strength adjustment | Avoids overcalling crowded pots | Inspect weak-pair losses |
| Flop and turn realization | Discounts fragile equity | Separate position and draw quality |
| River bluff-catch threshold | Responds to observed underbluffing | Use action-conditioned showdowns |
| Small / large sizing | Trades price against fold/value response | Compare paired local tournaments |
| Bluff intensity | Controls bluff combination mass | Lower against sticky ranges |
| Selection draw weight | Trades current strength for potential | Measure selection regret |
| Reveal bias | Controls informational exposure | Begin at zero bias |
| ICM pressure | Penalizes losing high-value survival chances | Fit on late-stage decisions |
| Exploitation strength | Controls response to noisy counts | Shrink strongly with little data |
| Mixing width | Smooths near-indifference actions | Keep far-from-threshold actions stable |

Avoid hundreds of free weights when only a few live feedback windows are available. A model can have many fixed offline coefficients while exposing only these few robust tuning controls.

# 9. Tournament points and ICM

## 9.1 Exact ICM definition

For positive remaining stacks $s_1,\ldots,s_n$ and total $S$, ICM assigns player $i$ first-place probability $s_i/S$. Conditional on another player finishing first, remove that player's stack and repeat for second place, and so on. Expected points are the sum of each remaining payout times its associated place probability.

For default top-three payouts, hero's utility can be computed directly as

$$U_i=50\frac{s_i}{S}+30\sum_{j\ne i}\frac{s_j}{S}\frac{s_i}{S-s_j}+20\sum_{j\ne i}\sum_{k\ne i,j}\frac{s_j}{S}\frac{s_k}{S-s_j}\frac{s_i}{S-s_j-s_k}.$$

This is $O(n^2)$ for a single player's utility with three paid places, not an exponential full-tournament simulation. Handle busted players and already assigned payouts explicitly. With nondefault payouts, use the supplied calculator or a verified general routine. Do not divide by zero after the last surviving player is selected.

The formula is the terminal scoring model at the hand cap under the supplied format. Before the cap, it is an approximation to continuation points, since it omits skill, blind position, future blind escalation, and strategic interaction. The official PokerStars explanation supports the basic distinction between chip count and payout equity [R5]; the formula and examples here are direct mathematical derivations.

## 9.2 Call threshold in points

For a terminal heads-up all-in decision, let $U_F$ be tournament utility after folding, $U_W$ after calling and winning, and $U_L$ after calling and losing. Ignoring ties, calling is preferred when

$$eU_W+(1-e)U_L>U_F.$$

Therefore

$$e>\frac{U_F-U_L}{U_W-U_L}.$$

All three utilities must be evaluated on **complete stack vectors**, including changes to opponents. It is wrong to insert only hero's changed stack while leaving the transferred chips on the opponent too. If ties matter, include a separate tie outcome and its actual stack distribution. A pot-share scalar alone is insufficient for nonlinear tournament utility.

## 9.3 A worked bubble example

Consider four players with equal stacks and payouts 50/30/20. Each has ICM utility 25. Suppose an illustrative fair gamble, with no intervening betting complications, either eliminates hero or doubles hero while eliminating one equal opponent. The winning stack vector is proportional to $(8,4,4)$, and hero's ICM utility becomes

$$50\left(\frac12\right)+30\left(\frac13\right)+20\left(\frac16\right)=38\tfrac13.$$

The losing utility is zero. The break-even success probability is

$$\frac{25}{38\tfrac13}=\frac{15}{23}\approx65.22\%.$$

A fair 50% chance to double is chip-neutral in this stylized gamble but loses expected points. This is an illustration of ICM curvature, not a complete legal betting-state example with posted blinds and an existing pot. For a real call, derive $U_F,U_W,U_L$ from the actual engine contributions.

## 9.4 Apply ICM selectively and correctly

The first implementation should use direct ICM comparisons for large all-in decisions involving a few live players, if timing permits. For small early-hand decisions, use a calibrated pressure feature rather than recomputing many stack outcomes. Read remaining players, stack rank, effective stack, payout jumps, and hands to cap.

Do not make “tournament-aware” synonymous with folding everything. Passing profitable steals sacrifices survival resources as blinds grow. Big stacks can sometimes profitably pressure medium stacks; short stacks may need to take risks before forced bets consume them. The optimum depends on the complete stack configuration and opponents' reactions.

When only two players remain with prizes 50 and 30, ICM utility is $30+20s_i/S$, linear in hero's chips. There is no extra ICM curvature within that two-player stage under this payout model. A universal fixed risk penalty would therefore be wrong.

## 9.5 Side pots and bust ordering

Hero may be eligible for the main pot but not a side pot. Each pot has its own eligible set. Expected chip award is the sum of pot size times hero's expected share in that pot; then subtract new costs. For tournament EV, jointly sample or enumerate outcomes because side-pot results are correlated and utility is nonlinear.

The supplied format ranks simultaneous busts by stack at the beginning of the hand. An ICM approximation that maps every zero-stack outcome to zero can be wrong when a simultaneous elimination already guarantees a paid place. The exact terminal outcome must include that rule. Use the supplied local engine and ICM calculator to validate these corner cases, rather than inventing a second full poker engine in `agent.py`.

# 10. Learning inside a table

## 10.1 Learn a few identifiable tendencies

Within at most a few hundred hands, each opponent produces limited context-specific evidence. Prioritize statistics with clear denominators:

- Voluntary preflop participation per opportunity.
- Preflop raise frequency per opportunity.
- Fold-to-bet by broad street and size bucket.
- Raise frequency when facing a bet.
- Showdown strength after specific betting lines.
- Selection/reveal behavior when enough cards become observable.

A check is not a fold opportunity. An all-in player has no fold decision. A player who folded before reaching the action is not in the denominator. A short all-in call is still a call. Prize events are not betting decisions and must not pollute action counts.

## 10.2 Beta-Binomial updates

For fold-to-bet probability $f$ in one coarse context, use a Beta prior:

$$f\sim\operatorname{Beta}(\alpha_0,\beta_0).$$

After $F$ folds and $N-F$ nonfolds in valid opportunities,

$$\widehat f=\frac{\alpha_0+F}{\alpha_0+\beta_0+N}.$$

Its posterior variance is

$$\operatorname{Var}(f)=\frac{\alpha\beta}{(\alpha+\beta)^2(\alpha+\beta+1)}.$$

A prior mean $\mu_0$ and strength $\kappa$ correspond to $\alpha_0=\kappa\mu_0$, $\beta_0=\kappa(1-\mu_0)$. For example, $\mu_0=0.4$, $\kappa=10$ gives a 4/6 prior. After three folds and one continuation the posterior mean is $7/14=0.5$, rather than the raw 75%. This example illustrates shrinkage; the prior is not claimed to describe the field.

For a speculative bluff, use a conservative fold estimate such as $\max(0,\widehat f-z\sqrt{\operatorname{Var}(f)})$. The normal approximation is imperfect for small counts, but it is computationally simple. Exact Beta quantiles belong offline if needed.

## 10.3 Track response categories separately

Nonfold can mean call or raise, which have very different consequences. A small Dirichlet model over fold/call/raise is useful where data support it. A bettor who is called frequently offers value opportunities; a bettor who is check-raised frequently faces a different risk. A single aggression statistic cannot represent both.

Do not fit a dense opponent model from five observations per bucket. Use hierarchical shrinkage: seat-specific estimates toward pooled table estimates, and table estimates toward an offline population prior. Keep the hierarchy simple enough to serialize and update safely.

## 10.4 Showdowns are a biased sample

Automatic disclosure of losing retained hands improves observability, but showdowns still occur selectively. Players who fold or win without showdown do not reveal their hidden card. You cannot estimate a player's overall hand distribution from shown hands alone without modeling the selection event.

Use showdowns for narrower questions: given a particular exposed card, bet size, and action line that reached showdown, which hidden cards occurred? Combine these with broader priors rather than treating shown frequencies as unconditional frequencies. Opponent discards remain hidden even at showdown; do not infer a unique original triple from a revealed retained pair.

## 10.5 Memory format and event idempotence

Keep a versioned memory object containing a hand marker, compact per-seat counts, last processed event position or event signature, and a small PRNG state if reproducibility is useful. A few kilobytes is ample for dozens of counts per seat. Immutable lookup tables belong in import-time data, not in memory bytes.

On timeout, exception, or crash, previous memory is kept and events are delivered again. A valid update must therefore be retry-safe. Processing events into a new local object and returning the serialized object only with the final action avoids partially committed external state. When using cumulative history or combining `events` with `history`, prevent double counting by a stable available event index or a carefully checked hand-relative cursor. Do not assume the protocol provides an undocumented event ID.

After an illegal action, returned memory is stored, so a final legal-action validator is also part of learning correctness. Truncated or malformed memory must reset to a conservative valid state, not throw an exception that repeats indefinitely. Never trust that decoding succeeded merely because the first bytes match a version tag.

# 11. Learning between uploads

## 11.1 What live feedback can and cannot identify

A round's average points estimates the whole deployed policy against that round's field. It does not identify which one of ten parameter changes helped. Opponents also improve between rounds, so a lower score in a later round does not prove your update regressed.

Use live results to detect coarse problems and update population assumptions. Use downloaded hand histories for action-level diagnosis. Use local paired tournaments to compare small candidate changes under controlled opponent mixtures. The guide states that hand histories can name opponents; that may help offline analysis, but live seats are anonymized and the deployed policy must not carry identities across tables.

## 11.2 Log extraction with high information per minute

Stream a manageable subset of the gzipped JSON lines. Extract:

| Diagnostic | What it can reveal |
|---|---|
| Failed decisions by phase/street | Legality, timing, or rare-state defects |
| Early bust fraction | Excess preflop risk or overcommitting weak pairs |
| Final stack / points by player count | Tournament conversion problems |
| Calls by price and hand category | Miscalibrated equity or realization |
| Bet success by size and players remaining in hand | Fold-equity model errors |
| Showdown residual by predicted equity bucket | Range or evaluator calibration errors |
| Selection outcomes with own private events | Index mistakes and pair-choice failures |
| Action frequencies by exposed-card relation | Deterministic signaling or missed exploitation |
| Restarts and memory truncation reports | Runtime reliability defects |

Interpret equity calibration carefully: showdowns are selected, and realized outcome variance is large. Preserve the predicted context and whether a call closes action. Selection reward cannot be isolated merely by looking at whether the hand was eventually won.

## 11.3 Use paired local tournaments

Maintain a small fixed opponent suite: check/fold, loose caller, tight raiser, aggressive bluffer, default selector, draw-aware selector, and previous versions of your own bot. Fill eight seats. The supplied example with three folder arguments is three-handed, and with three default paid places everybody cashes; it is a poor proxy for the eight-player bubble.

Run baseline and candidate over the same seeds, seat permutations, and opponent mixtures. Common randomness usually reduces variance, although diverging actions can change future random consumption unless the simulator uses stable counter-based deal streams. Do not claim perfect card-by-card pairing just because two runs share the same seed.

For paired table differences $D_i=Y_i^{\mathrm{new}}-Y_i^{\mathrm{old}}$, estimate

$$\widehat\Delta=\frac1N\sum_iD_i,$$

with standard error $s_D/\sqrt N$. Use table or independent iteration as the unit, not each decision. If multiple seats or observations share a table, cluster them appropriately rather than treating them as independent samples.

## 11.4 The size of tournament noise

Under fixed default payouts, $Y\in[0,50]$ implies a standard deviation no larger than 25, hence an independent-table sample-mean standard error no larger than $25/\sqrt N$. At 5,000 tables that is approximately 0.354 points; a rough 95% normal interval has half-width 0.693 points in the worst-variance case.

This is a conservative variance bound, not a guarantee of normal coverage or independence for every tournament arrangement. Actual standard errors can be smaller. It nevertheless shows why a tenth of a point of apparent improvement should not justify a risky rewrite without corroborating evidence.

If actual table payouts differ, recompute the score range and use the actual outcomes. If only aggregate frequencies are available and capped tables receive fractional ICM scores, place counts alone may not reconstruct exact score variance.

## 11.5 Coordinate search before elaborate online learning

Given few feedback windows, use a champion/challenger loop:

1. Freeze a reliable champion and its measured metrics.
2. Change one or two interpretable parameter families.
3. Test challengers on a screening seed set.
4. Retest the strongest challenger on a separate validation seed set.
5. Require timing and legality to pass, then promote only with sufficient evidence.
6. Record the parameter vector, source revision, score estimate, uncertainty, and deployment snapshot.

Reserve untouched seeds to reduce winner's-curse overfitting from many candidate trials. Avoid evaluating only against opponents that your previous version already dominates.

An optional derivative-free update is simultaneous perturbation:

$$\widehat g_i=\frac{\widehat J(\theta+c\Delta)-\widehat J(\theta-c\Delta)}{2c\Delta_i},\qquad\Delta_i\in\{-1,+1\}.$$

Use common local seeds for the two evaluations, clip parameter steps, and validate the resulting candidate. This is an offline optimization option, not a recommendation to infer a gradient from two unpaired official rounds against changing opponents.

## 11.6 Why a bandit is not automatically the answer

A few prevalidated policy configurations can be treated as arms in local experimentation. Points are continuous bounded rewards, so a Bernoulli Beta update is not the literal likelihood for average tournament points. Use an empirical mean/variance model, bootstrap, or an explicitly chosen bounded-reward bandit model.

Only six official scored rounds provide at most six noisy configuration-level observations, often with delayed results and changing opponents. That is too little to reliably optimize a high-dimensional policy. Round weights make reckless exploration in later rounds particularly expensive. Explore primarily offline; deploy credible improvements live.

## 11.7 Off-policy evaluation caveat

If logging action probabilities, a one-step contextual-bandit importance estimate has the familiar ratio $\pi(a\mid x)/\mu(a\mid x)$. Poker is sequential: replacing the policy changes later states and opponent responses. A single-action importance ratio does not unbiasedly estimate the entire tournament value of a different poker policy.

Trajectory ratios require support and can have enormous variance. Doubly robust evaluation [R7] and poker-specific variance reduction such as AIVAT [R6] offer relevant ideas, but require additional assumptions, model quantities, or known strategies. Do not spend the first hour implementing them unless working code already exists. Paired local tournaments and focused diagnostics are more feasible here.

# 12. Runtime architecture under 1 ms

## 12.1 Three computational tiers

| Tier | Live work | When to use |
|---|---|---|
| A: strict baseline | Compact features, a few lookups, threshold mixing | First legal submission and fallback |
| B: bounded refinement | Small exact river enumeration or fixed-budget evaluations | Only after measured headroom |
| C: offline teacher | Monte Carlo, range enumeration, ICM branch evaluation, model fitting | Between decisions outside tournament execution |

Do not assume NumPy, a tree ensemble, or a neural model is faster for a single tiny request. Python object conversion, feature-array allocation, model-call dispatch, and serialization can dominate a small mathematical computation. Benchmark the full decision path.

## 12.2 Features worth their cost

Use compact integer card IDs, rank masks, suit counts, and precomputed card objects where safe. With 52 cards, many relationships fit in tiny tables. Parse card strings once per request or reuse immutable mappings. Derive the current street from legitimate state, not from a guessed phase name: the guide says ordinary betting phase is `"betting"`, while this variant adds `"select"`.

A useful feature set contains:

- Street and number of eligible opponents.
- Position relative to remaining action, not just original seat index.
- Pot, call cost, legal raise limits, effective stack, and stack-to-pot ratio.
- Made-hand category with board-only distinctions.
- Pair rank, kickers, flush and straight potential, and nut blockers.
- Opponent exposed-card relations to the board.
- Coarse preflop and current-street aggression history.
- Tournament stack rank, payout stage, and distance to hand cap.
- Shrunk opponent response estimates.

Do not let a “compact” representation erase the defining feature of the game: which cards are exposed and which private card is dead.

## 12.3 Safe scheduling of expensive work

Import immutable data and warm approved prediction routines at import time, as the guide suggests. Respect the startup allowance. Do not start background threads and assume they survive worker forks. Do not use lazy JIT compilation on the first live decision. Numba or ONNX can be options only after their exact initialization, threading, fork, and memory behavior are tested under the supplied environment.

A hard fixed cap on optional computations is safer than a loop that merely checks elapsed time after each iteration. A single iteration can overshoot the deadline, and Python wall-clock checks do not account perfectly for host-side delivery. Establish a tested maximum work count; use time checks as a secondary guard.

No absolute safe loop count is claimed here. The supplied build box is the correct place to determine it. Aim for substantial margin below 1 ms, then inspect p99 and worst-case latency, not just average latency.

## 12.4 Legal-action adapter

Conceptual Python-like pseudocode:

```python
def finalize_betting(state, desired_kind, desired_total=None):
    offered = state.can(desired_kind)
    if offered is not None:
        if desired_kind == "raise":
            total = int(desired_total)
            total = max(offered.min_amount, total)
            total = min(offered.max_amount, total)
            return Action.raise_to(total)
        if desired_kind == "check":
            return Action.check()
        if desired_kind == "call":
            return Action.call()
        if desired_kind == "fold":
            return Action.fold()
    if state.can("check") is not None:
        return Action.check()
    if state.can("fold") is not None:
        return Action.fold()
    first = state.legal_actions[0]
    return Action(first.kind, first.min_amount)
```

This sketch assumes a nonempty legal action list and verified action-kind spelling from the kit. It is not a complete `agent.py`. Selection must have its own explicit branch and validation:

```python
if state.phase == "select":
    d, r = choose_indices(state, memory)
    if not valid_distinct_python_indices(d, r):
        d, r = 2, 0
    return Action("select", cards=(d, r)), memory_out
```

The helper should reject nonfinite sizing values before converting to an integer, and reject invalid selection index types rather than relying on implicit casts. Known action amounts should be built with the SDK's constructors. Test the adapter against the local protocol, including short all-ins, unavailable folds, and raises that have not reopened.

## 12.5 Bounded memory and fallback behavior

Decode memory defensively. If it is absent, unknown-version, malformed, or truncated, initialize conservative priors. Use a compact binary struct or short JSON with a bounded schema; whichever is chosen, benchmark the complete decode/update/encode process. Avoid writing a fresh list of every historical event into memory each turn.

The first version should have a simple fallback policy requiring no model call: check when offered, otherwise a conservative legal fold, and default selection `(2,0)` if the selection scorer fails. A fallback is damage control, not a reason to ignore errors. An exception-based fallback that triggers often can discard all strategic advantage.

## 12.6 A reliability calculation

If a simplified model assigns independent failure probability $p$ to each of $m$ decisions, the chance of at least one failure is $1-(1-p)^m$. At $p=0.001$ and $m=200$, that is about 18.1%. Real failures are often correlated by a rare state rather than independent, but the example explains why a seemingly small per-action error rate is unacceptable.

The upload rejection threshold of more than 10% failed decisions is an admission threshold, not a performance target. Aim for zero illegal actions, zero decoding exceptions, and no observed overruns on the validation suite.

# 13. An achievable build and revision schedule

The intervals below are targets, not claims about the time needed on the provided machine. If a stage slips, preserve the last working bot and shorten the optional work.

| Elapsed build time | Deliverable | Acceptance condition |
|---|---|---|
| 0-10 minutes | Legal phase handling and conservative baseline | Handles selection; valid memory; runs locally |
| 10-20 minutes | Three-pair scorer and random reveal | Index/unit tests; no future-card leakage |
| 20-35 minutes | Compact preflop/postflop policy | Pot odds, board features, known-dead-card handling |
| 35-45 minutes | Legal sizing and initial opponent counts | No duplicate actions; safe serialization |
| 45-55 minutes | Eight-seat local validation and timing | p99/max headroom, zero failed decisions |
| 55-60 minutes | Accepted active submission | Confirm active snapshot eligibility |
| 60-80 minutes | Fix failures; calibrate selection and major equity errors | First challenger beats baseline locally |
| 80-100 minutes | Improve one-card ranges and river decisions | Action-conditioned calibration improves |
| 100-120 minutes | Add or refine late-stage ICM | Validated complete-stack outcomes |
| 120-140 minutes | Tune sizing / exploitation using logs | Small controlled changes with held-out seeds |
| 140-160 minutes | Deploy strongest validated version | Avoid speculative architecture changes |

If the first bot is already functional, prioritize the earliest unresolved risk rather than restarting the schedule. If only 15 minutes remain, selection legality, correct pot odds, conservative multiway play, and timing reliability are more valuable than beginning a solver.

# 14. Offline modeling choices and compression

## 14.1 Start with tables, then add fitted models if worthwhile

Preflop can use a table over 22,100 unordered triples, with extra dimensions for opponent count or position if necessary. Store sorted-card keys while retaining a mapping to original indices for selection. Suit canonicalization can reduce redundant cases, but a naive renaming procedure is easy to get wrong when private cards, board, and exposures are canonicalized inconsistently. Use canonicalization only with permutation-invariance tests.

Selection needs a shared scorer of pair-plus-flop features, not a separate table for every raw triple/flop combination. Betting can use a small table over street, equity bucket, pot-odds bucket, player count, position, and tournament stage, plus a small response correction. Do not let the Cartesian product of dozens of bins produce a mostly empty table.

A tiny linear model, shallow tree, or manually quantized table can be inspected and updated quickly. A larger LightGBM or neural predictor might fit better offline, but its benefit must survive end-to-end latency and cold-start tests. Availability of PyTorch does not establish that it is the best deployment choice.

## 14.2 Training targets should match the decision

Use equity labels for an equity estimator, selection regret for pair ranking, and utility labels for action values. Do not train on raw hand-category codes and call the output a win probability. Do not train a chip-EV model and interpret its values as points without an explicit conversion.

To learn action values, run the candidate action and a legal continuation policy through a simulator against diverse opponents. Hidden cards may be used to compute the final reward but never as policy input. The teacher's opponent family is a modeling choice; evaluate on held-out styles so the learner does not simply memorize one weak opponent.

## 14.3 Calibration around thresholds

Global mean squared error can hide expensive mistakes. Evaluate separate bins for equity near call thresholds, large-pot commitments, multiway hands, exposed-card draws, and low effective stacks. A 3-point equity error is relatively harmless when both estimates say clear fold; it can flip a major all-in decision near the threshold.

Use isotonic calibration or a small binwise correction only if validation data support it. Keep calibration conditional on broad context. A single global correction cannot fix systematic errors that change sign between heads-up and multiway pots.

## 14.4 Controlled uncertainty

For offline estimates based on sampling, keep an uncertainty estimate or effective sample count. Use that to avoid overconfident exploitation and to identify regions for further sampling. Spend offline teacher effort on states where candidate actions are close and stakes are high.

Do not average contradictory opponent assumptions into a single confident number. A useful robustness check evaluates the policy against several plausible range families: broad/default selection, competent retention, sticky calling, and aggressive bluffing. Reject improvements that gain slightly against one family but fail catastrophically against another unless live evidence strongly supports the favorable family.

# 15. Validation cases with the highest expected value

## 15.1 Card and selection invariants

- Test every one of the six `(discard_index, reveal_index)` pairs against a distinct triple. The exposed card must be retained; the discarded card must never enter evaluation or future draws.
- Verify retained-card relative ordering after selection and identify exposure by identity.
- Test original triples with a pair, trips, three suited cards, an ace-low straight possibility, and a made-hand versus draw conflict.
- Test board-only best hands, ties, and cases where one or both hole cards play.
- Verify all public exposed cards remain excluded from simulated decks after folds.
- Confirm unknown opponent discards are never fabricated as known.

## 15.2 Action and accounting invariants

- Check offered, fold absent: return check, never fold.
- Call offered, check absent: do not treat a cheap call as a check.
- Fractional computed size: integer conversion must not land below minimum.
- Short all-in: use legal maximum; do not force a normal minimum raise.
- Several abstract sizes become the same total: merge before sampling.
- Raise unavailable because betting has not reopened: remove every raise candidate.
- Side pot with an all-in opponent: folding the active opponent does not award the main pot automatically.
- Refunded unmatched excess: evaluate the actual matched contribution.

## 15.3 Memory and timing invariants

- Empty memory; malformed bytes; unknown version; truncated payload.
- Retry after a failed decision without double counting history.
- Switching worker processes with the same table memory.
- Ten-player maximum supported state, even though scoring defaults to eight.
- Long event batch after hero has not acted for several hands.
- Selection phase after an all-in preflop action.
- First live call after import/fork, plus repeated calls.
- Eight-seat long local runs, p99 and maximum latency, and upload validation without a bank.

The hand evaluator itself should be cross-checked using known hand rankings and ties. The eval7 project documents hand evaluation and warns that its range equity helpers have limitations [R4]. Its existence does not remove the need to validate the variant's legal retained-card construction.

## 15.4 Strategy invariants

- Certain winner on a terminal board: calling a legal bet should not fold because a stale heuristic says “weak preflop hand.”
- Certain loser without fold equity: do not call merely because a preflop premium pair was held.
- Opponent all-in: do not estimate a positive fold probability for that opponent.
- No more betting possible: reveal identity should not alter computed showdown equity.
- Random reveal baseline: each retained card appears with approximately equal frequency over repeated draws.
- Multiway equity: adding an eligible opponent cannot increase hero's share in the same fixed sampled world.
- ICM: total utilities sum to the remaining prize pool; heads-up utility is linear for fixed two-place payouts.

# 16. What the research literature supports, and what it does not

Counterfactual regret minimization provides a principled method for learning strategies in imperfect-information games [R2]. Its standard equilibrium interpretation is strongest in two-player zero-sum settings. The eight-player tournament here is not covered by a blanket claim that ordinary self-play CFR yields an unexploitable strategy.

Monte Carlo CFR estimates regret updates using sampled trajectories, reducing per-iteration work at the cost of sampling noise [R3]. This is not the same as doing a few equity rollouts and choosing the highest chip EV. A correct CFR implementation must account for information sets, reach probabilities, counterfactual values, and strategy averaging.

Pluribus demonstrated strong six-player no-limit hold'em play using an offline blueprint and additional search [R1]. The relevant engineering inspiration is abstraction and offline computation. This memorandum does not propose recreating its training and search system in the allotted build hour, nor does its result validate this variant's proposed heuristics.

AIVAT concerns variance reduction in evaluating imperfect-information agents [R6]. Doubly robust policy evaluation combines outcome and propensity modeling under stated assumptions [R7]. These are useful later references, but neither makes six changing-field round scores sufficient to learn a complex optimal policy.

The variant-specific recommendations in this memorandum are original derivations and practical proposals based on the supplied rules. There is no cited paper establishing optimal discard, reveal, or betting probabilities for this exact game.

# 17. Common proposals to reject or qualify

| Proposal | Failure mode | Practical replacement |
|---|---|---|
| Evaluate all three hole cards with the board | Gives an illegal three-card showdown advantage | Evaluate only a retained pair |
| Pick discard after simulating full board | Uses future information unavailable at selection | Fix discard from flop information first |
| Keep highest current eval7 rank | Ignores draws; rank gaps are not EV gaps | Pair scorer with calibrated potential |
| Reveal lowest card always | Creates a deterministic rank tell | Random reveal, then small tested bias |
| Uniform hidden card forever | Ignores selection and action evidence | Shrunk selection-aware one-card range |
| Multiply heads-up equities | Mishandles dependence and ties | Joint legal samples or validated approximation |
| Bluff whenever equity is low | Ignores fold probability and checking value | Compare action values by response branch |
| Always defend MDF | Assumes an inapplicable toy game | Range, price, opponent, and ICM comparison |
| Add random noise to every action | Randomizes into costly mistakes | Mix only plausible actions |
| Use large online Monte Carlo | Latency and noisy threshold decisions | Offline teacher, bounded live work |
| Learn across live tables in globals | Breaks reset rule and process assumptions | Per-table memory; offline population updates |
| Optimize chip EV only | Misprices bubble survival | Points-aware large-decision evaluation |
| Tune dozens of weights from one score | Cannot identify cause; overfits noise | Small parameter vector and local paired tests |
| Trust average runtime | Rare states time out and lose pots | p99/max, cold-call, and no-bank tests |
| Trust local three-player test score | Every default place pays; wrong bubble | Eight-seat benchmark mixtures |
| Assume uploaded means active | Snapshot can miss the intended version | Verify accepted active status |

# 18. Compact final implementation specification

The following is the recommended minimum research-to-code contract.

**Inputs.** Actual state configuration; legal actions; hero's original/retained cards and own discarded card; board; all public exposed cards; current-street contributions; pot and call cost; player statuses; incremental public events; versioned table memory.

**Immutable data.** Card-ID maps; optional cached eval7 card objects; a small preflop triple score table; shared retained-pair score coefficients or lookup; street/context equity calibration; baseline action thresholds; population opponent priors.

**Per-table memory.** Coarse action opportunity counts, fold/call/raise counts, optional reveal-type evidence, hand/event cursor, and PRNG state. No team identities, no persistent live-table files, and no full historical transcript.

**Selection.** Score all three retained pairs. Choose the best or mix only near ties. Reveal a retained card with probability one half unless a tested model supports a small deviation. Return original distinct indices and zero amount.

**Betting.** Form legal distinct candidates. Estimate strength and continuing ranges using public exposure. Calculate terminal pot-odds values where appropriate; use a calibrated nonterminal approximation otherwise. Add ICM reasoning for large late-stage commitments. Apply a restricted distribution around a validated baseline. Convert to integer raise-to totals and validate again.

**Adaptation.** Within a table, update a few context-specific counts with shrinkage. Between rounds, inspect failure logs first, then compare small parameter changes on eight-seat paired local tournaments. Keep a deployable champion at all times.

**Acceptance.** Legal selection; correct unavailable-card masks; no future information in simulation; no unsupported persistence; zero observed failed decisions; substantial timing headroom; no-bank upload acceptance; intended version active before the next snapshot. Performance advantage remains an empirical question to be measured.

# References and evidence register

The two user-provided local attachments are cited here as supplied source documents, not as public URLs. They were available under filenames `Pasted text(20261107-022122).txt` (general official rules) and `Pasted text(20261107-022517).txt` (getting-started/runtime guide). The event-specific format was pasted directly in the conversation. No starter kit files or live performance logs were inspected.

**[R0] Supplied event format.** NO LIMIT '26, Bay Area tournament format. Default variant, scoring, selection protocol, and schedule. [Format page](https://pokerbot.sequoiacap.com/tournament/competitions/5f8be52b-8038-4c43-a0fa-971abcacec1b/format). Analysis uses the user-supplied contents; authenticated page state was not independently fetched.

**[R1] Brown, N., and Sandholm, T. (2019).** *Superhuman AI for multiplayer poker*. Science 365, 885-890. [Author-hosted paper](https://noambrown.github.io/papers/19-Science-Superhuman.pdf). Supports the multiplayer-poker result and offline-blueprint/search architecture; not a performance claim for the present design.

**[R2] Zinkevich, M., Johanson, M., Bowling, M., and Piccione, C. (2007).** *Regret Minimization in Games with Incomplete Information*. NeurIPS 20. [Proceedings](https://papers.nips.cc/paper_files/paper/2007/hash/08d98638c6fcd194a4b1e6992063e944-Abstract.html). Foundation for counterfactual regret minimization.

**[R3] Lanctot, M., Waugh, K., Zinkevich, M., and Bowling, M. (2009).** *Monte Carlo Sampling for Regret Minimization in Extensive Games*. NeurIPS 22. [Proceedings](https://proceedings.neurips.cc/paper/2009/hash/00411460f7c92d2124a67ea0f4cb5f85-Abstract.html). Sample-based regret updates; see the authors' corrected version/errata when implementing proofs or algorithms.

**[R4] eval7 maintainers.** *eval7 project documentation*. [PyPI project](https://pypi.org/project/eval7/). Checked 6 November 2026. Documents hand evaluation and range-helper limitations. Use the competition's pinned package version, not an assumed latest release.

**[R5] PokerStars Learn.** *ICM, and Its Impact on Tournaments*. [Official operator explanation](https://www.pokerstars.com/poker/learn/lesson/icm-and-its-impact-on-tournaments/). Used only for the basic meaning of ICM and distinction between chips and payout equity; exact formulas here are derived directly, and the competition's scoring code is authoritative.

**[R6] Burch, N., Schmid, M., Moravcik, M., and Bowling, M. (2018).** *AIVAT: A New Variance Reduction Technique for Agent Evaluation in Imperfect Information Games*. AAAI. [Proceedings](https://ojs.aaai.org/index.php/AAAI/article/view/11481). Relevant to evaluation noise, not a first-hour dependency.

**[R7] Dudik, M., Langford, J., and Li, L. (2011).** *Doubly Robust Policy Evaluation and Learning*. ICML. [Paper](https://icml.cc/2011/papers/554_icmlpaper.pdf). Relevant to off-policy evaluation; a one-step bandit result does not automatically evaluate full poker trajectories.

# Appendix A. Short derivations for implementation review

## A.1 Pot odds

A call gains the current pot $P$ on a win and loses the added cost $C$ on a loss, ignoring ties. Thus $eP-(1-e)C=e(P+C)-C$. Break-even is $e=C/(P+C)$. Ties can be included using expected pot share when the pot is simple and contribution accounting is correct.

## A.2 River bluff mixture

Let $q$ be the bluff fraction in a polarized betting range. A bluff-catcher calling a bet $B$ into a pre-bet pot $P$ gains $P+B$ against a bluff and loses $B$ against value. Indifference is $q(P+B)-(1-q)B=0$, giving $q=B/(P+2B)$. Convert fraction to bluff/value ratio using $q/(1-q)$.

## A.3 KL-regularized action choice

For normalization multiplier $\nu$, differentiate $\sum_a\pi_aQ_a-\tau\sum_a\pi_a\log(\pi_a/\pi_{0a})+\nu(\sum_a\pi_a-1)$. The stationary equation gives $\pi_a\propto\pi_{0a}\exp(Q_a/\tau)$. Restrict the domain to supported legal actions. At zero baseline mass, this regularizer does not spontaneously create support.

## A.4 ICM total-points conservation

For any complete finishing order, the assigned remaining prizes sum to the same remaining prize pool. ICM assigns probabilities summing to one over finishing orders. Taking expectations preserves this sum. Therefore a computed set of player ICM utilities that does not sum to the remaining payouts contains a bug or inconsistent payout treatment.

## A.5 Sampling error and uncertainty

For $X\in[0,1]$, variance is at most $1/4$. The mean of $M$ independent samples therefore has variance at most $1/(4M)$. This bound quantifies sampling noise only. It does not account for systematic errors from uniform hidden cards, omitted discards, a wrong opponent selection model, or using showdown equity as action value.

# Appendix B. Recommended reading order for a coding agent

Read sections 1-2 first for the contract; sections 6-8 for selection and betting distributions; sections 10 and 12 for memory and timing; section 15 for high-value tests. Then implement the smallest viable policy. Sections 4-5 and 9 support later accuracy upgrades. Sections 11 and 13 govern feedback and deployment. Sections 16-17 prevent inappropriate transfers from general poker theory.
