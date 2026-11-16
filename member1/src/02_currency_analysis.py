"""
Gate 2 / Dashboard 1: Currency Patterns
=======================================
Hypotheses (all tested on data/processed/clean_payments.parquet only; no external tables):
  H1  CURRENCY_CODE frequency is not uniform: concentrated / Zipf-like tiers.
  H2  Currency mix differs by party_pair (chi-square, Cramer's V, per-currency enrichment).
  H3  CURRENCY_CODE is the ordering-country's home currency (home currency is DERIVED as the
      modal currency per ordering_country in this data) with a EUR/USD hub component;
      the share depends on CURRENCY_CONVERSION_COUNT == 0 vs > 0.
  H4  Median USD_AMOUNT differs across currencies (Kruskal-Wallis): normal rows first, then all rows;
      confound checks stratified by party_pair and conversion status.
Outputs: outputs/csv/d1_currency_summary.csv, outputs/charts/d1_*.png
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
CSV_OUT = os.path.join(BASE, "outputs", "csv", "d1_currency_summary.csv")
CH_DIR = os.path.join(BASE, "outputs", "charts")
os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True)
os.makedirs(CH_DIR, exist_ok=True)

MIN_N = 1000        # minimum rows for a currency/country to enter tests
con = duckdb.connect()
Q = f"read_parquet('{PARQ}')"
def df(sql): return con.execute(sql).df()
def hdr(t): print("\n" + "=" * 76 + f"\n  {t}\n" + "=" * 76)

N = con.execute(f"SELECT COUNT(*) FROM {Q}").fetchone()[0]
print(f"Rows: {N:,}")
print("Verified parquet columns used:", [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {Q}").fetchall()][:0] or "see schema in Gate 1")

# ── H1: frequency distribution ─────────────────────────────────────────────
hdr("H1  Currency frequency distribution")
freq = df(f"SELECT CURRENCY_CODE c, COUNT(*) n FROM {Q} GROUP BY 1 ORDER BY n DESC")
freq["share"] = freq.n / N
freq["rank"] = np.arange(1, len(freq) + 1)
K = len(freq)
print(f"Distinct currencies: {K}")
for k in (1, 2, 5, 10, 20):
    print(f"  top-{k:<2} share: {freq.share.head(k).sum():.2%}")
hhi = (freq.share ** 2).sum()
print(f"  HHI = {hhi:.4f}  (uniform over {K} would be {1/K:.4f}; effective #currencies = {1/hhi:.1f})")
chi_u, p_u = stats.chisquare(freq.n.values)
print(f"  Chi-square vs uniform: chi2 = {chi_u:,.0f}, df = {K-1}, p = {p_u:.3g}")
# Zipf: log10(freq) = a + b*log10(rank), all currencies and head (top 20)
def zipf(sub):
    r = stats.linregress(np.log10(sub["rank"]), np.log10(sub.n))
    return r.slope, r.rvalue ** 2
sl_all, r2_all = zipf(freq)
sl_20, r2_20 = zipf(freq.head(20))
print(f"  Zipf log-log slope all {K}: {sl_all:.3f} (R2 {r2_all:.3f}); top-20: {sl_20:.3f} (R2 {r2_20:.3f})")
# log-linear (exponential) alternative on rank
r_exp = stats.linregress(freq["rank"], np.log10(freq.n))
print(f"  Exponential fit log10(n) ~ rank: slope {r_exp.slope:.4f}, R2 {r_exp.rvalue**2:.3f}")
print("  Top 12:")
for _, r in freq.head(12).iterrows():
    print(f"    {r.c}  {int(r.n):>10,}  {r.share:.2%}")
# tier boundaries: gaps in share (ratio to next)
freq["ratio_next"] = freq.n / freq.n.shift(-1)

# ── H2: party_pair x currency ──────────────────────────────────────────────
hdr("H2  Currency mix by party_pair")
top10 = list(freq.c.head(10))
pp = df(f"""SELECT party_pair, CASE WHEN CURRENCY_CODE IN ({','.join("'"+c+"'" for c in top10)})
                 THEN CURRENCY_CODE ELSE 'OTHER' END c, COUNT(*) n FROM {Q} GROUP BY 1,2""")
ct = pp.pivot(index="party_pair", columns="c", values="n").fillna(0)
chi, p, dof, _ = stats.chi2_contingency(ct.values)
cv = np.sqrt(chi / (ct.values.sum() * (min(ct.shape) - 1)))
print(f"  party_pair x (top10 + OTHER): chi2 = {chi:,.0f}, df = {dof}, p = {p:.3g}, Cramer's V = {cv:.4f}")
pair_n = df(f"SELECT party_pair, COUNT(*) n FROM {Q} GROUP BY 1").set_index("party_pair").n
full = df(f"SELECT party_pair, CURRENCY_CODE c, COUNT(*) n FROM {Q} GROUP BY 1,2")
shares = full.pivot(index="c", columns="party_pair", values="n").fillna(0)
share_pct = shares / pair_n
overall = freq.set_index("c").share
enrich = share_pct.div(overall, axis=0)          # share in pair / overall share
print("  Share of each pair's traffic, top 8 currencies (%):")
print((share_pct.loc[freq.c.head(8)] * 100).round(2).to_string())
# two-proportion z-tests for each pair vs rest, top 8 currencies
print("  Enrichment (pair share / overall share) with two-proportion z-test vs the other three pairs, |z|>5 only:")
rows = []
for c in freq.c.head(15):
    for pr in pair_n.index:
        k1 = shares.loc[c, pr]; n1 = pair_n[pr]
        k2 = shares.loc[c].sum() - k1; n2 = N - n1
        p1, p2 = k1 / n1, k2 / n2
        pp_ = (k1 + k2) / (n1 + n2)
        z = (p1 - p2) / np.sqrt(pp_ * (1 - pp_) * (1 / n1 + 1 / n2))
        rows.append((c, pr, p1, p2, p1 / p2, z))
        if abs(z) > 5:
            print(f"    {c} {pr}: share {p1:.2%} vs others {p2:.2%}  ratio {p1/p2:.3f}  z = {z:+.1f}")
exclusive = [(c, pr) for c in shares.index for pr in pair_n.index if shares.loc[c, pr] == 0 and shares.loc[c].sum() >= MIN_N]
print(f"  Currencies (n >= {MIN_N}) that never appear in some party_pair: {exclusive if exclusive else 'none'}")

# ── H3: currency vs ordering/beneficiary country and hubs ──────────────────
hdr("H3  Currency vs country of ordering / beneficiary bank, hubs and conversion count")
for side in ("ordering", "beneficiary"):
    col = f"{side}_country"
    modal = df(f"""WITH c AS (SELECT {col} ctry, CURRENCY_CODE cur, COUNT(*) n FROM {Q} GROUP BY 1,2),
        t AS (SELECT ctry, SUM(n) tot FROM c GROUP BY 1)
        SELECT c.ctry, c.cur, c.n, t.tot FROM c JOIN t USING(ctry)
        QUALIFY ROW_NUMBER() OVER (PARTITION BY c.ctry ORDER BY c.n DESC) = 1""")
    modal["pct"] = modal.n / modal.tot
    big = modal[modal.tot >= MIN_N]
    wm = (big.n.sum() / big.tot.sum())
    print(f"\n  {side}_country -> modal currency: {len(big)} countries with n>={MIN_N}; "
          f"row-weighted modal-currency match {wm:.2%}")
    print(f"    countries whose modal currency covers >=50% of their rows: {(big.pct>=0.5).sum()} / {len(big)}")
    print(big.sort_values("tot", ascending=False).head(15)[["ctry", "cur", "pct", "tot"]]
          .assign(pct=lambda d: (d.pct * 100).round(1)).to_string(index=False))
    modal.to_csv(os.path.join(BASE, "outputs", "csv", f"d1_{side}_country_modal_currency.csv"), index=False)
    if side == "ordering":
        ord_modal = modal.set_index("ctry").cur.to_dict()
    else:
        ben_modal = modal.set_index("ctry").cur.to_dict()

con.register("ordmap", pd.DataFrame({"ctry": list(ord_modal), "home": list(ord_modal.values())}))
con.register("benmap", pd.DataFrame({"ctry": list(ben_modal), "home": list(ben_modal.values())}))
base = df(f"""SELECT q.CURRENCY_CODE c, (q.CURRENCY_CONVERSION_COUNT=0) conv0,
       (q.CURRENCY_CODE = o.home) is_ord_home, (q.CURRENCY_CODE = b.home) is_ben_home,
       (q.CURRENCY_CODE IN ('USD','EUR')) is_hub, q.CURRENCY_CONVERSION_COUNT cc,
       q.ordering_country oc, q.beneficiary_country bc
       FROM {Q} q JOIN ordmap o ON q.ordering_country=o.ctry JOIN benmap b ON q.beneficiary_country=b.ctry""")
assert len(base) == N
base["cat"] = np.select(
    [base.is_ord_home & base.is_ben_home, base.is_ord_home, base.is_ben_home, base.is_hub],
    ["ordering+beneficiary home", "ordering home only", "beneficiary home only", "USD/EUR hub (neither home)"],
    default="other")
print("\n  Currency category (mutually exclusive, priority in listed order) by conversion status:")
tab = pd.crosstab(base.cat, np.where(base.conv0, "conv==0", "conv>0"))
tab_pct = tab / tab.sum()
out = tab.join(tab_pct.add_suffix(" %").mul(100).round(2))
print(out.to_string())
tot = pd.crosstab(base.cat, "all")["all"]
print("  All rows: " + "; ".join(f"{k}={v/N:.2%}" for k, v in tot.items()))
# test: is_ord_home vs conv0
t2 = pd.crosstab(base.is_ord_home, base.conv0)
chi2, p2, _, _ = stats.chi2_contingency(t2.values)
r_home0 = t2.loc[True, True] / t2[True].sum(); r_home1 = t2.loc[True, False] / t2[False].sum()
phi = np.sqrt(chi2 / N)
print(f"\n  P(currency == ordering home | conv==0) = {r_home0:.2%} ; | conv>0 = {r_home1:.2%}; "
      f"chi2 = {chi2:,.0f}, p = {p2:.3g}, phi = {phi:.3f}")
t3 = pd.crosstab(base.is_ben_home, base.conv0)
chi3, p3, _, _ = stats.chi2_contingency(t3.values)
print(f"  P(currency == beneficiary home | conv==0) = {t3.loc[True,True]/t3[True].sum():.2%} ; | conv>0 = "
      f"{t3.loc[True,False]/t3[False].sum():.2%}; chi2 = {chi3:,.0f}, p = {p3:.3g}")
# mean conversion count by category
print("\n  Mean CURRENCY_CONVERSION_COUNT by category:")
print(base.groupby("cat").cc.agg(["mean", "median", "count"]).round(3).to_string())
kw_cc = stats.kruskal(*[g.cc.values for _, g in base.groupby("cat")])
print(f"  Kruskal-Wallis conversion count across categories: H = {kw_cc.statistic:,.0f}, p = {kw_cc.pvalue:.3g}")
# Hub share by conv
print(f"\n  EUR share: conv==0 {(base[base.conv0].c=='EUR').mean():.2%}; conv>0 {(base[~base.conv0].c=='EUR').mean():.2%}")
print(f"  USD share: conv==0 {(base[base.conv0].c=='USD').mean():.2%}; conv>0 {(base[~base.conv0].c=='USD').mean():.2%}")
# Is it conv==0 structurally = same currency for the whole path? check conv0 & currency != ordering home
print(f"  conv==0 rows where currency != ordering-home currency: {int(((base.conv0)&(~base.is_ord_home)).sum()):,} "
      f"({((base.conv0)&(~base.is_ord_home)).sum()/base.conv0.sum():.2%} of conv==0)")
# Eurozone check: ordering countries whose modal currency is EUR
eur_cty = df(f"""SELECT ordering_country oc, COUNT(*) n, AVG((CURRENCY_CODE='EUR')::INT) eur FROM {Q}
                 GROUP BY 1 HAVING COUNT(*)>={MIN_N} AND AVG((CURRENCY_CODE='EUR')::INT) >= 0.5 ORDER BY n DESC""")
print(f"  Ordering countries with EUR >= 50% of rows: {len(eur_cty)} -> {list(eur_cty.oc)}")

# ── H4: amount by currency ─────────────────────────────────────────────────
hdr("H4  USD_AMOUNT by currency (Kruskal-Wallis)")
amt = df(f"SELECT CURRENCY_CODE c, party_pair pp, (CURRENCY_CONVERSION_COUNT=0) conv0, "
         f"ANOMALY_TYPE a, USD_AMOUNT x FROM {Q}")
amt["lx"] = np.log10(amt.x)
cnt = amt.c.value_counts()
elig = list(cnt[cnt >= MIN_N].index)
print(f"  Currencies with n >= {MIN_N}: {len(elig)} of {K}")

def kw(sub, label, by="c", min_n=MIN_N):
    vc = sub[by].value_counts()
    keep = vc[vc >= min_n].index
    s = sub[sub[by].isin(keep)]
    groups = [g.lx.values for _, g in s.groupby(by)]
    H, p = stats.kruskal(*groups)
    k, n = len(groups), len(s)
    eps2 = (H - k + 1) / (n - k)
    print(f"  {label:<46} k={k:<3} n={n:>10,}  H={H:>12,.0f}  p={p:.3g}  epsilon^2={eps2:.4f}")
    return H, p, eps2, k, n

normal = amt[amt.a == "NORMAL"]
kw_n = kw(normal, "NORMAL rows only")
kw_a = kw(amt, "ALL rows (anomalies included)")
kw_ff = kw(amt[amt.a != "FAT_FINGER_MISTAKE"], "all excl. FAT_FINGER_MISTAKE")
print("  Confound check - within party_pair (NORMAL):")
kw_pp = {}
for pr, g in normal.groupby("pp"):
    kw_pp[pr] = kw(g, f"  party_pair={pr}", min_n=MIN_N)
print("  Confound check - within conversion status (NORMAL):")
for flag, g in normal.groupby("conv0"):
    kw(g, f"  conv0={flag}")
print("  Control: does party_pair alone explain amount? (NORMAL) ")
kw(normal.assign(pp2=normal.pp), "  party_pair as grouping", by="pp2", min_n=1)

# median table
med = normal.groupby("c").lx.agg(n="count", median_log="median").query("n >= @MIN_N")
med["median_usd"] = 10 ** med.median_log
med_all = amt.groupby("c").x.median().rename("median_usd_all")
usd_med = med.loc["USD", "median_usd"]
med["ratio_vs_USD"] = med.median_usd / usd_med
print(f"\n  NORMAL median USD_AMOUNT: USD = {usd_med:,.2f}")
top_c = list(freq.c.head(15))
print(f"  {'cur':<5}{'n':>10}{'median':>12}{'x USD':>8}{'MWU vs USD: p':>16}{'rank-biserial':>15}")
usd_vals = normal[normal.c == "USD"].lx.values
mwu_rows = {}
for c in top_c:
    if c == "USD":
        continue
    v = normal[normal.c == c].lx.values
    u, pv = stats.mannwhitneyu(v, usd_vals, alternative="two-sided")
    rb = 2 * u / (len(v) * len(usd_vals)) - 1
    mwu_rows[c] = (pv, rb)
    print(f"  {c:<5}{len(v):>10,}{10**np.median(v):>12,.2f}{10**np.median(v)/usd_med:>8.3f}{pv:>16.3g}{rb:>15.3f}")
spread = med.median_usd.max() / med.median_usd.min()
print(f"\n  Across {len(med)} eligible currencies: lowest median {med.median_usd.min():,.2f} ({med.median_usd.idxmin()}), "
      f"highest {med.median_usd.max():,.2f} ({med.median_usd.idxmax()}), spread x{spread:,.1f}")
print("  Lowest 6 / highest 6 medians (NORMAL):")
srt = med.sort_values("median_usd")
print(srt.head(6)[["n", "median_usd"]].round(2).to_string())
print(srt.tail(6)[["n", "median_usd"]].round(2).to_string())
# Effect of FAT_FINGER on medians: compare per-currency medians with/without
medall_inc = amt.groupby("c").x.median()
delta = ((medall_inc / (10 ** normal.groupby("c").lx.median())) - 1).loc[med.index].abs()
print(f"  Max |median shift| per currency when anomalies are included: {delta.max():.2%} ({delta.idxmax()}); "
      f"median shift {delta.median():.4%}")

# ── Summary CSV ────────────────────────────────────────────────────────────
hdr("Export summary CSV")
summ = freq[["c", "n", "share", "rank"]].rename(columns={"c": "CURRENCY_CODE"}).set_index("CURRENCY_CODE")
for pr in pair_n.index:
    summ[f"share_in_{pr}"] = share_pct[pr]
    summ[f"enrich_{pr}"] = enrich[pr]
conv_tab = base.groupby("c").agg(share_conv0=("conv0", "mean"), pct_ordering_home=("is_ord_home", "mean"),
                                 pct_beneficiary_home=("is_ben_home", "mean"), mean_conv_count=("cc", "mean"))
summ = summ.join(conv_tab)
summ = summ.join(med[["n", "median_usd", "ratio_vs_USD"]].rename(columns={"n": "n_normal_ge_min", "median_usd": "median_usd_normal"}))
summ = summ.join(med_all)
summ["mwu_p_vs_USD"] = pd.Series({c: v[0] for c, v in mwu_rows.items()})
summ["mwu_rank_biserial_vs_USD"] = pd.Series({c: v[1] for c, v in mwu_rows.items()})
summ.reset_index().to_csv(CSV_OUT, index=False)
print(f"  Wrote {CSV_OUT}  ({len(summ)} rows x {summ.shape[1]+1} cols)")

# ── Charts ─────────────────────────────────────────────────────────────────
hdr("Charts (300 DPI)")
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8f98", "axes.labelcolor": "#2b2f36", "xtick.color": "#4a4f58",
                     "ytick.color": "#4a4f58", "figure.dpi": 100})
BLUE, GREY, INK = "#2a6fdb", "#b9bec7", "#1c1f24"

# Chart 1: top-15 share
fig, ax = plt.subplots(figsize=(9, 6))
t = freq.head(15).iloc[::-1]
colors = [BLUE if c in ("EUR", "USD") else GREY for c in t.c]
ax.barh(t.c, t.share * 100, color=colors, height=0.7)
for y, (s_, n_) in enumerate(zip(t.share, t.n)):
    ax.text(s_ * 100 + 0.4, y, f"{s_:.1%}", va="center", fontsize=9, color=INK)
ax.set_xlabel("Share of all payments (%)")
ax.set_xlim(0, t.share.max() * 100 * 1.15)
ax.axvline(100 / K, color="#d6453d", lw=1, ls="--")
ax.text(100 / K + 0.4, len(t) - 0.6, f"dashed = uniform share ({100/K:.2f}% each)", color="#d6453d", fontsize=8)
ttl = (f"EUR and USD carry {freq.share.head(2).sum():.0%} of payments; top-5 = {freq.share.head(5).sum():.0%} "
       f"of {K} currencies")
ax.set_title(ttl, loc="left", fontsize=13, fontweight="bold", color=INK)
fig.text(0.01, 0.01, f"n = {N:,} payments (UTC Apr 30 - Jul 31 2023). Chi-square vs uniform: p < 1e-300. "
         f"Exponential rank fit R2 = {r_exp.rvalue**2:.2f}.", fontsize=8, color="#4a4f58")
fig.tight_layout(rect=(0, 0.03, 1, 1))
p1 = os.path.join(CH_DIR, "d1_currency_frequency.png")
fig.savefig(p1, dpi=300); plt.close(fig); print("  saved", p1)

# Chart 2: median NORMAL amount by currency, top-15
fig, ax = plt.subplots(figsize=(9, 6))
t = med.loc[[c for c in top_c if c in med.index]].sort_values("median_usd")
cols = [BLUE if c == "USD" else GREY for c in t.index]
ax.barh(t.index, t.median_usd, color=cols, height=0.7)
ax.set_xscale("log")
for y, (c, r) in enumerate(t.iterrows()):
    ax.text(r.median_usd * 1.12, y, f"\\${r.median_usd:,.0f}  (n={int(r.n):,})", va="center", fontsize=8, color=INK,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.0))
ax.axvline(usd_med, color=BLUE, lw=1, ls="--")
ax.set_xlim(t.median_usd.min() * 0.5, t.median_usd.max() * 6)
ax.set_xlabel("Median USD_AMOUNT, normal payments (log scale)")
ax.set_title(f"Median payment spans \\${med.median_usd.min():,.0f} ({med.median_usd.idxmin()}) to "
             f"\\${med.median_usd.max():,.0f} ({med.median_usd.idxmax()}) across {len(med)} currencies "
             f"(x{spread:,.0f}); CNY is {1/med.loc['CNY','ratio_vs_USD']:.1f}x and UAH {1/med.loc['UAH','ratio_vs_USD']:.0f}x below USD",
             loc="left", fontsize=10.5, fontweight="bold", color=INK, wrap=True)
fig.text(0.01, 0.01, f"Top-15 currencies by volume, NORMAL rows only; KW epsilon^2 = {kw_n[2]:.3f} across {kw_n[3]} currencies "
         f"(n >= {MIN_N}). Dashed = USD median.", fontsize=8, color="#4a4f58")
fig.tight_layout(rect=(0, 0.03, 1, 1))
p2 = os.path.join(CH_DIR, "d1_currency_median_amount.png")
fig.savefig(p2, dpi=300); plt.close(fig); print("  saved", p2)

for f in (CSV_OUT, p1, p2):
    print(f"  exists: {os.path.exists(f)}  {os.path.getsize(f):,} bytes  {f}")
print("\nGATE 2 COMPLETE")
