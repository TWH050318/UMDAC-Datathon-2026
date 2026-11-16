# Hypothesis log (first pass, 14 Nov)

Status: **Proven** = holds on all rows in scope (structural) · **Supported** = strong, quantified, alternatives checked ·
**Open** = pattern seen, mechanism not yet pinned down · **Rejected** = tested and did not hold.
All figures come from the full 10M rows; each has a cell in the notebook named in the last column.

## Routing, continuity, conversions
| ID | Hypothesis | Result | Status | Where |
|---|---|---|---|---|
| R1 | `PARTICIPANT_COUNT` = number of BICs in `BIC8_PATH` (`...` not counted) | 10,000,000 / 10,000,000 | Proven | 01 A1 |
| R2 | `Direct` ⇔ exactly 2 participants | 100%, 0 exceptions | Proven | 01 A1 |
| R3 | Path length is geometric: each extra bank is added with constant probability | n(k+1)/n(k) = 0.368 for k = 2…8 (0.363–0.372); the same in all 4 flows and for domestic vs cross-border. 0.368 ≈ 1/e — check whether that is the intended parameter | Supported | 01 A2 |
| R4 | With 3+ banks, a fixed share is `Covered`, independent of path length | 11.3% for every k from 3 to 8. But it depends on geography: ≈10.5% cross-border vs ≈19.5% domestic | Supported; driver of the domestic difference Open | 01 A3 |
| R5 | `CONTINUITY_QFLAG = 'N'` ⇔ path contains `...` | 100%, 0 exceptions | Proven | 00 §5 |
| R6 | Each link is hidden independently with p = 5%, so P(gap) = 1 − 0.95^(k−1) | Implied per-link p = 0.0498–0.0500 for k = 2…6; observed vs model within 0.1 pt | Supported | 01 B1 |
| R7 | Path endpoints differ from the BIC columns as a generated event, 5% per end, independent | 4.98% and 4.99%; both together 0.247% (0.05² = 0.25%). Replacement bank is in another country ≈95% of the time | Supported; meaning Open | 01 A4 |
| R8 | A link converts currency iff it crosses a currency-area border | Direct, visible paths: same area → 0 conversions in 927,261 of 927,261; different area → 1 conversion in 99.7%. All 1,608 large country pairs convert either 0% or 100% of the time. Paths with 3–6 banks: FX count = number of area crossings in 99.5% | Supported (near-deterministic); remaining 0.3–0.5% are small country pairs not yet assigned to an area | 01 C2–C3 |
| R9 | Currency areas can be recovered from the data | Euro area (19 codes incl. AD, MC, MQ), USD area (US, PR, EC, VG, BQ), GBP area (GB, IM, JE), CHF area (CH, LI) | Supported | 01 C2 |
| R10 | Duration is a sum of per-link delays | Median 39 s (2 banks) → 126 → 418 → 590 → 796 s (6 banks); mean rises ≈ +200 s per extra bank | Supported | 01 B2 |
| R11 | Direct-payment duration is a two-component mixture (fast ≈ 30 s, slow ≈ 30 min) | ≈36% of direct payments exceed 300 s. The share barely moves with flow, weekend, hour or gap; slightly higher for domestic (43%) and small amounts (40–47% below USD 100 vs 35% above USD 100k) | Open — what decides fast vs slow is not yet found | 01 B2 |
| R12 | Duration depends on customer type or weekend | Slow share 36.0–37.2% across flows, 36.3% vs 36.2% weekday/weekend | Rejected | 01 B2 |

## Amounts, currency, time, geography
| ID | Hypothesis | Result | Status | Where |
|---|---|---|---|---|
| A1 | Amounts are log-normal with the same spread in every flow | sd of log10 = 0.992–0.996 in all four flows; slight left skew (−0.12) | Supported | 02 A1 |
| A2 | Each business party multiplies the typical amount by a constant factor, additively on the log scale | Sender B: +0.84 / +0.86; receiver B: +0.85 / +0.87; interaction 0.017. ≈ ×7.2 per business party (medians: C2C 464, B2C 3,118, C2B 3,236, B2B 22,883 USD) | Supported | 02 A1 |
| A3 | A2 is an artefact of currency mix (Simpson check) | Holds within every currency with 20,000+ payments: B2B − C2C = 1.74 ± 0.08 log units | Rejected (the effect is real) | 02 A1 |
| A4 | Each currency has its own amount level | Median from about 145 USD (XOF) to about 9,100 USD (KYD) among the 40 most used currencies; within-currency sd ≈ 0.92, lower than the pooled 0.99 | Supported; what sets the level (country income?) Open | 02 B1 |
| A5 | Round amounts are chosen in the payment currency | 38.6% of USD payments are whole dollars vs 1.0% of non-USD; same share in all flows (38.3–38.8%). Most common: 10,000 / 1,000 / 5,000 / 100,000 / 500 | Supported | 02 A2 |
| C1 | The payment currency is the sender's home currency | Cross-border: sender's home currency 78.0%, home on both sides 8.7%, receiver's 4.6%, USD/EUR vehicle 3.6%, other 5.1%. Domestic: home currency 93.8% | Supported; rule for the remaining ≈13% Open | 02 B2 |
| T1 | Weekend volume is a fixed fraction of weekday volume, for consumers as well as businesses | Saturday 25%, Sunday 36% of weekday level for both sender types; Thu/Fri ≈ 3–5% above Mon–Wed (UTC days) | Supported; Sat ≠ Sun may be a time-zone effect — Open | 02 C1 |
| T2 | Activity follows the sender's local clock with one common daily shape | After shifting each country by its estimated offset, the hourly curves of JP, SG, DE, GB, US coincide: sharp start, morning and late-afternoon peaks, night ≈ 1% per hour | Supported | 02 C2 |
| T3 | Business and consumer senders have different daily shapes | Nearly identical in GB (largest gap ≈ 0.7 pt per hour) | Rejected so far | 02 C2 |
| G1 | The receiving country is chosen independently of the sending country | Among large corridors the lift stays below 1.25 except for domestic pairs (US-US 1.27, GB-GB 1.48) and one extreme corridor MQ→TN (lift 238, 20,007 payments) | Open — MQ→TN needs explaining | 02 D |

## Parties and anomalies
| ID | Hypothesis | Result | Status | Where |
|---|---|---|---|---|
| P1 | Sender type and receiver type are drawn independently | Observed shares within 0.02 pt of the product of the marginals (B sender 78.7%, B receiver 28.8%) | Supported | 03 A1 |
| P2 | An account has one type and one bank | Type: 100% both sides. Ordering bank: 100%. Beneficiary bank: 97.6% (61,606 accounts appear with 2+ banks — consistent with R7) | Proven / Supported | 03 A2 |
| P3 | Account format is set by the bank's country | All 62 countries with 20,000+ payments are either ≈100% IBAN (35) or ≈0% IBAN (27); IBAN country = bank country in 100% of IBAN accounts | Proven | 03 A3, 00 §5 |
| P4 | Party details reveal the type | `<business>` tokens only for B (85%), `<first_name>`/`<last_name>` only for C | Proven (one-directional) | 03 A4 |
| P5 | Country in the party details = bank country | Ordering side 100%. Beneficiary side only 1.0% | Rejected for beneficiaries — Open: what does the beneficiary address country follow? | 03 A4 |
| N1 | Fat-finger = amount multiplied by a power of 10 | Median amount ≈ 80× the normal level of its flow (+1.9 log units), but the shift is spread from −4.6 to +6.6 and 24% are *below* the flow mean, so the separator moves both ways | Supported in direction; exact rule Open (needs digit-level test) | 03 B1 |
| N2 | Duplicate = exact copy of a payment | 679 rows form 185 groups of 2–5 identical payments (same accounts, amount, currency, path) spread over at most 7,043 s (< 2 h). All copies carry the label, including the first. Sender mix as normal traffic (80% B) | Supported | 03 B2 |
| N3 | Romance scam = one consumer paying one receiver repeatedly with escalating amounts | 500 episodes, 2–8 payments each (roughly uniform), sender always C, no prior history in the pair. Each payment ≈ 1.5× the previous (median step 1.46–1.55), ≈ 3.6 min apart, whole episode median 18 min. Small amounts (median 109 USD) | Supported | 03 B3 |
| N4 | CEO scam = business pays a new receiver an unusually large amount | Sender 100% B; pair has no history in 99.8%; amount ≈ 3.2× the sender's usual (+0.50 log); B2C median 25,556 vs normal 3,118 | Supported | 03 B4 |
| N5 | Account replacement = a usual-size payment to a new account | No pair history in 100%; amount equal to the sender's usual (+0.04 log); all four flows | Supported | 03 B4 |
| N6 | The replaced account keeps the legitimate beneficiary's name (same details, new account) | 0 of 649 matched on details text | Rejected with this test — Open: try matching on name only | 03 B4 |
| N7 | Scam payments are slower than normal ones | Median duration: romance 1,148 s, CEO 741 s, account replacement 571 s, duplicate 261 s vs 56 s normal; fat-finger and recall ≈ 53 s. Path length is the same (2.5–2.6 banks) | Supported; mechanism Open (ties to R11) | 03 timing |
| N8 | Anomalies cluster on weekends or at night | Weekend share 9.8–12.9% vs 11.2% normal | Rejected | 03 timing |

## Second pass (15 Nov) — open questions revisited. Evidence: `notebooks/04_open_questions.ipynb`
| ID | Hypothesis | Result | Status |
|---|---|---|---|
| D1 | Duration is set by the banks on the path, not by the payment (replaces R11) | Direct payments: the bank pair explains 98.4% of the variance of log10(duration) (32,734 pairs with 30+ payments; residual sd 0.11 log units). Ordering bank alone 54%, beneficiary bank alone 42%. For a given pair of banks a payment is always fast or always slow | Supported |
| D2 | Each bank has one delay, the same when sending and receiving, and delays add along the path | One delay per bank fitted on 2-bank payments predicts 3-bank `Indirect` payments it never saw: correlation 0.93 on the log scale, tight on the diagonal above 1,000 s. Fast-bank values (seconds) are imprecise; `Covered` fits worse (0.83) | Supported for slow banks; exact rule for fast banks and `Covered` Open |
| D3 | Bank speed depends on bank size | Among banks with 300+ direct payments, the largest eighth (7,689+ payments) is slow in 0.5% of cases; every other size group in 50–55% | Supported |
| D4 | Scams are slow because fraud receivers use slow banks (explains N7) | Beneficiary bank is slow for 44% of romance-scam, 41% of CEO-scam and 40% of account-replacement payments vs 17% of normal ones; romance-scam senders too (39% vs 19%). Once the banks are known, scam payments take 0.97–0.98 of the predicted time, so the banks account for the delay | Supported |
| G2 | The MQ→TN corridor comes from a single very active sender (explains G1) | One business account in MQ sent 27,737 payments to 4,687 receivers in 138 countries. Sender activity is heavy-tailed: the top 1% of accounts send 46% of all payments, and 905 of the top 1,000 are businesses | Supported |
| P6 | The beneficiary address country is fixed per account and follows a mapping from the bank country | One address country per account in 1,758,638 of 1,758,638 accounts. It equals the bank country in only 1.0% of payments, yet is concentrated: e.g. CH→UA 67%, SG→CN 72%, DE→MX 51%, US→BR 40% | Proven (fixed per account); the mapping's logic Open |
| N9 | Fat-finger = decimal separator moved, in either direction | USD fat-finger amounts end in .00 in 77.5% of cases vs 38.6% of normal USD payments; last cent digit is 0 in 88.6% vs 44.2%. Against the sender's usual level: 67% are 10× to 10,000×+ too large, 17% are more than 10× too small | Supported; how many places are moved, and how often left vs right, Open |

## Third pass (16 Nov) — completion. Evidence: `notebooks/05_completion.ipynb`. One-line statements with chart and code sources: `docs/RULES_AND_SOURCES.txt`
| ID | Hypothesis | Result | Status |
|---|---|---|---|
| P7 | IBAN-style accounts encode country, bank code and a 9-digit customer number | Bank code = first 4 characters of the BIC, country = bank country: 100% on both sides | Proven |
| P8 | The customer number identifies the party; receivers hold accounts at several banks (explains P5/P6) | 781,150 receiver accounts belong to 208,428 customer numbers, each with one address country; senders have one account each | Supported |
| P9 | Relationships repeat between parties | 39.7% of payments are in a repeating relationship by customer number vs 26.0% by account pair | Supported |
| P10 | Senders prefer receivers with nearby customer numbers | 12.0% within 1,000 numbers vs 3.4% if random (3.6×) | Supported |
| N10 | Fraud receivers are outside the sender's neighbourhood | Within 1,000 numbers: account replacement 0%, CEO 1.5%, romance 3.8% vs 12.0% normal | Supported |
| N6b | Account replacement reuses a known payee's name (second test, word overlap) | 0.5% of scams reach an overlap of 0.6 vs 18% of normal payments | Rejected |
| N11 | CUSTOMER_RECALL has a generating condition visible in the row | Matches unlabelled payments on every tested column; no twin payment | Negative result: no rule identified (see N11r) |
| R4b | Covered share depends on domestic vs cross-border only | 20.0% domestic, 10.6% cross-border, flat across 3–7 banks and across amounts | Supported |
| R7b | Endpoint mismatch replaces the path's end bank; the BIC column stays the real bank | IBAN country and bank code still match the BIC column in 100% of mismatch rows; anomalies are half as frequent there (3.9 vs 7.3 per 10,000) | Supported; the anomaly gap Open |
| T1b | Weekend effect in estimated local time | Saturday 21%, Sunday 35% of weekday level; Friday +6%, Tue/Wed −4% | Supported |

## Fourth pass (16 Nov) — peer-review fixes. Evidence: `notebooks/06_validation.ipynb`
Rules learned on the first 2/3 of the period (to 28 Jun 2023) and scored on the last 1/3, which they never saw.
| ID | Question | Held-out result | Status |
|---|---|---|---|
| D1v | Is the 98.4% for bank pairs only in-sample fit? | Pair means learned on earlier payments explain 98.20% of the variance of later direct payments; 96.59% within a factor of 2. Coverage: only pairs with 5+ training payments = 76.7% of eligible test payments. Random split inside pairs: 98.17% | D1 confirmed |
| D2v | How accurate is the additive bank-delay model? | Log correlation 0.93 but 61% within a factor of 2 (Covered 50%). Paths with a slow bank: 100% within a factor of 2; fast banks only: 34% (over-predicted about 2×) | D2 holds for slow banks; fast-bank delays Open |
| R8v | Is the FX rule circular (areas inferred and tested on the same payments)? | Areas learned on earlier direct payments: rule correct for 100.00% of later payments between pairs seen in training (0 exceptions), 99.52% between pairs never seen (521 exceptions in 109,519), and 99.94% of 3–6-bank paths never used for learning | R8 confirmed |
| N11r | CUSTOMER_RECALL wording | Changed from "assigned at random" to "no distinguishing rule identified with the tested features"; randomness is not proven | Negative result |

## Not yet explained (be upfront about these)
1. Exact per-bank delay of fast banks; how `Covered` payments combine delays (D2).
2. Why anomalies are half as frequent when a path endpoint was replaced (R7b).
3. Number of decimal places moved in a fat-finger mistake (N9).
4. What sets each currency's amount level (A4); currency choice in the remaining 13% (C1).
5. Why a receiver's accounts sit in the particular bank countries they do (P8).
