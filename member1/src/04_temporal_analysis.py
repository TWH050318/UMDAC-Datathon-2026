"""
Gate 4 / Dashboard 3: Temporal Patterns
=======================================
Hypotheses (data/processed/clean_payments.parquet only; no external timezone tables):
  T1  Volume depends on UTC hour and day-of-week (profile shape, weekend drop).
  T2  Timing follows the ORDERING country's local clock: a per-country UTC offset (inferred from the
      data, minimising the local-weekend share) makes weekend share country-independent and gives one
      common local hour-of-day profile. Negative control: the beneficiary country's offset does not.
  T3  Corporate (B) vs consumer (C) senders have different schedules (weekend drop, hour clustering).
  T4  Weekly volume moves between discrete levels with unchanged composition.
  T5  No batch/minute/second spikes in timestamps.
  T6  Amount / routing type / anomaly labels vary with time?
Outputs: outputs/csv/d3_temporal_summary.csv, outputs/charts/d3_*.png
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
CSV_OUT = os.path.join(BASE, "outputs", "csv", "d3_temporal_summary.csv")
CH_DIR = os.path.join(BASE, "outputs", "charts")
os.makedirs(os.path.dirname(CSV_OUT), exist_ok=True); os.makedirs(CH_DIR, exist_ok=True)
con = duckdb.connect()
Q = f"read_parquet('{PARQ}')"
def hdr(t): print("\n" + "=" * 76 + f"\n  {t}\n" + "=" * 76)
BLOCKS = []
def add(block, **kw): BLOCKS.append({"block": block, **kw})
def cramers(ct):
    chi, p, dof, _ = stats.chi2_contingency(ct)
    return chi, p, dof, np.sqrt(chi / (ct.sum() * (min(ct.shape) - 1)))

d = con.execute(f"""SELECT EPOCH_SECONDS e, utc_dt, utc_hour h, utc_dow w, ORDERING_TYPE ot, party_pair pp,
        CURRENCY_CODE cur, TRANSACTION_TYPE_CODE tt, ANOMALY_TYPE a, USD_AMOUNT x, ordering_country oc, beneficiary_country bc
        FROM {Q}""").df()
# utc_hour / utc_dow are stored as TINYINT in the parquet: widen BEFORE any arithmetic (dow*24+hour overflows int8)
d["h"] = d.h.astype("int32"); d["w"] = d.w.astype("int32")
assert d.h.between(0, 23).all() and d.w.between(0, 6).all()
N = len(d); d["lx"] = np.log10(d.x)
print(f"Rows {N:,}; UTC {d.utc_dt.min()} -> {d.utc_dt.max()}")
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
# complete Mon-Sun weeks only for rate comparisons (the file starts Sun 30 Apr 11:22 and ends Mon 31 Jul 09:56)
t0 = pd.Timestamp("2023-05-01"); t1 = pd.Timestamp("2023-07-31")
full = d[(d.utc_dt >= t0) & (d.utc_dt < t1)]
print(f"Complete 13-week window (Mon 2023-05-01 .. Sun 2023-07-30): {len(full):,} rows ({len(full)/N:.2%}); excluded partial edge days: {N-len(full):,}")

# ── T1 UTC hour / dow ─────────────────────────────────────────────────────
hdr("T1  UTC hour-of-day and day-of-week volume")
hc = full.groupby("h").size()
print("  UTC hour share (%): " + " ".join(f"{h}:{hc[h]/len(full)*100:.1f}" for h in range(24)))
print(f"  Peak UTC hour {hc.idxmax()} ({hc.max()/len(full):.2%}); trough {hc.idxmin()} ({hc.min()/len(full):.2%}); peak/trough x{hc.max()/hc.min():.2f}")
chi, p = stats.chisquare(hc.values)
print(f"  Chi-square vs uniform hours: chi2={chi:,.0f}, p={p:.3g}")
dc = full.groupby("w").size()
nd = full.groupby("w").utc_dt.apply(lambda s: s.dt.normalize().nunique())
perday = dc / nd
print("  Mean daily volume by UTC dow: " + ", ".join(f"{DOW[i]}={perday[i]:,.0f}" for i in range(7)))
wk, we = perday[:5].mean(), perday[5:].mean()
print(f"  Weekend/weekday per-day ratio (UTC): {we/wk:.3f}; Sat/Mon {perday[5]/perday[0]:.3f}; Sun/Mon {perday[6]/perday[0]:.3f}; weekend share of rows {dc[5:].sum()/len(full):.2%}")
for i in range(7): add("utc_dow", dow=DOW[i], rows=int(dc[i]), mean_per_day=float(perday[i]))
for h in range(24): add("utc_hour", hour=h, rows=int(hc[h]), share=float(hc[h] / len(full)))
# weekend share by UTC hour
wsh = full.assign(we=full.w >= 5).groupby("h").we.mean()
print(f"  Weekend share of rows by UTC hour: min {wsh.min():.1%} (hour {wsh.idxmin()}), max {wsh.max():.1%} (hour {wsh.idxmax()})  [overall {len(full[full.w>=5])/len(full):.1%}]")

# ── T2 local clock ────────────────────────────────────────────────────────
hdr("T2  Local-clock hypothesis: infer a UTC offset per ordering country")
cn = full.groupby("oc").size()
big = cn[cn >= 50_000].index.tolist()
print(f"  Ordering countries with >= 50,000 rows: {len(big)} ({cn[big].sum()/len(full):.1%} of rows)")
def hw_matrix(sub):
    M = np.zeros(168)
    idx = (sub.w.values * 24 + sub.h.values)
    np.add.at(M, idx, 1)
    return M
fit = {}
print(f"  {'ctry':<5}{'n':>10}{'best off':>9}{'local-wkend %':>14}{'UTC-wkend %':>12}{'off-2..off+2 curve (%)':>38}")
for k in sorted(big, key=lambda c: -cn[c]):
    M = hw_matrix(full[full.oc == k]); tot = M.sum()
    shares = {o: np.roll(M, o).reshape(7, 24)[5:].sum() / tot for o in range(-12, 12)}
    best = min(shares, key=shares.get)
    cur = [shares[((best + j + 12) % 24) - 12] * 100 for j in (-2, -1, 0, 1, 2)]
    utc_w = M.reshape(7, 24)[5:].sum() / tot
    fit[k] = dict(off=best, local_wk=shares[best], utc_wk=utc_w, n=int(tot), curve=cur)
    print(f"  {k:<5}{int(tot):>10,}{best:>+9d}{shares[best]*100:>14.2f}{utc_w*100:>12.2f}   " + " ".join(f"{c:5.2f}" for c in cur))
    add("country_offset", country=k, n=int(tot), best_offset_h=best, local_weekend_share=float(shares[best]), utc_weekend_share=float(utc_w))
fdf = pd.DataFrame(fit).T
print(f"\n  Local-weekend share across countries: {fdf.local_wk.astype(float).min():.2%}-{fdf.local_wk.astype(float).max():.2%} "
      f"(sd {fdf.local_wk.astype(float).std():.4f}); UTC-weekend share: {fdf.utc_wk.astype(float).min():.2%}-{fdf.utc_wk.astype(float).max():.2%} (sd {fdf.utc_wk.astype(float).std():.4f})")
offs = {k: v["off"] for k, v in fit.items()}
sub = full[full.oc.isin(offs)].copy()
sub["off"] = sub.oc.map(offs)
sub["lidx"] = (sub.w * 24 + sub.h + sub.off) % 168
sub["lh"] = sub.lidx % 24; sub["lw"] = sub.lidx // 24
print(f"  Pooled local-time analysis uses {len(sub):,} rows ({len(sub)/len(full):.1%})")
lh = sub.groupby("lh").size(); lhp = lh / lh.sum()
print("  Pooled LOCAL hour share (%): " + " ".join(f"{h}:{lhp[h]*100:.1f}" for h in range(24)))
print(f"  Local-hour peak {lhp.idxmax()} ({lhp.max():.2%}), trough {lhp.idxmin()} ({lhp.min():.2%}); peak/trough x{lhp.max()/lhp.min():.1f} (UTC pooled-all: x{hc.max()/hc.min():.1f})")
for h in range(24): add("local_hour", hour=h, share=float(lhp[h]))
lw = sub.groupby("lw").size(); lwd = lw / sub.groupby("lw").utc_dt.apply(lambda s: s.dt.normalize().nunique() if False else 13)
lw_rel = lw / lw[0]
print("  Pooled LOCAL dow volume relative to Monday: " + ", ".join(f"{DOW[i]}={lw_rel[i]:.3f}" for i in range(7)))
lwk = lw[:5].mean(); lwe = lw[5:].mean()
print(f"  Local weekend/weekday per-day ratio: {lwe/lwk:.3f}; Sat/Sun = {lw[5]/lw[6]:.3f}; UTC pooled Sat/Sun = {dc[5]/dc[6]:.3f}")
for i in range(7): add("local_dow", dow=DOW[i], rel_to_monday=float(lw_rel[i]))
# similarity of each country's local hour profile to the pooled one
sims = []
for k in offs:
    s = sub[sub.oc == k]; pr = s.groupby("lh").size().reindex(range(24), fill_value=0); pr = pr / pr.sum()
    r = np.corrcoef(pr.values, lhp.values)[0, 1]; tv = 0.5 * np.abs(pr.values - lhp.values).sum()
    sims.append((k, r, tv))
print(f"  Country local-hour profile vs pooled: min Pearson r = {min(s[1] for s in sims):.3f} ({min(sims,key=lambda t:t[1])[0]}); max total-variation distance = {max(s[2] for s in sims):.3f}")
# same countries, same hours but UTC alignment: spread across countries
sims_utc = []
for k in offs:
    s = full[full.oc == k]; pr = s.groupby("h").size().reindex(range(24), fill_value=0); pr = pr / pr.sum()
    sims_utc.append(0.5 * np.abs(pr.values - hc.values / hc.sum()).sum())
print(f"  Same comparison on UTC hours: max total-variation distance to the UTC pooled profile = {max(sims_utc):.3f} (local alignment: {max(s[2] for s in sims):.3f})")
# independent cross-check of the offsets: circular alignment of each country's UTC hour profile to the pooled local profile
agree, rows_ = 0, []
for k in offs:
    pk = full[full.oc == k].groupby("h").size().reindex(range(24), fill_value=0).values.astype(float); pk /= pk.sum()
    cors = [np.corrcoef(np.roll(pk, o), lhp.values)[0, 1] for o in range(24)]
    o_prof = int(np.argmax(cors)); o_wk = offs[k] % 24
    diff = min((o_prof - o_wk) % 24, (o_wk - o_prof) % 24)
    rows_.append((k, o_wk, o_prof, diff, max(cors)))
    agree += diff <= 1
print(f"\n  Independent check (hour-profile alignment vs weekend-minimum offset): {agree}/{len(offs)} countries agree within 1 hour; "
      f"{sum(1 for r in rows_ if r[3]==0)}/{len(offs)} exactly; median best-fit r = {np.median([r[4] for r in rows_]):.3f}")
for r in rows_:
    if r[3] > 0: print(f"    {r[0]}: weekend offset {r[1]:+d} (mod 24) vs profile offset {r[2]:+d} (diff {r[3]}h, r={r[4]:.3f})")
add("offset_crosscheck", countries=len(offs), agree_within_1h=int(agree), exact=int(sum(1 for r in rows_ if r[3] == 0)))
# negative control: beneficiary offset
both = full[full.oc.isin(offs) & full.bc.isin(offs) & (full.oc != full.bc)].copy()
both["bo"] = both.bc.map(offs); both["oo"] = both.oc.map(offs)
def wk_share(df_, offcol):
    i = (df_.w.values * 24 + df_.h.values + df_[offcol].values) % 168
    return (i // 24 >= 5).mean()
so, sb = wk_share(both, "oo"), wk_share(both, "bo")
print(f"\n  Negative control (cross-border rows, both countries fitted, n={len(both):,}): weekend share in ORDERING local time {so:.2%}; "
      f"in BENEFICIARY local time {sb:.2%}; in UTC {(both.w>=5).mean():.2%}")
add("negative_control", n=len(both), weekend_share_ordering_local=float(so), weekend_share_beneficiary_local=float(sb), weekend_share_utc=float((both.w >= 5).mean()))
# local weekend share per-day factor and weekday uniformity
wkd_share = (lw[:5].sum() / lw.sum())
print(f"  Pooled local weekend share {1-wkd_share:.2%}; per-day weekend factor {lwe/lwk:.3f} of a weekday")
# do hour profiles differ between local weekday and local weekend?
ct = pd.crosstab(sub.lw >= 5, sub.lh).values
chi, p, dof, v = cramers(ct)
print(f"  Local hour profile weekday vs weekend: chi2={chi:,.0f}, df={dof}, p={p:.3g}, Cramer's V={v:.4f}")

# ── T3 B vs C ─────────────────────────────────────────────────────────────
hdr("T3  Corporate (B) vs Consumer (C) sender schedules")
ct = pd.crosstab(full.ot, full.h).values
chi, p, dof, v = cramers(ct)
print(f"  UTC hour x ordering type: chi2={chi:,.0f}, df={dof}, p={p:.3g}, Cramer's V={v:.4f}")
bshare = full.groupby("h").ot.apply(lambda s: (s == "B").mean())
print(f"  B share of rows by UTC hour: min {bshare.min():.2%} (h{bshare.idxmin()}), max {bshare.max():.2%} (h{bshare.idxmax()}); overall {(full.ot=='B').mean():.2%}")
ctd = pd.crosstab(full.ot, full.w).values
chi, p, dof, v = cramers(ctd)
print(f"  UTC dow x ordering type: chi2={chi:,.0f}, df={dof}, p={p:.3g}, Cramer's V={v:.4f}")
for t in ("B", "C"):
    s = sub[sub.ot == t]
    ws = (s.lw >= 5).mean()
    lhB = s.groupby("lh").size().reindex(range(24), fill_value=0); lhB = lhB / lhB.sum()
    nd_ = s.groupby("lw").size()
    fac = (nd_[5:].mean()) / nd_[:5].mean()
    print(f"  Sender {t}: n={len(s):,}; LOCAL weekend share {ws:.2%}; per-day weekend factor {fac:.3f}; Sat/Sun {nd_[5]/nd_[6]:.3f}; "
          f"local-hour peak {lhB.idxmax()} ({lhB.max():.2%})")
    add("type_schedule", sender_type=t, n=len(s), local_weekend_share=float(ws), weekend_factor=float(fac))
sB = sub[sub.ot == "B"]; sC = sub[sub.ot == "C"]
zt = (lambda a, b, n1, n2: (a - b) / np.sqrt(((a * n1 + b * n2) / (n1 + n2)) * (1 - (a * n1 + b * n2) / (n1 + n2)) * (1 / n1 + 1 / n2)))(
    (sB.lw >= 5).mean(), (sC.lw >= 5).mean(), len(sB), len(sC))
print(f"  B vs C local weekend share difference: {(sB.lw>=5).mean()-(sC.lw>=5).mean():+.4f} (z = {zt:+.1f})")
hB = sB.groupby("lh").size().reindex(range(24), fill_value=0); hC = sC.groupby("lh").size().reindex(range(24), fill_value=0)
chi, p, dof, v = cramers(np.vstack([hB.values, hC.values]))
print(f"  Local hour profile B vs C: chi2={chi:,.0f}, df={dof}, p={p:.3g}, Cramer's V={v:.4f}; max |share diff| = {np.abs(hB/hB.sum()-hC/hC.sum()).max():.4f}")
add("type_hour_test", cramers_v=float(v), max_abs_share_diff=float(np.abs(hB / hB.sum() - hC / hC.sum()).max()))
# party pair B2B vs C2C weekend
for pr in ["B2B", "B2C", "C2B", "C2C"]:
    s = sub[sub.pp == pr]; print(f"    {pr}: local weekend share {(s.lw>=5).mean():.2%} (n={len(s):,})")

# ── T4 weekly volume levels ───────────────────────────────────────────────
hdr("T4  Weekly volume levels (complete ISO weeks 18-30)")
fd = full.assign(day=full.utc_dt.dt.normalize(), wkn=full.utc_dt.dt.isocalendar().week.astype(int))
daily = fd.groupby(["wkn", "day"]).size().reset_index(name="n")
daily["dow"] = daily.day.dt.dayofweek
wl = daily[daily.dow < 5].groupby("wkn").n.agg(["mean", "std"])
wl["cv"] = wl["std"] / wl["mean"]
we_l = daily[daily.dow >= 5].groupby("wkn").n.mean()
wl["wkend"] = we_l; wl["ratio_we_wk"] = wl.wkend / wl["mean"]
print(wl.round(3).to_string())
order = wl["mean"].sort_values()
clusters = []
for w_, m in order.items():
    if clusters and m / np.mean([c[1] for c in clusters[-1]]) < 1.04:
        clusters[-1].append((w_, m))
    else:
        clusters.append([(w_, m)])
base = np.mean([m for _, m in clusters[0]])
print(f"\n  Levels (weeks within 4% grouped): {len(clusters)} clusters")
for c in clusters:
    ms = np.array([m for _, m in c]); weeks = [w_ for w_, _ in c]
    print(f"    level {ms.mean():>9,.0f}/weekday  x{ms.mean()/base:.3f} of lowest  weeks {weeks}  within-level spread {(ms.max()-ms.min())/ms.mean():.2%}")
    add("weekly_level", level_weekday_mean=float(ms.mean()), ratio_to_lowest=float(ms.mean() / base), weeks=str(weeks))
print(f"  Between-level spread: lowest {order.min():,.0f}, highest {order.max():,.0f} (x{order.max()/order.min():.2f}); weekend/weekday ratio by week: "
      f"{wl.ratio_we_wk.min():.3f}-{wl.ratio_we_wk.max():.3f}; within-week weekday CV median {wl.cv.median():.3f}")
# composition constant across weeks?
print("  Composition vs week (Cramer's V; ~0 = unchanged composition):")
topc = full.cur.value_counts().head(8).index
for nm_, col in [("ordering type", full.ot), ("party pair", full.pp), ("routing type", full.tt),
                 ("currency(top8+other)", full.cur.where(full.cur.isin(topc), "OTHER")),
                 ("ordering country(top10+other)", full.oc.where(full.oc.isin(full.oc.value_counts().head(10).index), "OTHER")),
                 ("UTC hour", full.h)]:
    wk_ = fd.wkn
    chi, p, dof, v = cramers(pd.crosstab(col.values, wk_.values).values)
    print(f"    {nm_:<30} chi2={chi:>10,.0f} df={dof:<4} p={p:.3g}  V={v:.4f}")
    add("composition_by_week", variable=nm_, cramers_v=float(v))
low = fd[fd.wkn.isin([w_ for w_, _ in clusters[0]])]; hi = fd[fd.wkn.isin([w_ for w_, _ in clusters[-1]])]
chi, p, dof, v = cramers(np.vstack([low.groupby("h").size().reindex(range(24), fill_value=0).values, hi.groupby("h").size().reindex(range(24), fill_value=0).values]))
print(f"  Hour profile lowest-level vs highest-level weeks: V={v:.4f}")
kwm = stats.kruskal(*[g.lx.values for _, g in fd[fd.a == "NORMAL"].groupby("wkn")])
print(f"  Amount by week (NORMAL, 13 groups): KW H={kwm.statistic:,.0f}, epsilon^2={(kwm.statistic-12)/(len(fd)-13):.5f}")

# ── T5 batch / minute / second structure ─────────────────────────────────
hdr("T5  Minute / second / batch spikes")
mm = (d.e // 60) % 60; ss = d.e % 60
for nm_, v_ in [("minute-of-hour", mm), ("second-of-minute", ss)]:
    c_ = np.bincount(v_, minlength=60); chi, p = stats.chisquare(c_)
    print(f"  {nm_}: chi2={chi:,.1f}, df=59, p={p:.3g}; max/min share {c_.max()/N:.4%}/{c_.min()/N:.4%} (uniform 1.6667%)")
    add("uniformity", variable=nm_, chi2=float(chi), p=float(p), max_share=float(c_.max() / N), min_share=float(c_.min() / N))
for m_, nm_ in [(3600, "top of hour"), (300, "5-min boundary"), (60, "whole minute")]:
    sh = (d.e % m_ == 0).mean(); ex = 1 / m_
    print(f"  Timestamps on a {nm_}: {sh:.4%} (expected {ex:.4%} if uniform; ratio {sh/ex:.2f})")
hh = (d.e // 3600) % 24
# per-second collision rate vs expected (Poisson) on busiest day
cps = d.groupby("e").size()
print(f"  Rows per distinct timestamp-second: max {cps.max()}, share of rows in seconds with >=2 payments {(cps[cps>=2].sum())/N:.2%}")

# ── T6 amount, routing, anomalies vs time ────────────────────────────────
hdr("T6  Amount, routing type and anomaly labels vs time")
nmv = sub[sub.a == "NORMAL"]
kw_h = stats.kruskal(*[g.lx.values for _, g in nmv.groupby("lh")])
kw_hu = stats.kruskal(*[g.lx.values for _, g in full[full.a == "NORMAL"].groupby("h")])
print(f"  log10(amount) by LOCAL hour: KW H={kw_h.statistic:,.0f}, epsilon^2={(kw_h.statistic-23)/(len(nmv)-24):.5f}; by UTC hour: H={kw_hu.statistic:,.0f}, epsilon^2={(kw_hu.statistic-23)/(len(full[full.a=='NORMAL'])-24):.5f}")
medh = full[full.a == "NORMAL"].groupby("h").x.median()
print(f"  Median NORMAL amount by UTC hour: min ${medh.min():,.0f} (h{medh.idxmin()}) max ${medh.max():,.0f} (h{medh.idxmax()}); ratio x{medh.max()/medh.min():.2f}")
# is the UTC-hour effect a country-mix effect? within US only
us = full[(full.oc == "US") & (full.a == "NORMAL")]
kw_us = stats.kruskal(*[g.lx.values for _, g in us.groupby("h")])
print(f"  Within ordering_country=US (n={len(us):,}): amount by UTC hour KW epsilon^2={(kw_us.statistic-23)/(len(us)-24):.5f}")
add("amount_time", test="KW local hour", epsilon2=float((kw_h.statistic - 23) / (len(nmv) - 24)))
add("amount_time", test="KW UTC hour", epsilon2=float((kw_hu.statistic - 23) / (len(full[full.a == 'NORMAL']) - 24)))
add("amount_time", test="KW UTC hour within US", epsilon2=float((kw_us.statistic - 23) / (len(us) - 24)))
for t in ("B", "C"):
    a_ = nmv[(nmv.ot == t) & (nmv.lw >= 5)].lx.values; b_ = nmv[(nmv.ot == t) & (nmv.lw < 5)].lx.values
    u = stats.mannwhitneyu(a_, b_)
    print(f"  Sender {t}: median amount weekend ${10**np.median(a_):,.0f} vs weekday ${10**np.median(b_):,.0f}; MWU p={u.pvalue:.3g}, rank-biserial {2*u.statistic/(len(a_)*len(b_))-1:+.4f}")
chi, p, dof, v = cramers(pd.crosstab(full.tt, full.h).values)
print(f"  Routing type x UTC hour: V={v:.4f} (p={p:.3g}); routing type x week: see composition; Direct share by local weekend: "
      f"{(sub[sub.lw>=5].tt=='Direct').mean():.2%} vs weekday {(sub[sub.lw<5].tt=='Direct').mean():.2%}")
print("  Anomaly label timing (local time, fitted countries): weekend share and 6-hour block distribution vs NORMAL")
subn = sub[sub.a == "NORMAL"]
blk = lambda x: (x // 6)
nb = blk(subn.lh).value_counts(normalize=True).sort_index()
for lab in ["ROMANCE_SCAM", "CEO_SCAM", "ACCOUNT_REPLACEMENT_SCAM", "FAT_FINGER_MISTAKE", "DUPLICATE_PAYMENT", "CUSTOMER_RECALL"]:
    s = sub[sub.a == lab]
    if len(s) < 30: continue
    ob = np.bincount(blk(s.lh), minlength=4)
    # reference matched on sender type (B/C differ slightly in hour profile): expected = sum_t share_t * NORMAL block dist of type t
    exp_b = np.zeros(4)
    for t_, c_ in s.ot.value_counts().items():
        exp_b += c_ * blk(subn[subn.ot == t_].lh).value_counts(normalize=True).reindex(range(4), fill_value=0).values
    chi, p = stats.chisquare(ob, exp_b * (len(s) / exp_b.sum()))
    wkp = stats.binomtest(int((s.lw >= 5).sum()), len(s), (subn.lw >= 5).mean()).pvalue
    print(f"    {lab:<26} n={len(s):>5,}  weekend {(s.lw>=5).mean():.1%} (NORMAL {(subn.lw>=5).mean():.1%}, p={wkp:.2g}); 6h-block chi2={chi:.1f} p={p:.2g}")
    print(f"      6h blocks (00-05/06-11/12-17/18-23) observed % {np.round(ob/ob.sum()*100,1).tolist()} vs sender-type-matched NORMAL % {np.round(exp_b/exp_b.sum()*100,1).tolist()}")
    add("anomaly_timing", label=lab, n=len(s), weekend_share=float((s.lw >= 5).mean()), weekend_p=float(wkp), block_p=float(p))

# ── Export & charts ──────────────────────────────────────────────────────
hdr("Export CSV and charts (300 DPI)")
out = pd.DataFrame(BLOCKS); out[["block"] + [c for c in out.columns if c != "block"]].to_csv(CSV_OUT, index=False)
print(f"  {CSV_OUT}: {len(out)} rows; blocks {sorted(out.block.unique())}")
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8f98", "axes.labelcolor": "#2b2f36", "xtick.color": "#4a4f58", "ytick.color": "#4a4f58"})
INK, GREY, BLUE, ORG = "#1c1f24", "#4a4f58", "#1b4f9c", "#d6762e"
# chart 1
fig, axs = plt.subplots(1, 2, figsize=(12, 5.4), gridspec_kw={"width_ratios": [1.25, 1]})
ks = [k for k in sorted(offs, key=lambda c: -fit[c]["n"])][:10]
x = np.arange(len(ks)); wd = 0.38
ax = axs[0]
ax.bar(x - wd / 2, [fit[k]["utc_wk"] * 100 for k in ks], wd, color="#b9bec7", label="weekend share in UTC")
ax.bar(x + wd / 2, [fit[k]["local_wk"] * 100 for k in ks], wd, color=BLUE, label="weekend share in sender's local time")
ax.axhline(2 / 7 * 100, color="#d6453d", lw=1, ls="--"); ax.text(len(ks) - 0.5, 2 / 7 * 100 + 0.4, "2/7 of days = 28.6% if no weekend effect", color="#d6453d", fontsize=7.5, ha="right")
ax.set_xticks(x); ax.set_xticklabels([f"{k}\n({offs[k]:+d}h)" for k in ks], fontsize=8)
ax.set_ylabel("Share of payments on Sat/Sun (%)"); ax.set_ylim(0, 32); ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, 0.9))
ax.set_title("Weekend share is the same in every country once measured in local time", loc="left", fontsize=10, fontweight="bold", color=INK)
ax = axs[1]
ax.bar(range(24), lhp.values * 100, color=BLUE, width=0.8)
ax.set_xlabel("Sender's local hour of day"); ax.set_ylabel("Share of payments (%)")
ax.set_title(f"Common local profile: peak {lhp.idxmax():02d}:00 ({lhp.max():.1%}),\ntrough {lhp.idxmin():02d}:00 ({lhp.min():.1%})", loc="left", fontsize=10, fontweight="bold", color=INK)
fig.suptitle(f"Payments follow the sender's clock: local weekend share {fdf.local_wk.astype(float).min():.1%}-{fdf.local_wk.astype(float).max():.1%} in every country vs "
             f"{fdf.utc_wk.astype(float).min():.1%}-{fdf.utc_wk.astype(float).max():.1%} in UTC", x=0.01, ha="left", fontsize=11.5, fontweight="bold", color=INK)
fig.text(0.01, 0.01, f"n = {len(sub):,} payments from {len(offs)} ordering countries (>=50k rows each), complete weeks 1 May - 30 Jul 2023. Offset per country inferred from the data (minimum local-weekend share).",
         fontsize=7.5, color=GREY)
fig.tight_layout(rect=(0, 0.03, 1, 0.93))
p1 = os.path.join(CH_DIR, "d3_local_time_structure.png"); fig.savefig(p1, dpi=300); plt.close(fig); print("  saved", p1)
# chart 2
fig, ax = plt.subplots(figsize=(11, 5.4))
dd = daily.sort_values("day")
ax.bar(dd.day, dd.n / 1000, color=[("#b9bec7" if w_ >= 5 else BLUE) for w_ in dd.dow], width=0.85)
for c in clusters:
    ms = np.mean([m for _, m in c])
for wk_n, row in wl.iterrows():
    mon = pd.Timestamp.fromisocalendar(2023, int(wk_n), 1)
    ax.hlines(row["mean"] / 1000, mon - pd.Timedelta(hours=12), mon + pd.Timedelta(days=4.5), color=ORG, lw=2)
    ax.text(mon + pd.Timedelta(days=2), row["mean"] / 1000 + 4, f"{row['mean']/base:.1f}x", ha="center", fontsize=7.5, color=INK)
ax.set_ylabel("Payments per day (thousands)"); ax.set_xlabel("UTC date (blue = Mon-Fri, grey = Sat/Sun; orange = weekday mean)")
ax.set_title(f"Weekly volume steps between {len(clusters)} levels ({order.min()/1000:.0f}k to {order.max()/1000:.0f}k per weekday, x{order.max()/order.min():.1f}); "
             f"weeks of equal level agree within {max((max(m for _,m in c)-min(m for _,m in c))/np.mean([m for _,m in c]) for c in clusters if len(c)>1):.1%}", loc="left", fontsize=10.5, fontweight="bold", color=INK)
fig.text(0.01, 0.01, f"n = {len(full):,} payments, complete weeks. Labels show weekday mean relative to the lowest level. Composition (party pair, currency, country, routing type) is unchanged across weeks (Cramer's V < 0.01).",
         fontsize=7.5, color=GREY)
fig.tight_layout(rect=(0, 0.03, 1, 1))
p2 = os.path.join(CH_DIR, "d3_weekly_volume_levels.png"); fig.savefig(p2, dpi=300); plt.close(fig); print("  saved", p2)
for f in (CSV_OUT, p1, p2): print(f"  exists: {os.path.exists(f)}  {os.path.getsize(f):,} bytes")
print("\nGATE 4 COMPLETE")
