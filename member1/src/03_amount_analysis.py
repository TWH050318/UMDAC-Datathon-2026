"""
Gate 3 / Dashboard 2: Payment Amount Patterns
=============================================
Hypotheses (data/processed/clean_payments.parquet only; no external FX/GDP tables):
  A  log10(USD_AMOUNT) of NORMAL traffic is ~normal (log-normal) within each party_pair.
  B  Party pair sets a multiplicative scale: each Business party multiplies the amount by a constant.
  C  Hard thresholds / caps / structuring just below 10,000 USD.
  D  Rounding: USD-denominated amounts are round numbers; non-USD amounts are round numbers in LOCAL
     currency converted at a daily rate (tested by reconstructing the daily rate from mass points,
     with a shifted-date placebo).
  E  Anomaly labels: amount level vs NORMAL (same party_pair); FAT_FINGER scale vs the sender's own
     normal amounts; DUPLICATE_PAYMENT = same account pair + same amount.
Outputs: outputs/csv/d2_amount_summary.csv, outputs/charts/d2_*.png
"""
import os
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQ = os.path.join(BASE, "data", "processed", "clean_payments.parquet").replace("\\", "/")
CSV_OUT = os.path.join(BASE, "outputs", "csv", "d2_amount_summary.csv")
CH_DIR = os.path.join(BASE, "outputs", "charts")
os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True); os.makedirs(CH_DIR, exist_ok=True)
con = duckdb.connect()
Q = f"read_parquet('{PARQ}')"
def df(sql): return con.execute(sql).df()
def hdr(t): print("\n" + "=" * 76 + f"\n  {t}\n" + "=" * 76)
BLOCKS = []     # tidy rows for the summary CSV
def add(block, **kw): BLOCKS.append({"block": block, **kw})
PAIRS = ["B2B", "B2C", "C2B", "C2C"]

N = con.execute(f"SELECT COUNT(*) FROM {Q}").fetchone()[0]
amt = df(f"SELECT party_pair pp, CURRENCY_CODE cur, CURRENCY_CONVERSION_COUNT cc, ANOMALY_TYPE a, "
         f"USD_AMOUNT x, utc_dt FROM {Q}")
amt["lx"] = np.log10(amt.x)
nm = amt[amt.a == "NORMAL"]
print(f"Rows {N:,}; NORMAL {len(nm):,}")

# ── A: shape per party pair ────────────────────────────────────────────────
hdr("A  Distribution shape of log10(USD_AMOUNT), NORMAL rows")
shape = {}
print(f"{'pair':<6}{'n':>10}{'median $':>12}{'mean log10':>12}{'sd log10':>10}{'skew':>8}{'ex.kurt':>9}{'KS D':>8}{'p10-p90 dex':>13}")
for pr in PAIRS:
    v = nm[nm.pp == pr].lx.values
    mu, sd = v.mean(), v.std()
    D, p = stats.kstest((v - mu) / sd, "norm")
    q10, q90 = np.quantile(v, [.1, .9])
    shape[pr] = dict(n=len(v), median=10 ** np.median(v), mu=mu, sd=sd, skew=stats.skew(v), kurt=stats.kurtosis(v), D=D)
    print(f"{pr:<6}{len(v):>10,}{10**np.median(v):>12,.2f}{mu:>12.4f}{sd:>10.4f}{stats.skew(v):>8.3f}{stats.kurtosis(v):>9.3f}{D:>8.4f}{q90-q10:>13.3f}")
    add("shape", party_pair=pr, **{k: float(v_) for k, v_ in shape[pr].items()}, ks_p=float(p))
print("  (KS p-values are ~0 at this n; the D statistic is the effect size. D<0.02 ~ visually log-normal.)")
# expected vs observed tail counts under the fitted log-normal (per pair)
print("\n  Tail check: observed NORMAL rows above threshold vs fitted log-normal expectation")
for thr in (1e7, 1e8, 1e9):
    for pr in PAIRS:
        s = shape[pr]; obs = int((nm[nm.pp == pr].x > thr).sum())
        exp = s["n"] * stats.norm.sf((np.log10(thr) - s["mu"]) / s["sd"])
        print(f"    {pr} > {thr:>8.0e}: observed {obs:>6,}  expected {exp:>10,.1f}  ratio {obs/max(exp,1e-9):.2f}")
        add("tail", party_pair=pr, threshold=thr, observed=obs, expected=float(exp))
sd_all = [shape[p]["sd"] for p in PAIRS]
lev = stats.levene(*[nm[nm.pp == p].lx.sample(200_000, random_state=1).values for p in PAIRS])
print(f"\n  sd(log10) by pair: {', '.join(f'{p}={s:.3f}' for p, s in zip(PAIRS, sd_all))}; Levene (200k per pair) W={lev.statistic:.1f}, p={lev.pvalue:.3g}")

# ── B: multipliers ─────────────────────────────────────────────────────────
hdr("B  Party-pair multipliers (additive model on log10)")
def mult_table(sub, label):
    m = {p: sub[sub.pp == p].lx.mean() for p in PAIRS}
    s = {p: sub[sub.pp == p].lx.std() for p in PAIRS}
    n = {p: (sub.pp == p).sum() for p in PAIRS}
    if min(n.values()) < 1000: return None
    se = lambda ps: np.sqrt(sum(s[p] ** 2 / n[p] for p in ps))
    # B-sender effect: (B2B+B2C)/2 - (C2B+C2C)/2 ; B-receiver effect: (B2B+C2B)/2 - (B2C+C2C)/2
    ord_eff = (m["B2B"] + m["B2C"]) / 2 - (m["C2B"] + m["C2C"]) / 2
    ben_eff = (m["B2B"] + m["C2B"]) / 2 - (m["B2C"] + m["C2C"]) / 2
    inter = (m["B2B"] - m["B2C"]) - (m["C2B"] - m["C2C"])
    se_o = se(PAIRS) / 2; se_i = se(PAIRS)
    medr = {p: sub[sub.pp == p].x.median() for p in PAIRS}
    print(f"  [{label}] n={len(sub):,}")
    print(f"     medians: " + ", ".join(f"{p}=${medr[p]:,.0f}" for p in PAIRS))
    print(f"     B-ordering effect {ord_eff:+.3f} dex (x{10**ord_eff:.2f}, 95% CI x{10**(ord_eff-1.96*se_o):.2f}-x{10**(ord_eff+1.96*se_o):.2f})")
    print(f"     B-beneficiary effect {ben_eff:+.3f} dex (x{10**ben_eff:.2f}, 95% CI x{10**(ben_eff-1.96*se_o):.2f}-x{10**(ben_eff+1.96*se_o):.2f})")
    print(f"     interaction {inter:+.3f} dex (95% CI {inter-1.96*se_i:+.3f}..{inter+1.96*se_i:+.3f})")
    print(f"     median ratios: B2B/C2C x{medr['B2B']/medr['C2C']:.2f}; B2B/B2C x{medr['B2B']/medr['B2C']:.2f}; "
          f"B2C/C2C x{medr['B2C']/medr['C2C']:.2f}; C2B/C2C x{medr['C2B']/medr['C2C']:.2f}; B2C/C2B x{medr['B2C']/medr['C2B']:.3f}")
    add("multiplier", subset=label, n=len(sub), ordering_B_mult=10 ** ord_eff, beneficiary_B_mult=10 ** ben_eff,
        interaction_dex=inter, **{f"median_{p}": medr[p] for p in PAIRS})
    return ord_eff, ben_eff, inter
base_mult = mult_table(nm, "ALL NORMAL")
mult_table(nm[nm.cur == "USD"], "USD only")
mult_table(nm[nm.cur == "EUR"], "EUR only")
mult_table(nm[nm.cc == 0], "conversion count == 0")
mult_table(nm[nm.cc > 0], "conversion count > 0")
mw = stats.mannwhitneyu(nm[nm.pp == "B2C"].lx.values, nm[nm.pp == "C2B"].lx.values)
print(f"\n  B2C vs C2B (sender vs receiver symmetry): MWU p={mw.pvalue:.3g}, rank-biserial={2*mw.statistic/(shape['B2C']['n']*shape['C2B']['n'])-1:+.4f}")
kwp = stats.kruskal(*[nm[nm.pp == p].lx.values for p in PAIRS])
print(f"  Kruskal-Wallis across 4 pairs: H={kwp.statistic:,.0f}, p={kwp.pvalue:.3g}, epsilon^2={(kwp.statistic-3)/(len(nm)-4):.4f}")
# with anomalies
allm = {p: amt[amt.pp == p].x.median() for p in PAIRS}
print("  Medians incl. anomalies: " + ", ".join(f"{p}=${allm[p]:,.0f}" for p in PAIRS))

# ── C: thresholds ──────────────────────────────────────────────────────────
hdr("C  Thresholds, caps, floors")
print(f"  NORMAL min ${nm.x.min():.2f}; max ${nm.x.max():,.2f}; rows < $1: {(nm.x<1).sum():,}")
below = int(((nm.x >= 9900) & (nm.x < 10000)).sum()); above = int(((nm.x > 10000) & (nm.x <= 10100)).sum())
exact = int((nm.x == 10000).sum())
tb = stats.binomtest(below, below + above, 0.5)
print(f"  Just-below vs just-above 10,000 (width $100): {below:,} vs {above:,} (ratio {below/above:.3f}; binomial p={tb.pvalue:.3g}); exactly 10,000.00: {exact:,}")
print("  -> no structuring dip/bump around the $10,000 reporting cutoff" if tb.pvalue > 0.01 else "  -> asymmetry around 10,000 (see ratio)")
add("threshold", name="10k_below", n=below); add("threshold", name="10k_above", n=above); add("threshold", name="10k_exact", n=exact)
print("\n  Exact repeated USD amounts (NORMAL) - top 12:")
rep = nm.groupby("x").size().sort_values(ascending=False).head(12)
for v, n in rep.items():
    print(f"    ${v:>12,.2f}  {n:>7,}  ({n/len(nm):.3%})")
    add("repeated_amount", amount=float(v), n=int(n))
print(f"  Normal rows at any amount repeated >= 1000 times: {int(nm.groupby('x').size().loc[lambda s: s>=1000].sum()):,}")

# ── D: rounding ────────────────────────────────────────────────────────────
hdr("D  Rounding structure")
nm = nm.assign(whole=(nm.x == nm.x.round()))
usd = nm[nm.cur == "USD"]; non = nm[nm.cur != "USD"]
w1, w0 = usd.whole.mean(), non.whole.mean()
z, p = (lambda a, b, n1, n2: ((a - b) / np.sqrt(((a * n1 + b * n2) / (n1 + n2)) * (1 - (a * n1 + b * n2) / (n1 + n2)) * (1 / n1 + 1 / n2)), None))(w1, w0, len(usd), len(non))
print(f"  Whole-dollar share: USD {w1:.2%} (n={len(usd):,}) vs non-USD {w0:.2%} (n={len(non):,}); z={z:.0f}; chance for 2-decimal amounts = 1.00%")
add("rounding", name="whole_USD", value=float(w1), n=len(usd)); add("rounding", name="whole_nonUSD", value=float(w0), n=len(non))
byc = nm.groupby("cur").whole.agg(["mean", "size"]).query("size>=50000").sort_values("size", ascending=False)
print("  Whole-dollar share by currency (n >= 50,000): " + ", ".join(f"{c}={r['mean']:.1%}" for c, r in byc.iterrows()))
print(f"  USD whole-dollar share by conversion count: " + ", ".join(f"cc={k}: {v:.1%}" for k, v in usd.groupby(usd.cc.clip(upper=3)).whole.mean().items()))
# roundness within USD by pair, stratified by magnitude decade
usd = usd.assign(dec=np.floor(usd.lx).astype(int))
def rnd_flag(x, m): return np.isclose(np.mod(x, m), 0) | np.isclose(np.mod(x, m), m)
usd = usd.assign(r100=rnd_flag(usd.x, 100) & (usd.x >= 100), r1000=rnd_flag(usd.x, 1000) & (usd.x >= 1000))
print("\n  USD NORMAL: share of amounts that are multiples of 1,000 (>=1,000) by pair and magnitude decade:")
tab = usd[usd.dec.between(3, 6)].pivot_table(index="dec", columns="pp", values="r1000", aggfunc="mean")[PAIRS]
cnt = usd[usd.dec.between(3, 6)].pivot_table(index="dec", columns="pp", values="r1000", aggfunc="size")[PAIRS]
print((tab * 100).round(2).to_string())
print("  n per cell:"); print(cnt.to_string())
for d in tab.index:
    ct = np.array([[usd[(usd.dec == d) & (usd.pp == p)].r1000.sum(), ((usd.dec == d) & (usd.pp == p)).sum() - usd[(usd.dec == d) & (usd.pp == p)].r1000.sum()] for p in PAIRS])
    chi, pv, _, _ = stats.chi2_contingency(ct)
    print(f"    decade 10^{d}: chi2={chi:,.0f}, p={pv:.3g}")
    for p in PAIRS: add("round1000_by_decade", decade=int(d), party_pair=p, share=float(tab.loc[d, p]), n=int(cnt.loc[d, p]))
print("\n  USD NORMAL overall share multiple of $100 (>=100) / $1,000 (>=1,000): "
      f"{usd.r100.sum()/(usd.x>=100).sum():.2%} / {usd.r1000.sum()/(usd.x>=1000).sum():.2%}")

# daily-rate reconstruction for non-USD currencies
print("\n  Reconstructing daily conversion rate from mass points (anchor = most repeated value's decade):")
nm = nm.assign(day=nm.utc_dt.dt.floor("D"))
ROUNDSET = np.array([1, 2, 2.5, 3, 4, 5, 6, 7.5, 8])
def nearest_round_rel(w):
    # w>0; relative distance to nearest {1,2,2.5,3,4,5,6,7.5,8}*10^k and 10^k
    mant = w / 10 ** np.floor(np.log10(w))
    cand = np.concatenate([ROUNDSET, [10]])
    d = np.abs(mant[:, None] / cand[None, :] - 1)
    return d.min(axis=1)
recon = {}
# baseline for comparison: USD amounts are already in 'local' units -> share that are round numbers of the same set
u100 = usd[usd.x >= 100]
usd_round = (nearest_round_rel(u100.x.values) <= 0.0051 / u100.x.values + 1e-9).mean()
print(f"  Baseline: share of USD NORMAL rows (>=$100) that are in the round set {{1,2,2.5,3,4,5,6,7.5,8,10}}x10^k: {usd_round:.2%}")
add("rounding", name="usd_round_set_share", value=float(usd_round), n=len(u100))
for cur in ["EUR", "GBP", "CHF", "SGD", "CNY"]:
    s = nm[nm.cur == cur]
    top = s.groupby("x").size().sort_values(ascending=False).head(30)
    dec = int(np.floor(np.log10(top.index[0])))
    inb = [v for v in top.index if int(np.floor(np.log10(v))) == dec]
    v_anchor = float(np.median(inb)); lo, hi = v_anchor * 0.88, v_anchor * 1.12
    win = s[(s.x >= lo) & (s.x <= hi)]
    g = win.groupby(["day", "x"]).size().reset_index(name="n")
    best = g.sort_values(["day", "n"], ascending=[True, False]).groupby("day").head(1).set_index("day")
    best = best[best.n >= 3]
    idx = best.x
    if len(idx) < 30:
        print(f"    {cur}: only {len(idx)} days with a repeated anchor value -> not reconstructable"); continue
    ndays = s.day.nunique()
    sd = s[s.x >= 100].copy()
    sd["idx"] = sd.day.map(idx)
    ok = sd.dropna(subset=["idx"]).copy()
    # tolerance: USD amount is cent-rounded (0.005/x) AND the anchor itself is cent-rounded (0.005/idx,
    # an error that scales with the amount) -> relative tol = 0.0051/x + 0.0051/idx
    tol = 0.0051 / ok.x + 0.0051 / ok.idx
    w = ok.x / ok.idx
    hit = nearest_round_rel(w.values) <= tol.values * 1.0 + 1e-9
    # placebo: idx of the day 17 days later (wrap), same rows
    days = sorted(idx.index); shift = {d: days[(i + 17) % len(days)] for i, d in enumerate(days)}
    idx_pl = ok.day.map(shift).map(idx)
    w_pl = ok.x / idx_pl
    tol_pl = 0.0051 / ok.x + 0.0051 / idx_pl
    hit_pl = nearest_round_rel(w_pl.values) <= tol_pl.values + 1e-9
    # also unanchored sanity: a global constant idx (median) instead of daily
    w_gl = ok.x / idx.median()
    hit_gl = nearest_round_rel(w_gl.values) <= (0.0051 / ok.x + 0.0051 / idx.median()).values + 1e-9
    recon[cur] = dict(true=hit.mean(), placebo=hit_pl.mean(), const=hit_gl.mean(), n=len(ok), days=len(idx), ndays=ndays,
                      rmin=idx.min(), rmax=idx.max(), anchor=v_anchor, idx=idx)
    print(f"    {cur}: anchor ~{v_anchor:,.2f}; daily mode found on {len(idx)}/{ndays} days, range {idx.min():,.2f}-{idx.max():,.2f}; "
          f"rows (>=$100, covered days) n={len(ok):,}; matches a round local amount at that day's rate: {hit.mean():.2%} | "
          f"placebo (rate of another day): {hit_pl.mean():.2%} | single constant rate: {hit_gl.mean():.2%}")
    add("rate_reconstruction", currency=cur, anchor=v_anchor, days_found=len(idx), rate_min=float(idx.min()), rate_max=float(idx.max()),
        n=len(ok), match_true=float(hit.mean()), match_placebo=float(hit_pl.mean()), match_constant=float(hit_gl.mean()))
if "EUR" in recon:
    e = recon["EUR"]["idx"].sort_index()
    print(f"  EUR daily anchor series: first {e.iloc[0]:,.2f}, last {e.iloc[-1]:,.2f}; day-to-day |change| median "
          f"{e.diff().abs().median():.2f} ({e.diff().abs().median()/e.median():.2%}); Spearman(date, anchor) = "
          f"{stats.spearmanr(np.arange(len(e)), e.values).statistic:+.3f}")

# ── E: anomaly labels ──────────────────────────────────────────────────────
hdr("E  Anomaly labels vs NORMAL (same party_pair)")
med_pp = nm.groupby("pp").x.median()
rows = []
print(f"{'label':<26}{'pair':<6}{'n':>7}{'median $':>12}{'x NORMAL-pair':>14}{'MWU p':>10}{'rank-bis':>10}")
for lab in ["ROMANCE_SCAM", "CEO_SCAM", "ACCOUNT_REPLACEMENT_SCAM", "FAT_FINGER_MISTAKE", "DUPLICATE_PAYMENT", "CUSTOMER_RECALL"]:
    for pr in PAIRS:
        a = amt[(amt.a == lab) & (amt.pp == pr)]
        if len(a) < 20: continue
        ref = nm[nm.pp == pr].lx.values
        u, pv = stats.mannwhitneyu(a.lx.values, ref)
        rb = 2 * u / (len(a) * len(ref)) - 1
        print(f"{lab:<26}{pr:<6}{len(a):>7,}{a.x.median():>12,.2f}{a.x.median()/med_pp[pr]:>14.3f}{pv:>10.2g}{rb:>10.3f}")
        add("anomaly_amount", label=lab, party_pair=pr, n=len(a), median=float(a.x.median()), ratio_to_normal_pair=float(a.x.median() / med_pp[pr]),
            mwu_p=float(pv), rank_biserial=float(rb))
print("  Label overall: ")
for lab in ["ROMANCE_SCAM", "CEO_SCAM", "ACCOUNT_REPLACEMENT_SCAM", "FAT_FINGER_MISTAKE", "DUPLICATE_PAYMENT", "CUSTOMER_RECALL"]:
    a = amt[amt.a == lab]
    print(f"    {lab:<26} n={len(a):>5,}  median ${a.x.median():>12,.2f}  p5 ${a.x.quantile(.05):>10,.2f}  p95 ${a.x.quantile(.95):>16,.2f}  whole-dollar {(a.x==a.x.round()).mean():.1%}")
# party types of scams
print("  Scam label x party_pair counts: ROMANCE_SCAM only in " + ",".join(sorted(amt[amt.a == 'ROMANCE_SCAM'].pp.unique()))
      + "; CEO_SCAM only in " + ",".join(sorted(amt[amt.a == 'CEO_SCAM'].pp.unique())))

# FAT_FINGER vs sender's own NORMAL history
print("\n  FAT_FINGER_MISTAKE scale vs the same ORDERING_ACCOUNT's median NORMAL amount (accounts with >= 3 NORMAL rows):")
ff = df(f"""WITH nrm AS (SELECT ORDERING_ACCOUNT acc, median(USD_AMOUNT) m, COUNT(*) k FROM {Q} WHERE ANOMALY_TYPE='NORMAL' GROUP BY 1 HAVING COUNT(*)>=3)
            SELECT t.ANOMALY_TYPE a, log10(t.USD_AMOUNT / n.m) d FROM {Q} t JOIN nrm n ON t.ORDERING_ACCOUNT=n.acc
            WHERE t.ANOMALY_TYPE IN ('FAT_FINGER_MISTAKE','NORMAL','DUPLICATE_PAYMENT') AND (t.ANOMALY_TYPE<>'NORMAL' OR hash(t.row_id)%50=0)""")
dff = ff[ff.a == "FAT_FINGER_MISTAKE"].d.values; dnm = ff[ff.a == "NORMAL"].d.values
print(f"    FAT_FINGER n={len(dff):,}; NORMAL reference sample n={len(dnm):,}")
bins = np.arange(-4, 6.01, 0.5)
hf, _ = np.histogram(dff, bins); hn, _ = np.histogram(dnm, bins)
print(f"    {'dex bin':>10}{'FF %':>8}{'NORMAL %':>10}")
for b, a1, a2 in zip(bins[:-1], hf / hf.sum(), hn / hn.sum()):
    print(f"    {b:>+5.1f}..{b+0.5:+.1f}{a1*100:>8.1f}{a2*100:>10.1f}")
ksff = stats.ks_2samp(dff, dnm)
print(f"    median dex FF {np.median(dff):+.2f} (x{10**np.median(dff):,.1f}) vs NORMAL {np.median(dnm):+.2f}; KS D={ksff.statistic:.3f}, p={ksff.pvalue:.3g}")
print(f"    share of FF with amount >= 10x own median: {np.mean(dff>=1):.1%} (NORMAL {np.mean(dnm>=1):.1%}); >= 100x: {np.mean(dff>=2):.1%} (NORMAL {np.mean(dnm>=2):.1%}); "
      f"<= 1/10: {np.mean(dff<=-1):.1%} (NORMAL {np.mean(dnm<=-1):.1%}); <= 1/100: {np.mean(dff<=-2):.1%} (NORMAL {np.mean(dnm<=-2):.1%})")
for b, a1, a2 in zip(bins[:-1], hf / hf.sum(), hn / hn.sum()):
    add("fatfinger_dex", dex_from=float(b), ff_share=float(a1), normal_share=float(a2))
add("fatfinger_summary", n_ff=len(dff), median_dex=float(np.median(dff)), ks_D=float(ksff.statistic),
    share_ge10x=float(np.mean(dff >= 1)), share_ge100x=float(np.mean(dff >= 2)), share_le_tenth=float(np.mean(dff <= -1)))

# DUPLICATE_PAYMENT: exact-amount same-account-pair partner
print("\n  DUPLICATE_PAYMENT: other rows with identical (ORDERING_ACCOUNT, BENEFICIARY_ACCOUNT, USD_AMOUNT)?")
keyed = df(f"""WITH g AS (SELECT ORDERING_ACCOUNT a, BENEFICIARY_ACCOUNT b, USD_AMOUNT x, COUNT(*) k FROM {Q} GROUP BY ALL)
  SELECT t.ANOMALY_TYPE lab, COUNT(*) n, COUNT(*) FILTER (WHERE g.k>1) with_twin FROM {Q} t
  JOIN g ON t.ORDERING_ACCOUNT=g.a AND t.BENEFICIARY_ACCOUNT=g.b AND t.USD_AMOUNT=g.x GROUP BY 1 ORDER BY n DESC""")
keyed["pct"] = keyed.with_twin / keyed.n
print(keyed.assign(pct=lambda d: (d.pct * 100).round(3)).to_string(index=False))
for _, r in keyed.iterrows(): add("dup_twin", label=r.lab, n=int(r.n), with_twin=int(r.with_twin))
tw = df(f"""WITH d AS (SELECT row_id,ORDERING_ACCOUNT a,BENEFICIARY_ACCOUNT b,USD_AMOUNT x,EPOCH_SECONDS e FROM {Q} WHERE ANOMALY_TYPE='DUPLICATE_PAYMENT'),
  j AS (SELECT d.row_id, t.ANOMALY_TYPE tl, t.EPOCH_SECONDS-d.e dt FROM d JOIN {Q} t ON t.ORDERING_ACCOUNT=d.a AND t.BENEFICIARY_ACCOUNT=d.b AND t.USD_AMOUNT=d.x AND t.row_id<>d.row_id)
  SELECT * FROM j""")
cl = df(f"""SELECT k, COUNT(*) clusters FROM (SELECT COUNT(*) k FROM {Q} WHERE ANOMALY_TYPE='DUPLICATE_PAYMENT'
            GROUP BY ORDERING_ACCOUNT, BENEFICIARY_ACCOUNT, USD_AMOUNT) GROUP BY 1 ORDER BY 1""")
print("    DUPLICATE_PAYMENT cluster sizes (rows sharing account pair + amount): " + ", ".join(f"size {int(r.k)}: {int(r.clusters)}" for r in cl.itertuples()))
for r in cl.itertuples(): add("dup_cluster_size", size=int(r.k), clusters=int(r.clusters))
if len(tw):
    print(f"    twins found for {tw.row_id.nunique()} of {int(keyed.set_index('lab').loc['DUPLICATE_PAYMENT','n'])} DUPLICATE_PAYMENT rows; twin labels: "
          f"{tw.tl.value_counts().to_dict()}; |time gap| quantiles (s) 25/50/75/95/max: {np.quantile(tw.dt.abs(), [.25,.5,.75,.95,1]).round(0).tolist()}")

# ── Export & charts ───────────────────────────────────────────────────────
hdr("Export CSV and charts (300 DPI)")
out = pd.DataFrame(BLOCKS); cols = ["block"] + [c for c in out.columns if c != "block"]
out[cols].to_csv(CSV_OUT, index=False)
print(f"  {CSV_OUT}: {len(out)} rows, blocks = {sorted(out.block.unique())}")
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8f98", "axes.labelcolor": "#2b2f36", "xtick.color": "#4a4f58", "ytick.color": "#4a4f58"})
INK, GREY = "#1c1f24", "#4a4f58"
PC = {"B2B": "#1b4f9c", "B2C": "#2a9d8f", "C2B": "#e08a1e", "C2C": "#9b5de5"}   # fixed pair order, validated below by contrast on white
# chart 1: distributions
fig, ax = plt.subplots(figsize=(10, 6))
bins = np.linspace(-1, 9, 201)
for pr in PAIRS:
    v = nm[nm.pp == pr].lx.values
    h, e = np.histogram(v, bins=bins, density=True)
    ax.plot((e[:-1] + e[1:]) / 2, h, color=PC[pr], lw=2, label=f"{pr} (n={len(v):,}; median \\${10**np.median(v):,.0f})")
    ax.axvline(np.median(v), color=PC[pr], lw=1, ls=":")
ax.set_xlabel("USD_AMOUNT (log10 scale; 3 = \\$1,000, 5 = \\$100,000)"); ax.set_ylabel("Density")
oe, be, ie = base_mult
ax.set_title(f"Each Business party multiplies the payment ~{10**((oe+be)/2):.1f}x: B2B median \\${shape['B2B']['median']:,.0f} "
             f"vs C2C \\${shape['C2C']['median']:,.0f} ({shape['B2B']['median']/shape['C2C']['median']:.0f}x)", loc="left", fontsize=11.5, fontweight="bold", color=INK)
ax.legend(frameon=False, loc="upper left")
fig.text(0.01, 0.01, f"NORMAL rows only (n={len(nm):,}). All four shapes ~log-normal (sd(log10) {min(sd_all):.2f}-{max(sd_all):.2f}); sender and receiver effects "
         f"x{10**oe:.1f} / x{10**be:.1f}, interaction {ie:+.2f} dex. Dotted = pair median.", fontsize=8, color=GREY)
fig.tight_layout(rect=(0, 0.03, 1, 1))
p1 = os.path.join(CH_DIR, "d2_amount_by_party_pair.png"); fig.savefig(p1, dpi=300); plt.close(fig); print("  saved", p1)
# chart 2: rounding evidence
fig, axs = plt.subplots(1, 2, figsize=(11, 5.2), gridspec_kw={"width_ratios": [1, 1.3]})
ax = axs[0]
vals = [w1 * 100, w0 * 100, 1.0]; labs = ["USD", "non-USD", "chance\n(2 decimals)"]
ax.bar(labs, vals, color=["#1b4f9c", "#b9bec7", "#d6d9de"], width=0.6)
for i, v in enumerate(vals): ax.text(i, v + 0.8, f"{v:.1f}%", ha="center", fontsize=10, color=INK)
ax.set_ylabel("Share of NORMAL payments that are whole-dollar (%)"); ax.set_title("USD amounts are round; others are not", loc="left", fontsize=10.5, fontweight="bold", color=INK)
ax = axs[1]
cs = [c for c in recon]
xs = np.arange(len(cs)); wdt = 0.27
ax.bar(xs - wdt, [recon[c]["true"] * 100 for c in cs], wdt, color="#1b4f9c", label="daily rate (reconstructed)")
ax.bar(xs, [recon[c]["const"] * 100 for c in cs], wdt, color="#8a9bb5", label="one constant rate")
ax.bar(xs + wdt, [recon[c]["placebo"] * 100 for c in cs], wdt, color="#d6d9de", label="placebo: another day's rate")
ax.set_xticks(xs); ax.set_xticklabels(cs); ax.set_ylabel("Rows that are a round local amount (%)")
ax.axhline(usd_round * 100, color="#d6453d", lw=1, ls="--")
ax.text(len(cs) - 0.45, usd_round * 100 + 0.3, f"USD baseline {usd_round:.1%}", color="#d6453d", fontsize=8, ha="right")
ax.set_ylim(0, 19)
ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=3, bbox_to_anchor=(0, 1.0))
ax.set_title("Non-USD amounts are round in local currency at a daily rate", loc="left", fontsize=10.5, fontweight="bold", color=INK)
fig.suptitle(f"USD amounts are whole-dollar {w1:.0%} of the time vs {w0:.1%} for other currencies; non-USD amounts snap to round local figures at a day-specific rate",
             x=0.01, ha="left", fontsize=11.5, fontweight="bold", color=INK, wrap=True)
fig.text(0.01, 0.01, "NORMAL rows; round = {1,2,2.5,3,4,5,6,7.5,8,10} x 10^k local units within one USD cent; rate = most repeated anchor amount per UTC day (>=3 repeats); rows >= $100.", fontsize=7.5, color=GREY)
fig.tight_layout(rect=(0, 0.03, 1, 0.92))
p2 = os.path.join(CH_DIR, "d2_rounding_evidence.png"); fig.savefig(p2, dpi=300); plt.close(fig); print("  saved", p2)
for f in (CSV_OUT, p1, p2): print(f"  exists: {os.path.exists(f)}  {os.path.getsize(f):,} bytes")
print("\nGATE 3 COMPLETE")
