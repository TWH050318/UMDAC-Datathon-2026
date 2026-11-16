# Extracted Rules

All numbers come from executed scripts run on `data/processed/clean_payments.parquet` (n = 10,000,000; built and audited in Gate 1, see `data_issues_log.md`): Dashboard 1 from `src/02_currency_analysis.py` (log `outputs/d1_run.log`), Dashboard 2 from `src/03_amount_analysis.py` (`outputs/d2_run.log`), Dashboard 3 from `src/04_temporal_analysis.py` (`outputs/d3_run.log`). No external primary data is used. "Home currency" of a country is **derived from this dataset** (modal currency of rows whose ordering bank is in that country).

Rule index: D1 (currency): R1 concentration, R2 ordering-country currency, R3 conversion count, R4 party-pair mix, R5 amount by currency. D2 (amounts): R1 log-normal shape, R2 party-pair multipliers, R3 rounding and daily FX, R4 no $10k threshold, R5 scam amounts, R6 fat finger, R7 duplicate clusters. D3 (time): R1 local clock, R2 hour profile, R3 weekend factor, R4 B vs C, R5 weekly levels, R6 no batch spikes, R7 time independence.

---

## Dashboard 1 - Currency Patterns

### D1-R1 Currency traffic is concentrated, not uniform
- **Hypothesis:** `CURRENCY_CODE` is uniformly distributed across the 155 codes observed.
- **Reconstructed Rule:** `IF payment THEN currency is EUR with p = 31.99% and USD with p = 17.03%; top-5 = 69.47%, top-10 = 79.32%, top-20 = 86.63%` (Scope: 100% of records, n = 10,000,000; chi-square vs uniform = 222,280,002, df = 154, p < 1e-300). Head follows a power law (top-20 log-log slope -1.49, R2 = 0.985); the full tail is better fit by an exponential in rank (R2 = 0.892) than a single Zipf line (R2 = 0.804). HHI = 0.150, i.e. an effective 6.7 currencies.
- **Confounding / Negative Check:** Uniform baseline would give 0.65% each; only RUB/UAH sit near it among the top 15. A single Zipf exponent does not fit the whole tail.
- **Interpretation:** Hub currencies (EUR, USD) dominate cross-border messaging; the generator appears to use tiered weights.

### D1-R2 Currency is the ordering bank's home currency about 89% of the time
- **Hypothesis:** `CURRENCY_CODE` follows `ordering_country` (and/or `beneficiary_country`).
- **Reconstructed Rule:** `IF ordering_country = X THEN CURRENCY_CODE = home(X) with p ~ 84-95% for the 15 largest ordering countries` (Scope: 89.45% of records match the modal currency, across 182 countries with n >= 1,000; every one of the 182 has a modal currency covering >= 50% of its rows). Examples: US->USD 90.5%, CH->CHF 88.8%, GB->GBP 88.6%, CN->CNY 86.2%, DE/FR/IT/BE/LU/NL->EUR 93-94.5%. 27 ordering countries are >= 50% EUR (euro area incl. FR, DE, IT, BE, LU, NL, FI, ES, AT, IE).
- **Confounding / Negative Check:** The same test on `beneficiary_country` fails: modal currency matches only 32.20% of rows, and the modal currency is EUR for the top 15 beneficiary countries (27-38%), so the beneficiary side does not determine currency.
- **Interpretation:** Payments are mostly denominated in the sender's currency. The other 10.55% split (mutually exclusive categories): 4.63% beneficiary's home currency only, 2.34% USD/EUR with neither party's home currency, 3.58% any other currency.

### D1-R3 Conversion count 0 means the payment stayed in the ordering (and often beneficiary) currency
- **Hypothesis:** `CURRENCY_CONVERSION_COUNT == 0` changes the currency mix.
- **Reconstructed Rule:** `IF CURRENCY_CONVERSION_COUNT = 0 THEN P(currency = ordering home) = 94.93% (vs 88.78% if > 0) and P(currency = beneficiary home) = 58.46% (vs 29.00%)` (Scope: 10.87% of records, n = 1,086,531; chi-square 38,883 and 385,169, p < 1e-300; phi = 0.062 for the ordering test, a small effect, larger for beneficiary). EUR share 58.44% vs 28.76%; USD 25.84% vs 15.96%. Rows where currency matches both ordering and beneficiary home are 55.90% of conv==0 but 24.12% of conv>0; mean conversion count is 1.18 for both-home vs 1.38-1.55 otherwise (Kruskal-Wallis H = 194,505, p < 1e-300).
- **Confounding / Negative Check:** 5.07% of conv==0 rows (55,033) are not in the ordering home currency, so conv==0 is not a strict single-currency rule. Effect sizes are modest (phi 0.062); the beneficiary shift is partly mechanical (conv==0 rows skew to EUR/USD, which are also modal beneficiary currencies).
- **Interpretation:** Conversions are needed when the payment currency differs from a party's currency; hub-currency traffic needs the fewest.

### D1-R4 Currency mix differs by party pair, but weakly
- **Hypothesis:** Currency distribution is independent of `party_pair`.
- **Reconstructed Rule:** `IF party_pair = C2C THEN CHF share = 10.29% (x1.35 vs other pairs) and USD 15.83% (x0.92); IF B2B THEN CHF 6.67% (x0.79), USD 17.86% (x1.06)`. Strongest enrichment: UAH is 2.87x over-represented in C2C and 2.53x in C2B (1.54% / 1.60% of those pairs vs 0.44-0.46% in B2B/B2C); CNY is 0.66x in C2B and C2C. (Scope: C2C 15.15% of records, n = 1,514,758; chi-square party_pair x top-10 + OTHER = 31,741, df = 30, p < 1e-300, **Cramer's V = 0.0325**; two-proportion z: CHF C2C +110.4, UAH C2C +137.6.)
- **Confounding / Negative Check:** V = 0.03 means the association is statistically overwhelming (n = 10M) but practically small; EUR share is flat (31.85-32.25%) across all four pairs. No currency (n >= 1,000) is exclusive to or absent from a pair.
- **Interpretation:** Party-pair-specific corridors exist for a few currencies (UAH, CHF, CNY) but pair does not drive the currency mix overall.

### D1-R5 Median payment size depends strongly on currency
- **Hypothesis:** `USD_AMOUNT` distributions are identical across currencies.
- **Reconstructed Rule:** `IF currency = USD THEN normal median = $6,371; EUR $4,602 (x0.72); GBP $3,585 (x0.56); CHF $6,097 (x0.96); SGD $6,402 (x1.005); CNY $1,349 (x0.21); JPY $2,814 (x0.44); KRW $2,859 (x0.45); RUB $1,671 (x0.26); UAH $222 (x0.035)`. Across 130 currencies (n >= 1,000) the medians span $50.79 (YER) to $9,142 (KYD), x180. (Scope: 99.8% of records; Kruskal-Wallis on log10 USD_AMOUNT, NORMAL rows: H = 770,250, k = 130, p < 1e-300, epsilon^2 = 0.0771; Mann-Whitney vs USD p < 1e-100 for 13 of 14 top currencies, rank-biserial -0.017 for CHF to -0.629 for UAH; SGD vs USD p = 0.0015, rank-biserial -0.003, effectively equal.)
- **Confounding / Negative Check:** (i) Including anomalies gives epsilon^2 = 0.0774 and excluding only FAT_FINGER 0.0774, so anomalies do not create the effect (median shift when anomalies are included: 0.07% typical, max 6.9% for TZS). (ii) Within each party_pair epsilon^2 stays 0.077-0.098, so pair mix does not explain it. (iii) Within conv==0, only 11 currencies qualify and epsilon^2 falls to 0.010; within conv>0, 0.083, so the effect lives in converted payments. (iv) party_pair alone gives epsilon^2 = 0.211, i.e. party pair explains more amount variance than currency (Gate 3 target).
- **Economic interpretation:** Low-value local currencies (UAH, RUB, CNY, JPY, KRW) carry much smaller USD amounts. Gate 3 (D2-R3) shows non-USD amounts are round numbers in their own currency converted at a daily rate, which is consistent with amounts being generated in local units; that would let the USD level follow the currency's own scale. It does not by itself prove that mechanism for the cross-currency median differences (no external FX table is used).

### Open items
- Why the median ratio to USD is ~1.0 for SGD and CHF but 0.56 for GBP (Gate 3 did not resolve this).

---

## Dashboard 2 - Payment Amount Patterns

Source: `src/03_amount_analysis.py` (log: `outputs/d2_run.log`; tidy results: `outputs/csv/d2_amount_summary.csv`). "NORMAL" = `ANOMALY_TYPE = 'NORMAL'` (n = 9,992,994) unless stated.

### D2-R1 Normal amounts are log-normal within every party pair, with the same spread
- **Hypothesis:** log10(`USD_AMOUNT`) is normally distributed with a pair-specific location and a common scale.
- **Reconstructed Rule:** `IF payment is NORMAL THEN log10(USD_AMOUNT) ~ Normal(mu_pair, sd = 0.992-0.996)`; mu = 4.342 (B2B), 3.472 (B2C), 3.486 (C2B), 2.633 (C2C). (Scope: 100% of NORMAL rows; skew -0.12 to -0.13, excess kurtosis 0.08-0.15, KS D = 0.011-0.014 vs the fitted normal; Levene on equal sd, W = 0.3, p = 0.789.)
- **Confounding / Negative Check:** KS p-values are ~0 at this n, so D is the effect size; the shape is slightly left-skewed. The upper tail is *lighter* than log-normal (rows above $10M: B2B 6,268 observed vs 8,401 expected; above $100M: 124 vs 259). There is no hard cap: NORMAL max is $1,395,062,089.32 and min $0.01. Fine spikes in the histogram are round-number mass points (D2-R3).
- **Interpretation:** Amounts look generated as exp(location + fixed-sigma noise), with the location set by who the parties are.

### D2-R2 Each Business party multiplies the payment amount by about 7x
- **Hypothesis:** Party pair sets a multiplicative scale on amounts.
- **Reconstructed Rule:** `IF ordering party is Business THEN amount x7.04 (95% CI 7.01-7.06); IF beneficiary party is Business THEN amount x7.27 (7.25-7.30)`; medians B2B $22,883, B2C $3,118, C2B $3,236, C2C $464, so B2B/C2C = 49.35x, B2B/B2C = 7.34x, B2C/C2C = 6.72x, C2B/C2C = 6.98x. Interaction +0.017 dex (about x1.04; 95% CI +0.014 to +0.020), i.e. effects are almost exactly additive on the log scale. (Scope: 100% of NORMAL rows, Kruskal-Wallis across the four pairs H = 2,106,183, p < 1e-300, epsilon^2 = 0.211.)
- **Confounding / Negative Check:** The multipliers hold within USD only (x7.78 / x7.30), EUR only (x6.96 / x7.32), conversion count = 0 (x7.08 / x7.28) and > 0 (x7.04 / x7.26); with conversion = 0 the interaction CI includes zero (-0.005 to +0.014). Sender-vs-receiver asymmetry is negligible (B2C vs C2B rank-biserial -0.008). Party pair explains more amount variance (epsilon^2 0.211) than currency does (0.077, D1-R5), and the currency effect persists within each pair.
- **Interpretation:** Corporate payments are about an order of magnitude larger than consumer ones, and the effect compounds when both ends are corporate.

### D2-R3 USD amounts are round numbers about 38.6% of the time; other currencies are round in their own currency
- **Hypothesis:** Rounding differs by currency, and non-USD amounts are round in local currency before conversion at a daily rate.
- **Reconstructed Rule (USD):** `IF CURRENCY_CODE = USD THEN amount is whole-dollar with p = 38.64%` (vs 0.99% for non-USD, where 1.00% is chance for 2-decimal amounts; n = 1,702,039 vs 8,290,955; z = 1,709). Independent of conversion count (cc = 0: 38.8%, 1: 38.6%, 2: 38.5%, 3+: 38.8%). 13.55% of USD amounts >= $100 are of the form {1,2,2.5,3,4,5,6,7.5,8,10} x 10^k; the most repeated exact amounts are $10,000 (35,634 rows), $1,000 (32,609), $5,000 (21,703), $100,000 (16,988), $500, $100, $50,000.
- **Reconstructed Rule (non-USD):** `IF CURRENCY_CODE != USD THEN USD_AMOUNT = round(L x rate_day, 2) where L is a round local amount and rate_day is a UTC-day-specific rate`. Rate reconstructed from each day's most repeated anchor amount (>= 3 repeats; found on 91-92 of 93 days). Share of rows (>= $100) that are a round local amount at that day's rate: EUR 13.43%, GBP 13.39%, CHF 13.41%, SGD 12.38%, CNY 12.83% (n = 0.28M-2.99M each), which equals the USD baseline of 13.55%. (Scope: all non-USD currencies tested, 5 of them; EUR anchor ranges 1,100.72-1,217.69 per 1,000 round units, moves a median 0.60% per day, Spearman with date +0.83.)
- **Confounding / Negative Check:** Placebo using another day's rate: 0.00-0.01% match; a single constant rate: 0.00-0.06% match. The match tolerance covers the cent rounding of both the amount and the anchor. Rounding by party pair is *not* a rule: multiples of $1,000 within USD run 12.3-20.6% across pair x magnitude cells, with no consistent ordering (B2B highest at 10^3, C2C highest at 10^5; chi-square p < 0.05 is a sample-size effect). The L = 1,000 interpretation of the anchor is an assumption; the proof is the day-specific fit, not the unit.
- **Interpretation:** The generator draws an amount in the payment currency (round with fixed probability), then converts to USD at a daily rate; USD-denominated payments skip the conversion.

### D2-R4 No $10,000 reporting-threshold or structuring effect
- **Hypothesis:** Amounts avoid or cluster near $10,000.
- **Reconstructed Rule:** `NO effect`: 13,482 rows in [9,900, 10,000) vs 13,364 in (10,000, 10,100] (ratio 1.009; binomial p = 0.475). The only feature at 10,000 is the round-number spike (35,634 rows at exactly $10,000.00, 0.357% of NORMAL). (Scope: n = 26,846 around the threshold.)
- **Confounding / Negative Check:** No dip below or bump above the cutoff; no cap or floor besides the $0.01 minimum (11,645 NORMAL rows below $1).
- **Interpretation:** Reporting-cutoff behaviour is not part of the generator; spikes come from round-number sampling.

### D2-R5 Scam labels shift amounts by party pair; ACCOUNT_REPLACEMENT_SCAM, DUPLICATE_PAYMENT and CUSTOMER_RECALL do not
- **Hypothesis:** Anomaly labels have distinct amount distributions from NORMAL in the same party pair.
- **Reconstructed Rule:** `IF ROMANCE_SCAM (only C2B/C2C) THEN median $120.77 (C2B, 0.037x NORMAL) / $104.65 (C2C, 0.226x)` (n = 665 / 1,811; MWU p = 2e-165 / 3e-111; rank-biserial -0.61 / -0.30). `IF CEO_SCAM (only B2B/B2C) AND B2C THEN median $25,556 = 8.2x NORMAL B2C` (n = 683; p = 2.6e-70; rank-biserial +0.39); CEO_SCAM B2B 0.66x is not significant (n = 262, p = 0.23).
- **Confounding / Negative Check:** ACCOUNT_REPLACEMENT_SCAM (all four pairs, p = 0.14-0.88), CUSTOMER_RECALL (p = 0.18-0.53) and DUPLICATE_PAYMENT (p = 0.015-0.82, marginal in B2B/C2C and not a consistent direction) are not detectable by amount. Scope is small: the scam labels are 4,070 of 7,006 anomaly rows (0.04% of all rows).
- **Interpretation:** Romance scams are small consumer transfers; CEO fraud targets large corporate-to-consumer payments.

### D2-R6 FAT_FINGER amounts are inflated by one to three orders of magnitude, with no single fixed factor
- **Hypothesis:** `FAT_FINGER_MISTAKE` rows are decimal-shifted versions of a normal amount (e.g. 10x/100x).
- **Reconstructed Rule:** `IF FAT_FINGER_MISTAKE THEN amount is a median 86.3x (+1.94 dex) the sender's own NORMAL median; 66.1% are >= 10x and 48.8% are >= 100x (NORMAL rows: 14.8% and 2.1%)`; vs the NORMAL median of the same pair it is 85.9x (B2B), 69.8x (B2C), 35.0x (C2B), 109.4x (C2C). (Scope: 1,940 rows = 0.019%; 1,874 with >= 3 NORMAL rows on the sending account; KS D = 0.522, p ~ 0; MWU vs NORMAL p < 1e-13 in every pair.)
- **Confounding / Negative Check:** The shift distribution is broad (about +0.5 to +4 dex, peaking at +2.0 to +3.0), not a spike at exactly +1 or +2, so a single 10x/100x multiplier is **not** supported; the sender baseline (a median of that account's other payments) is itself noisy. 17.2% are <= 1/10 of the sender's median and 10.6% are <= 1/100 (NORMAL 14.4% / 1.7%), so a minority look like downward shifts. Only 279 FAT_FINGER rows exceed the NORMAL p99.99, so extreme amounts alone cannot identify them (Gate 1). The NORMAL reference sample includes each row in its own median, a slight bias toward 0.
- **Interpretation:** Fat-finger errors inflate amounts mostly by extra digits; they are identifiable relative to a sender's history, not by absolute size.

### D2-R7 DUPLICATE_PAYMENT is a cluster of 2-5 payments with the same account pair and amount within two hours
- **Hypothesis:** Rows labelled `DUPLICATE_PAYMENT` repeat a payment.
- **Reconstructed Rule:** `IF DUPLICATE_PAYMENT THEN another row exists with identical ORDERING_ACCOUNT, BENEFICIARY_ACCOUNT and USD_AMOUNT, also labelled DUPLICATE_PAYMENT, within 7,043 s (median 2,145 s)` (Scope: 679 of 679 labelled rows = 100%, forming 185 clusters: 37 of size 2, 43 of size 3, 49 of size 4, 56 of size 5; time gap quartiles 884 / 2,145 / 3,581 s, 95th percentile 5,538 s).
- **Confounding / Negative Check:** The same account-pair-plus-amount twin exists for only 0.056% of NORMAL rows (5,560 of 9,992,994) and 0.89% of ROMANCE_SCAM rows. Gate 1 found only one byte-identical row across all 20 columns, so the cluster members differ in other fields (e.g. timestamp). The label sits on every member of a cluster, so the original payment is also labelled.
- **Interpretation:** Duplicates are re-submitted payments (same sender, receiver and amount) within a short window; they can be detected by this key without the label.

### Open items
- Do duplicate clusters differ in other fields beyond timestamp (route, BIC path, duration)?
- Does the 0.056% NORMAL twin rate come from legitimate repeated payments or unlabelled duplicates?
- (Timing of scams and duplicates was tested in Gate 4: see D3-R7.)

---

## Dashboard 3 - Temporal Patterns

Source: `src/04_temporal_analysis.py` (log: `outputs/d3_run.log`; tidy results: `outputs/csv/d3_temporal_summary.csv`). Rate comparisons use the complete 13-week window Mon 2023-05-01 to Sun 2023-07-30 (9,991,528 rows; the file starts Sun 30 Apr 11:22 UTC and ends Mon 31 Jul 09:56 UTC, so partial edge days are excluded). "Local time" uses a UTC offset per ordering country **inferred from the data**; no external timezone table is used.

### D3-R1 Volume follows the sender's local clock, not UTC
- **Hypothesis:** The weekend drop and hour-of-day profile are defined in each ordering country's local time.
- **Reconstructed Rule:** `IF ordering_country = X THEN payment timestamp = local time at offset off(X) from UTC, with weekends (Sat/Sun local) carrying 10.0% of volume`. The offset that minimises the local-weekend share gives 9.88%-10.45% (sd 0.13 pp) across all 35 ordering countries with >= 50,000 rows (83.5% of rows), versus 10.03%-14.23% (sd 1.17 pp) in UTC. Fitted offsets: GB/IM/IE/JE 0; CH, FR, DE, IT, BE, LU, NL, ES, AT, DK, LI +1; FI, UA, IL +2; SA, RU, QA, TR +3; AE +4; IN +5; SG, CN, HK, MY +8; JP, KR +9; AU +11; US, CA, PA -5; AR -3. (Scope: 8,347,845 rows = 83.5%; the offset-vs-weekend-share curve is shallow, about 0.1-0.4 pp per hour.)
- **Confounding / Negative Check:** (i) Independent cross-check: aligning each country's UTC hour profile to the pooled local profile recovers exactly the same offset for 35 of 35 countries (median best-fit r = 0.999). (ii) Negative control on 6,514,441 cross-border rows: weekend share is 10.08% in the *ordering* country's local time, 12.10% in the *beneficiary* country's local time and 11.10% in UTC, so the sender's clock, not the receiver's, drives timing. (iii) The offsets match fixed standard-time zones (e.g. GB 0, CET +1), so no daylight-saving shift is visible, and AU +11 has a flat curve (+10 gives 10.42% vs 10.29%).
- **Interpretation:** Consistent with the generator drawing a local timestamp for the sending institution and converting it to UTC. The country-to-offset link behaves like real time zones, even though other geographic distributions were randomised by Swift.

### D3-R2 One local-time hour-of-day profile applies to every country
- **Hypothesis:** After local-time alignment all countries share a single double-peaked daily profile.
- **Reconstructed Rule:** `IF local hour h THEN share of payments = profile(h)`: peak 18:00 (7.64%), strong peaks at 07:00 (7.5%), 16:00 (7.5%), 17:00 (7.4%); mid-day plateau 4.3-5.5% for 11:00-15:00; overnight floor 0.98%-1.1% for 01:00-05:00 (trough 04:00). Peak/trough x7.8, versus only x2.7 in pooled UTC (UTC peak 15:00 = 5.86%, trough 03:00 = 2.18%). (Scope: 8,347,845 rows; per-country local profile vs pooled: min Pearson r = 0.955 (IN), max total-variation distance 0.055, versus 0.330 on UTC hours.)
- **Confounding / Negative Check:** The profile differs a little between local weekdays and weekends (chi-square V = 0.101), so weekends are flatter rather than a pure scale-down. Hour-of-day chi-square vs uniform is huge (UTC: chi2 = 731,003, p < 1e-300), confirming the shape is real.
- **Interpretation:** Business-hour clustering (morning 07:00, afternoon-evening 16:00-19:00) with a quiet night, observed at the sender's clock.

### D3-R3 Weekends carry 28% of a weekday's volume per day; Sunday exceeds Saturday
- **Hypothesis:** Day-of-week volume is flat versus a weekend drop.
- **Reconstructed Rule:** `IF local day is Sat or Sun THEN volume = 0.280 x a weekday day`; relative to Monday (=1.000): Tue 0.901, Wed 0.901, Thu 0.953, Fri 1.005, Sat 0.190, Sun 0.344 (Sat/Sun 0.552). In UTC the per-day ratio is 0.313 (Mon 140,875, Tue 131,422, Wed 131,124, Thu 138,542, Fri 141,054, Sat 33,457, Sun 52,106 per day) and weekend rows are 11.13% of volume. (Scope: 100% of complete-week rows; local-time figures use the 83.5% fitted countries.)
- **Confounding / Negative Check:** The weekend/weekday ratio varies only 0.292-0.330 across the 13 weeks despite a x2.4 change in weekly volume (D3-R5), so it is not a by-product of the weekly level. In UTC the weekend share by hour ranges from 8.0% (06:00) to 17.9% (00:00); that spread is what the country time-zone mixture produces (D3-R1), not a separate rule. The Tue/Wed dip (0.901) and the Sat < Sun asymmetry were measured on pooled data only and were not tested per country or per week.
- **Interpretation:** Weekday processing with a mid-week trough; Sunday carries more than Saturday (0.344 vs 0.190 of Monday). The generator's reason for this asymmetry is not identified.

### D3-R4 Corporate and consumer senders share the same schedule (hypothesis rejected)
- **Hypothesis:** `ORDERING_TYPE = B` drops sharply on weekends and clusters in business hours, while `C` stays active.
- **Reconstructed Rule:** `NO difference`: local weekend share B 10.07% vs C 10.09% (z = -0.5); per-day weekend factor 0.280 for both; B2B, B2C, C2B, C2C local weekend share 10.07%-10.12%. Local hour profiles differ only slightly (chi-square V = 0.026; max hour-share difference 0.62 pp; peak B 16:00 at 7.66%, C 18:00 at 8.09%). (Scope: B senders n = 6,586,947, C senders n = 1,760,898.)
- **Confounding / Negative Check:** In UTC, B's share of senders is 77.4%-79.7% across hours (overall 78.75%; V = 0.016) and does not change with day of week (V = 0.0016); the B share dips about 1.4 pp below average at 17:00 UTC and peaks about 1.0 pp above it at 08:00 UTC, a small effect that was not traced to a cause (the local-time profiles differ by V = 0.026).
- **Interpretation:** Timing is a property of the sending institution's location, not of whether the sender is a business or an individual.

### D3-R5 Weekly volume moves between six discrete levels with unchanged composition
- **Hypothesis:** Week-to-week volume is a smooth trend; or discrete multipliers.
- **Reconstructed Rule:** `IF ISO week w THEN weekday volume = L(w) per day, L in {88,877; 106,316; 133,031; 151,073; 168,729; 213,126}` = x1.000, x1.196, x1.497, x1.700, x1.898, x2.398 of the lowest level. Weeks by level: 19, 20, 27 at 88,877 (spread 0.16%); 28 at 106,316; 18, 23, 29 at 133,031 (0.55%); 21, 22, 24 at 151,073 (0.28%); 26, 30 at 168,729 (0.11%); 25 at 213,126. (Scope: weeks 18-30, 9,991,528 rows; within-week weekday CV median 0.036.)
- **Confounding / Negative Check:** Composition is unchanged across weeks: Cramer's V for week x ordering type 0.0011 (p = 0.47), party pair 0.0011 (p = 0.42), routing type 0.0010 (p = 0.62), currency 0.0018, ordering country 0.0015, UTC hour 0.0030 (the last three have p < 1e-6 only because n = 10M); hour profile in the lowest vs highest level weeks V = 0.0065; NORMAL amount by week Kruskal-Wallis epsilon^2 = 0.00000. Equal-level weeks agree to 0.1-0.6%, which a random walk would not produce.
- **Interpretation:** A weekly volume multiplier (campaign or load factor) scales all traffic proportionally; it carries no information about who pays or how much. The ratios 1.2, 1.5, 1.7, 1.9, 2.4 look like a small fixed set of multipliers.

### D3-R6 No batch, minute or second effects in timestamps
- **Hypothesis:** Payments spike at batch times (top of hour, 5-minute boundaries, specific seconds).
- **Reconstructed Rule:** `NO effect`: minute-of-hour chi2 = 82.3 (df 59, p = 0.024) and second-of-minute chi2 = 73.8 (p = 0.093); max/min cell share 1.677%/1.654% vs 1.667% uniform. Timestamps exactly on the hour: 0.0277% (expected 0.0278%); on a 5-minute boundary 0.3307% (0.3333%); on a whole minute 1.6702% (1.6667%). (Scope: n = 10,000,000.)
- **Confounding / Negative Check:** The minute-of-hour p = 0.024 is a weak deviation (every minute within 0.015 pp of the uniform 1.667%) and not a spike; 76.41% of rows share their exact second with at least one other payment (max 13) simply because of volume (~1.3 payments per second on average).
- **Interpretation:** Sub-hour timing is uniform; there is no batch-processing structure to extract.

### D3-R7 Amount, routing type and anomaly labels are independent of time of day and weekend
- **Hypothesis:** Amounts, routing type or anomaly labels vary with time.
- **Reconstructed Rule:** `NO effect` once country mix is controlled. Median NORMAL amount varies x1.56 by UTC hour ($2,800 at 04:00 to $4,357 at 21:00; epsilon^2 = 0.00113) but only epsilon^2 = 0.00010 by local hour and 0.00008 within ordering_country = US alone, so the UTC pattern is a country-mix effect. Weekend vs weekday: B senders median $6,639 vs $6,644 (p = 0.44), C senders $945 vs $942 (p = 0.94). `Direct` share is 63.22% on local weekends vs 63.23% on weekdays; routing type x UTC hour V = 0.0137. (Scope: NORMAL rows of the fitted countries.)
- **Confounding / Negative Check:** Anomaly labels have local weekend shares of 8.4%-12.0% vs 10.1% NORMAL (all p >= 0.085). Sender-type-matched 6-hour block tests: ROMANCE_SCAM p = 0.022, CEO_SCAM 0.096, ACCOUNT_REPLACEMENT_SCAM 0.47, FAT_FINGER 0.30, CUSTOMER_RECALL 0.25 (none survive a 6-test Bonferroni threshold of 0.0083); DUPLICATE_PAYMENT p = 0.00019, which is not interpretable because its rows come in 2-5-row clusters within two hours (D2-R7), violating independence.
- **Interpretation:** Time determines *when* payments are initiated, not their size, routing or label; anomaly types are injected independently of the clock.

### Open items
- The weekly multiplier schedule (which week gets which level) may have a rule; 13 weeks are too few to test.
- Whether the 0.28 weekend factor and the Sat/Sun asymmetry (0.19 vs 0.34 of Monday) are generator constants or country-specific.
