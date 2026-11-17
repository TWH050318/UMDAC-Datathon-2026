"""
Gate 1: Data Ingestion, Audit & Shared Pipeline
================================================
UMDAC Datathon 2026 - Swift Payments Reverse-Engineering Challenge (Member 1)

Design rules (SKILL.md):
  * Ingest EVERYTHING as VARCHAR first, then TRY_CAST and COUNT every failed cast
    -> proves zero silent coercion (any failure aborts the run).
  * ID / BIC columns stay VARCHAR (leading zeros preserved, byte-checked vs raw).
  * Never drop rows. Anomalies/duplicates are flagged, not removed.
  * ANOMALY_TYPE keeps its original NULLs; ANOMALY_GROUP = COALESCE(ANOMALY_TYPE, 'UNLABELLED').

Outputs:
  data/processed/clean_payments.parquet
  outputs/reports/data_issues_log.md
"""
import os
import datetime as dt
import duckdb

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_CSV = os.path.join(BASE, "data", "swift_umdac_datathon_2026_fictitious_payment_data.csv")
OUT_PARQ = os.path.join(BASE, "data", "processed", "clean_payments.parquet")
OUT_LOG = os.path.join(BASE, "outputs", "reports", "data_issues_log.md")
os.makedirs(os.path.dirname(OUT_PARQ), exist_ok=True)
os.makedirs(os.path.dirname(OUT_LOG), exist_ok=True)

P = lambda s: s.replace(os.sep, "/").replace("'", "''")
LOG = []                      # markdown lines
def h(msg): print("\n" + "=" * 76 + f"\n  {msg}\n" + "=" * 76)
def log(s=""): LOG.append(s)

con = duckdb.connect()
con.execute("PRAGMA enable_progress_bar=false")

# Columns in the raw file (verified against CSV header during inspection)
STR_COLS = ["CURRENCY_CODE", "ORDERING_BIC8", "BENEFICIARY_BIC8", "BIC8_PATH",
            "CONTINUITY_QFLAG", "TRANSACTION_TYPE_CODE", "ORDERING_ACCOUNT",
            "BENEFICIARY_ACCOUNT", "ORDERING_DETAILS", "ORDERING_TOKENS",
            "BENEFICIARY_DETAILS", "BENEFICIARY_TOKENS", "ORDERING_TYPE",
            "BENEFICIARY_TYPE", "ANOMALY_TYPE"]
NUM_COLS = {"EPOCH_SECONDS": "BIGINT", "USD_AMOUNT": "DOUBLE", "TOTAL_DURATION": "DOUBLE",
            "CURRENCY_CONVERSION_COUNT": "INTEGER", "PARTICIPANT_COUNT": "INTEGER"}
DATA_COLS = ["EPOCH_SECONDS", "CURRENCY_CODE", "USD_AMOUNT", "ORDERING_BIC8",
             "BENEFICIARY_BIC8", "BIC8_PATH", "TOTAL_DURATION", "CONTINUITY_QFLAG",
             "CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT", "TRANSACTION_TYPE_CODE",
             "ORDERING_ACCOUNT", "BENEFICIARY_ACCOUNT", "ORDERING_DETAILS",
             "ORDERING_TOKENS", "BENEFICIARY_DETAILS", "BENEFICIARY_TOKENS",
             "ORDERING_TYPE", "BENEFICIARY_TYPE", "ANOMALY_TYPE"]
ID_COLS = ["ORDERING_BIC8", "BENEFICIARY_BIC8", "BIC8_PATH", "ORDERING_ACCOUNT", "BENEFICIARY_ACCOUNT"]

# ── 1. INGEST (all VARCHAR, no inference) ───────────────────────────────────
h("[1] INGEST raw CSV via DuckDB (all_varchar, no type inference)")
con.execute(f"""
    CREATE TABLE raw AS
    SELECT row_number() OVER () AS row_id, *
    FROM read_csv('{P(RAW_CSV)}', header=true, all_varchar=true)
""")
raw_n = con.execute("SELECT COUNT(*) FROM raw").fetchone()[0]
raw_cols = [r[0] for r in con.execute("DESCRIBE raw").fetchall()][1:]
print(f"Raw row count : {raw_n:,}")
print(f"Raw columns   : {len(raw_cols)} -> {raw_cols}")
assert raw_cols == ["DISCLAIMER"] + DATA_COLS, "Header differs from expected schema"
print("Header matches expected 21-column schema (DISCLAIMER + 20 data columns)")

# ── 2. DISCLAIMER ───────────────────────────────────────────────────────────
h("[2] DISCLAIMER column audit")
disc = con.execute("SELECT row_id, DISCLAIMER FROM raw WHERE DISCLAIMER IS NOT NULL").fetchall()
disc_nonnull = len(disc)
print(f"Rows with non-null DISCLAIMER: {disc_nonnull:,} of {raw_n:,}")
for rid, txt in disc:
    print(f"  row_id={rid}: {txt!r}")
# shift check: no data column may contain the disclaimer text
shift = con.execute("SELECT COUNT(*) FROM raw WHERE EPOCH_SECONDS LIKE 'WARNING%'").fetchone()[0]
print(f"Rows where EPOCH_SECONDS holds disclaimer text (column-shift check): {shift}")
assert shift == 0

# ── 3. NULLS + CAST-FAILURE AUDIT ───────────────────────────────────────────
h("[3] NULL counts per column & cast-failure audit (silent-coercion check)")
null_counts = {c: con.execute(f'SELECT COUNT(*) FROM raw WHERE "{c}" IS NULL').fetchone()[0]
               for c in raw_cols}
empty_counts = {c: con.execute(f"SELECT COUNT(*) FROM raw WHERE \"{c}\" = ''").fetchone()[0]
                for c in raw_cols}
print(f"{'column':<28}{'NULL':>12}{'empty-str':>12}")
for c in raw_cols:
    print(f"{c:<28}{null_counts[c]:>12,}{empty_counts[c]:>12,}")

cast_fail = {}
for c, t in NUM_COLS.items():
    cast_fail[c] = con.execute(
        f'SELECT COUNT(*) FROM raw WHERE "{c}" IS NOT NULL AND TRY_CAST("{c}" AS {t}) IS NULL'
    ).fetchone()[0]
print("\nNumeric cast failures (non-null text that fails TRY_CAST):")
for c, n in cast_fail.items():
    print(f"  {c:<28}{NUM_COLS[c]:<9}{n:>6}")
assert all(v == 0 for v in cast_fail.values()), "Silent coercion would occur - aborting"
# integer columns: confirm values are whole numbers (INTEGER cast would round otherwise)
nonint = con.execute("""
    SELECT COUNT(*) FROM raw WHERE
      (TRY_CAST(CURRENCY_CONVERSION_COUNT AS DOUBLE) <> floor(TRY_CAST(CURRENCY_CONVERSION_COUNT AS DOUBLE)))
   OR (TRY_CAST(PARTICIPANT_COUNT AS DOUBLE) <> floor(TRY_CAST(PARTICIPANT_COUNT AS DOUBLE)))
   OR (TRY_CAST(EPOCH_SECONDS AS DOUBLE) <> floor(TRY_CAST(EPOCH_SECONDS AS DOUBLE)))""").fetchone()[0]
print(f"Non-integer values in integer columns: {nonint}")
assert nonint == 0

# ── 4. TYPED TABLE ──────────────────────────────────────────────────────────
sel = []
for c in DATA_COLS:
    if c in NUM_COLS:
        sel.append(f'CAST("{c}" AS {NUM_COLS[c]}) AS "{c}"')
    elif c == "ANOMALY_TYPE":
        sel.append('ANOMALY_TYPE AS ANOMALY_RAW')
    else:
        sel.append(f'CAST("{c}" AS VARCHAR) AS "{c}"')
con.execute(f"CREATE TABLE typed AS SELECT row_id, {', '.join(sel)} FROM raw")

# ── 5. CATEGORICAL VALUE AUDIT ──────────────────────────────────────────────
h("[4] Categorical value audit")
def vc(col, tbl="typed", lim=50):
    return con.execute(
        f"SELECT COALESCE(CAST({col} AS VARCHAR),'<NULL>') v, COUNT(*) n FROM {tbl} "
        f"GROUP BY 1 ORDER BY n DESC LIMIT {lim}").fetchall()
cat = {}
for c in ["ANOMALY_RAW", "ORDERING_TYPE", "BENEFICIARY_TYPE", "CONTINUITY_QFLAG",
          "TRANSACTION_TYPE_CODE", "CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT"]:
    cat[c] = vc(c)
    print(f"\n{c}:")
    for v, n in cat[c]:
        print(f"  {v:<30}{n:>12,}  ({n / raw_n:.4%})")

cur_n = con.execute("SELECT COUNT(DISTINCT CURRENCY_CODE) FROM typed").fetchone()[0]
cur_bad = con.execute("SELECT COUNT(*) FROM typed WHERE CURRENCY_CODE IS NULL OR NOT regexp_matches(CURRENCY_CODE,'^[A-Z]{3}$')").fetchone()[0]
print(f"\nDistinct CURRENCY_CODE: {cur_n}; rows not matching ^[A-Z]{{3}}$ (or NULL): {cur_bad:,}")

# ── 6. NUMERIC / STRUCTURAL AUDIT ───────────────────────────────────────────
h("[5] Numeric & structural audit")
neg = con.execute("SELECT COUNT(*) FROM typed WHERE USD_AMOUNT <= 0").fetchone()[0]
neg_only = con.execute("SELECT COUNT(*) FROM typed WHERE USD_AMOUNT < 0").fetchone()[0]
zero = neg - neg_only
nul_amt = null_counts["USD_AMOUNT"]
print(f"USD_AMOUNT <= 0: {neg:,} (negative {neg_only:,}, zero {zero:,}); NULL: {nul_amt:,}")
dur_neg = con.execute("SELECT COUNT(*) FROM typed WHERE TOTAL_DURATION < 0").fetchone()[0]
print(f"TOTAL_DURATION < 0: {dur_neg:,}")
bic_bad = con.execute("""SELECT COUNT(*) FROM typed WHERE LENGTH(ORDERING_BIC8)<>8 OR LENGTH(BENEFICIARY_BIC8)<>8
                         OR ORDERING_BIC8 IS NULL OR BENEFICIARY_BIC8 IS NULL""").fetchone()[0]
print(f"BIC8 length != 8 or NULL: {bic_bad:,}")
path_mis = con.execute("""
    SELECT COUNT(*) FROM typed
    WHERE BIC8_PATH NOT LIKE '%...%'
      AND len(string_split(BIC8_PATH,';')) <> PARTICIPANT_COUNT""").fetchone()[0]
path_gap = con.execute("SELECT COUNT(*) FROM typed WHERE BIC8_PATH LIKE '%...%'").fetchone()[0]
qn = con.execute("SELECT COUNT(*) FROM typed WHERE CONTINUITY_QFLAG='N'").fetchone()[0]
gap_vs_flag = con.execute("""SELECT COUNT(*) FROM typed
    WHERE (BIC8_PATH LIKE '%...%') <> (CONTINUITY_QFLAG='N')""").fetchone()[0]
print(f"BIC8_PATH containing '...': {path_gap:,}; CONTINUITY_QFLAG='N': {qn:,}; disagreements: {gap_vs_flag:,}")
print(f"Complete paths whose segment count != PARTICIPANT_COUNT: {path_mis:,}")
same_bic = con.execute("SELECT COUNT(*) FROM typed WHERE ORDERING_BIC8 = BENEFICIARY_BIC8").fetchone()[0]
print(f"ORDERING_BIC8 == BENEFICIARY_BIC8: {same_bic:,}")
lz = con.execute("SELECT COUNT(*) FROM typed WHERE ORDERING_BIC8 LIKE '0%'").fetchone()[0]
print(f"ORDERING_BIC8 with a leading zero: {lz:,}")

h("[6] EPOCH_SECONDS range (UTC)")
emin, emax = con.execute("SELECT MIN(EPOCH_SECONDS), MAX(EPOCH_SECONDS) FROM typed").fetchone()
utc = lambda e: dt.datetime.fromtimestamp(e, tz=dt.timezone.utc)
print(f"MIN {emin} -> {utc(emin).isoformat()}\nMAX {emax} -> {utc(emax).isoformat()}")

# ── 7. EXACT DUPLICATES ─────────────────────────────────────────────────────
h("[7] Exact duplicate detection (all 20 data columns; DISCLAIMER excluded)")
# md5 over every data column (NULL-safe, unit-separator joined) -> candidate groups,
# then verified with a full-tuple GROUP BY on the candidates (no hash-collision risk).
exprs = ", ".join(f"COALESCE(CAST(\"{c}\" AS VARCHAR), '<NULL>')" for c in
                  [x if x != "ANOMALY_TYPE" else "ANOMALY_RAW" for x in DATA_COLS])
con.execute(f"""
    CREATE TABLE dupkeys AS
    SELECT row_id, md5(concat_ws(chr(31), {exprs})) AS k FROM typed""")
con.execute("""
    CREATE TABLE dupinfo AS
    SELECT row_id,
           row_number() OVER (PARTITION BY k ORDER BY row_id) AS rn,
           count(*)     OVER (PARTITION BY k)                 AS grp
    FROM dupkeys""")
cand = con.execute("SELECT COUNT(*) FROM dupinfo WHERE grp>1").fetchone()[0]
cols_q = ", ".join(f'"{c}"' if c != "ANOMALY_TYPE" else "ANOMALY_RAW" for c in DATA_COLS)
full_groups = con.execute(f"""
    SELECT COUNT(*) FROM (SELECT {cols_q} FROM typed t JOIN dupinfo d USING(row_id)
                          WHERE d.grp>1 GROUP BY ALL)""").fetchone()[0]
hash_groups = con.execute("SELECT COUNT(DISTINCT k) FROM dupkeys WHERE k IN (SELECT k FROM dupkeys d JOIN dupinfo i USING(row_id) WHERE i.grp>1)").fetchone()[0]
print(f"Rows in duplicate groups: {cand:,}; groups (full-tuple): {full_groups:,}; groups (hash): {hash_groups:,}")
assert full_groups == hash_groups, "md5 collision detected"
dup_extra = con.execute("SELECT COUNT(*) FROM dupinfo WHERE rn>1").fetchone()[0]
print(f"Surplus duplicate rows (rn>1) flagged is_exact_dup: {dup_extra:,}")
xt = con.execute("""
    SELECT COALESCE(t.ANOMALY_RAW,'<NULL>') a, COUNT(*) FILTER (WHERE d.grp>1) in_dup_grp,
           COUNT(*) FILTER (WHERE d.rn>1) surplus, COUNT(*) total
    FROM typed t JOIN dupinfo d USING(row_id) GROUP BY 1 ORDER BY total DESC""").fetchall()
print(f"\n{'ANOMALY_TYPE':<28}{'in dup group':>14}{'surplus (rn>1)':>16}{'total':>12}")
for a, g, s, n in xt:
    print(f"{a:<28}{g:>14,}{s:>16,}{n:>12,}")
dp_total = dict((a, n) for a, g, s, n in xt).get("DUPLICATE_PAYMENT", 0)
dp_exact = dict((a, s) for a, g, s, n in xt).get("DUPLICATE_PAYMENT", 0)
print(f"\nDUPLICATE_PAYMENT labelled: {dp_total:,}; of which byte-identical to an earlier row: {dp_exact:,}")
unl_dup = dict((a, s) for a, g, s, n in xt).get("<NULL>", 0)
print(f"Unlabelled rows that are exact surplus duplicates: {unl_dup:,}")

# ── 8. OUTLIERS vs FAT_FINGER ───────────────────────────────────────────────
h("[8] USD_AMOUNT extremes vs FAT_FINGER_MISTAKE (flag only, never drop)")
q = con.execute("""SELECT quantile_cont(USD_AMOUNT,[0.5,0.99,0.999,0.9999]) FROM typed
                   WHERE ANOMALY_RAW IS NULL""").fetchone()[0]
print(f"UNLABELLED rows quantiles  p50={q[0]:,.2f}  p99={q[1]:,.2f}  p99.9={q[2]:,.2f}  p99.99={q[3]:,.2f}")
thr = q[3]
ext = con.execute(f"""SELECT COALESCE(ANOMALY_RAW,'<NULL>'), COUNT(*) FROM typed
                      WHERE USD_AMOUNT > {thr} GROUP BY 1 ORDER BY 2 DESC""").fetchall()
print(f"Rows above UNLABELLED p99.99 ({thr:,.2f}) by label:")
for a, n in ext:
    print(f"  {a:<28}{n:>10,}")
per_lab = con.execute("""SELECT COALESCE(ANOMALY_RAW,'<NULL>'), COUNT(*), MIN(USD_AMOUNT),
        quantile_cont(USD_AMOUNT,0.5), MAX(USD_AMOUNT)
        FROM typed GROUP BY 1 ORDER BY 2 DESC""").fetchall()
print(f"\n{'label':<28}{'n':>12}{'min':>16}{'median':>16}{'max':>20}")
for a, n, mn, md, mx in per_lab:
    print(f"{a:<28}{n:>12,}{mn:>16,.2f}{md:>16,.2f}{mx:>20,.2f}")

# ── 9. BUILD CLEAN TABLE ────────────────────────────────────────────────────
h("[9] Build clean table (engineered columns, flags; no rows dropped)")
orig = [c for c in DATA_COLS if c != "ANOMALY_TYPE"]
con.execute(f"""
    CREATE TABLE clean AS
    SELECT
        t.row_id,
        {', '.join('t."'+c+'"' for c in orig)},
        t.ANOMALY_RAW                                       AS ANOMALY_TYPE,   -- original label; NULL = no ground-truth label
        COALESCE(t.ANOMALY_RAW, 'UNLABELLED')               AS ANOMALY_GROUP,  -- non-null grouping key for analysis
        epoch_ms(t.EPOCH_SECONDS * 1000)                    AS utc_dt,        -- naive TIMESTAMP, UTC
        CAST(hour(epoch_ms(t.EPOCH_SECONDS * 1000)) AS TINYINT)               AS utc_hour,
        CAST(isodow(epoch_ms(t.EPOCH_SECONDS * 1000)) - 1 AS TINYINT)         AS utc_dow,   -- 0=Mon..6=Sun
        isodow(epoch_ms(t.EPOCH_SECONDS * 1000)) >= 6       AS is_weekend,
        t.ORDERING_TYPE || '2' || t.BENEFICIARY_TYPE        AS party_pair,
        substr(t.ORDERING_BIC8, 5, 2)                       AS ordering_country,
        substr(t.BENEFICIARY_BIC8, 5, 2)                    AS beneficiary_country,
        t.ANOMALY_RAW IS NOT NULL                           AS is_anomaly,
        d.rn > 1                                            AS is_exact_dup,
        d.grp                                               AS dup_group_size
    FROM typed t JOIN dupinfo d USING(row_id)
    ORDER BY t.row_id""")
clean_n = con.execute("SELECT COUNT(*) FROM clean").fetchone()[0]
assert clean_n == raw_n, f"ROW LOSS raw={raw_n} clean={clean_n}"
print(f"clean rows = {clean_n:,} == raw rows = {raw_n:,}  -> zero rows lost")

# ── 10. EXPORT + VERIFY ─────────────────────────────────────────────────────
h("[10] Export parquet & round-trip verification")
con.execute(f"COPY clean TO '{P(OUT_PARQ)}' (FORMAT PARQUET, COMPRESSION ZSTD)")
psize = os.path.getsize(OUT_PARQ)
pq = f"read_parquet('{P(OUT_PARQ)}')"
pn = con.execute(f"SELECT COUNT(*) FROM {pq}").fetchone()[0]
print(f"Parquet rows: {pn:,}  size: {psize/1024**2:,.1f} MB")
assert pn == raw_n

# Checksums: raw VARCHAR text vs parquet values, per ID column (byte-level) + numerics
chk_ok = True
print(f"\n{'check':<34}{'raw':>34}{'parquet':>34}  ok")
for c in ID_COLS + ["ORDERING_DETAILS", "BENEFICIARY_DETAILS", "ORDERING_TOKENS", "BENEFICIARY_TOKENS", "CURRENCY_CODE"]:
    a = con.execute(f'SELECT sum(hash("{c}")::HUGEINT) FROM raw').fetchone()[0]
    b = con.execute(f'SELECT sum(hash("{c}")::HUGEINT) FROM {pq}').fetchone()[0]
    ok = a == b; chk_ok &= ok
    print(f"hash-sum {c:<25}{str(a):>34}{str(b):>34}  {'OK' if ok else 'FAIL'}")
for c in ["EPOCH_SECONDS", "USD_AMOUNT", "TOTAL_DURATION", "CURRENCY_CONVERSION_COUNT", "PARTICIPANT_COUNT"]:
    a = con.execute(f'SELECT sum(CAST("{c}" AS DOUBLE)) FROM raw').fetchone()[0]
    b = con.execute(f'SELECT sum(CAST("{c}" AS DOUBLE)) FROM {pq}').fetchone()[0]
    ok = (a == b) or abs(a - b) <= 1e-9 * abs(a); chk_ok &= ok
    print(f"sum      {c:<25}{a:>34,.4f}{b:>34,.4f}  {'OK' if ok else 'FAIL'}")
assert chk_ok, "Parquet content differs from raw CSV"
nz = con.execute(f"SELECT COUNT(*) FROM {pq} WHERE ORDERING_BIC8 LIKE '0%'").fetchone()[0]
smp = [r[0] for r in con.execute(f"SELECT ORDERING_BIC8 FROM {pq} WHERE ORDERING_BIC8 LIKE '0%' LIMIT 3").fetchall()]
def mask(s):   # generic placeholder: keeps the leading zero, hides the actual identifier (N = digit, X = letter)
    return s[0] + "".join("N" if ch.isdigit() else "X" if ch.isalpha() else ch for ch in s[1:])
smp = [mask(s_) for s_ in smp]
print(f"\nLeading-zero ORDERING_BIC8 rows in parquet: {nz:,} (== typed {lz:,}); masked sample pattern {smp}")
assert nz == lz
schema = con.execute(f"DESCRIBE SELECT * FROM {pq}").fetchall()
print("\nParquet schema:")
for r in schema:
    print(f"  {r[0]:<28}{r[1]}")
assert "DISCLAIMER" not in [r[0] for r in schema]

print("\nEngineered-column checks:")
chk = con.execute(f"""
    SELECT MIN(utc_hour), MAX(utc_hour), MIN(utc_dow), MAX(utc_dow),
           COUNT(*) FILTER (WHERE is_weekend <> (utc_dow >= 5)),
           MIN(utc_dt), MAX(utc_dt),
           COUNT(*) FILTER (WHERE is_anomaly <> (ANOMALY_TYPE IS NOT NULL)),
           COUNT(*) FILTER (WHERE EXTRACT(epoch FROM utc_dt) <> EPOCH_SECONDS) FROM {pq}""").fetchone()
print(f"  utc_hour {chk[0]}-{chk[1]}; utc_dow {chk[2]}-{chk[3]}; weekend/dow mismatches {chk[4]}; "
      f"utc_dt {chk[5]} -> {chk[6]}; is_anomaly/label mismatches {chk[7]}; epoch round-trip mismatches {chk[8]}")
assert chk[4] == 0 and chk[7] == 0 and chk[8] == 0
for col in ["ANOMALY_TYPE", "ANOMALY_GROUP", "party_pair", "is_anomaly", "is_exact_dup", "is_weekend"]:
    print(f"\n  {col}:")
    for v, n in vc(col, pq):
        print(f"    {v:<28}{n:>12,}")
print("\n  ordering_country top 10:")
for v, n in vc("ordering_country", pq, 10):
    print(f"    {v:<28}{n:>12,}")
anom_clean = {v: n for v, n in vc("ANOMALY_GROUP", pq)}
null_pq = con.execute(f"SELECT COUNT(*) FROM {pq} WHERE ANOMALY_TYPE IS NULL").fetchone()[0]
grp_unl = con.execute(f"SELECT COUNT(*) FROM {pq} WHERE ANOMALY_GROUP = 'UNLABELLED'").fetchone()[0]
grp_null = con.execute(f"SELECT COUNT(*) FROM {pq} WHERE ANOMALY_GROUP IS NULL").fetchone()[0]
print(f"\n  ANOMALY_TYPE NULLs preserved in parquet: {null_pq:,} (raw: {null_counts['ANOMALY_TYPE']:,}); "
      f"ANOMALY_GROUP = 'UNLABELLED': {grp_unl:,}; ANOMALY_GROUP NULLs: {grp_null}")
assert null_pq == null_counts["ANOMALY_TYPE"] == grp_unl and grp_null == 0
exact_flag = con.execute(f"SELECT COUNT(*) FROM {pq} WHERE is_exact_dup").fetchone()[0]
assert exact_flag == dup_extra
# Anomaly preservation: label counts parquet == raw
raw_anom = {(a if a is not None else "UNLABELLED"): n for a, n in con.execute(
    "SELECT ANOMALY_TYPE, COUNT(*) FROM raw GROUP BY 1").fetchall()}
assert raw_anom == anom_clean, "Anomaly label counts differ between raw and parquet"
print("\n  Anomaly label counts identical in raw CSV and parquet: OK")

# ── 11. WRITE data_issues_log.md ────────────────────────────────────────────
log("# Data Issues Log - Gate 1 Audit")
log(f"\n- **Generated (UTC):** {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}")
log(f"- **Source:** `{os.path.basename(RAW_CSV)}` ({os.path.getsize(RAW_CSV)/1024**3:.2f} GB)")
log(f"- **Raw rows:** {raw_n:,} | **Clean/parquet rows:** {pn:,} | **Rows dropped:** {raw_n-pn:,}")
log("- **Method:** DuckDB `read_csv(all_varchar=true)` -> explicit `CAST` after a `TRY_CAST` failure audit (0 failures required, run aborts otherwise). All numbers below are printed by `src/01_data_prep_and_audit.py`.")
log("\n## Summary of issues\n")
log("| # | Issue | Rows affected | Decision |")
log("| :-- | :-- | --: | :-- |")
log(f"| 1 | Undocumented `DISCLAIMER` column (multi-line text) | {disc_nonnull:,} non-null | Isolated and excluded from parquet; no column shift |")
log(f"| 2 | `ANOMALY_TYPE` is NULL when a row carries no ground-truth label | {null_counts['ANOMALY_TYPE']:,} | NULLs preserved in `ANOMALY_TYPE`; new column `ANOMALY_GROUP` = `COALESCE(ANOMALY_TYPE,'UNLABELLED')` |")
log(f"| 3 | Label `CUSTOMER_RECALL` not listed in the schema reference | {anom_clean.get('CUSTOMER_RECALL',0):,} | Kept; `is_anomaly=True`; flagged for team |")
log(f"| 4 | Exact duplicate rows (all 20 data cols) | {dup_extra:,} surplus ({cand:,} in groups) | Flagged `is_exact_dup`; none dropped |")
log(f"| 5 | `DUPLICATE_PAYMENT` labels vs exact duplicates | {dp_total:,} labelled / {dp_exact:,} byte-identical | See section below |")
log(f"| 6 | USD_AMOUNT <= 0 | {neg:,} | None found; no action |" if neg == 0 else f"| 6 | USD_AMOUNT <= 0 | {neg:,} | Preserved |")
log(f"| 7 | Invalid CURRENCY_CODE (not 3 uppercase letters / NULL) | {cur_bad:,} | {'None' if cur_bad==0 else 'Preserved'} |")
log(f"| 8 | BIC8 length != 8 / NULL | {bic_bad:,} | {'None' if bic_bad==0 else 'Preserved'} |")
log(f"| 9 | Numeric cast failures | {sum(cast_fail.values()):,} | None - zero silent coercion |")
log(f"| 10 | Leading-zero BIC8 (pattern `{smp[0] if smp else ''}`; N = digit, X = letter) | {lz:,} (ordering side) | Kept as VARCHAR; hash-verified vs raw |")
log(f"| 11 | Incomplete paths (`...` in BIC8_PATH) | {path_gap:,} | Kept; `CONTINUITY_QFLAG='N'` rows = {qn:,}; disagreements = {gap_vs_flag:,} |")
log("\n## 1. `DISCLAIMER` column\n")
log(f"Only {disc_nonnull:,} of {raw_n:,} rows carry a value (row_id {', '.join(str(r) for r,_ in disc)}). Full text:\n")
for _, txt in disc:
    log("```text\n" + txt + "\n```")
log(f"\nColumn-shift check: 0 rows where `EPOCH_SECONDS` contains disclaimer text. Column excluded from `clean_payments.parquet`.")
log("\n## 2. Null counts per raw column\n")
log("| Column | NULL | Empty string |\n| :-- | --: | --: |")
for c in raw_cols:
    log(f"| {c} | {null_counts[c]:,} | {empty_counts[c]:,} |")
log("\n## 3. `ANOMALY_GROUP` distribution (`ANOMALY_TYPE` with NULL shown as UNLABELLED)\n")
log("`UNLABELLED` means no ground-truth label. It is *presumed* normal traffic, but it may contain anomalies that were never labelled (e.g. extreme amounts, Section 5).\n")
log("| ANOMALY_GROUP | Rows | % |\n| :-- | --: | --: |")
for v, n in vc("ANOMALY_GROUP", pq):
    log(f"| {v} | {n:,} | {n/pn:.4%} |")
log("\n`CUSTOMER_RECALL` is present in the data but absent from the challenge schema notes; it is preserved as an anomaly label.")
log("\n## 4. Exact duplicates vs `DUPLICATE_PAYMENT`\n")
log(f"Duplicates are defined on all 20 data columns (including `ANOMALY_TYPE`) using an md5 key, verified collision-free by a full-tuple GROUP BY ({full_groups:,} groups). First occurrence is kept as `is_exact_dup=False`; later copies are `True`.\n")
log("| ANOMALY_TYPE | Rows in dup group | Surplus (is_exact_dup) | Total |\n| :-- | --: | --: | --: |")
for a, g, s, n in xt:
    log(f"| {a if a!='<NULL>' else 'UNLABELLED'} | {g:,} | {s:,} | {n:,} |")
log(f"\n**Finding:** {dp_exact:,} of {dp_total:,} `DUPLICATE_PAYMENT` rows are byte-identical to an earlier row. "
    f"{unl_dup:,} unlabelled rows are exact duplicates of an earlier row. Because duplicate detection includes `ANOMALY_TYPE`, a labelled row can only match another row carrying the same label; near-duplicates (e.g. same payment with a different timestamp) are for later analysis.")
log("\n## 5. Extreme amounts vs `FAT_FINGER_MISTAKE`\n")
log(f"UNLABELLED-row quantiles: p50={q[0]:,.2f}, p99={q[1]:,.2f}, p99.9={q[2]:,.2f}, p99.99={q[3]:,.2f}.\n")
log("| Label | Rows | Min | Median | Max |\n| :-- | --: | --: | --: | --: |")
for a, n, mn, md, mx in per_lab:
    log(f"| {a if a!='<NULL>' else 'UNLABELLED'} | {n:,} | {mn:,.2f} | {md:,.2f} | {mx:,.2f} |")
log(f"\nRows above the UNLABELLED p99.99 ({thr:,.2f}) by label: " + "; ".join(f"{a if a!='<NULL>' else 'UNLABELLED'}={n:,}" for a, n in ext) + ". No row removed.")
log("\n## 6. Other structural checks\n")
log(f"- USD_AMOUNT <= 0: {neg:,} (negative {neg_only:,}, zero {zero:,}); NULL: {nul_amt:,}")
log(f"- TOTAL_DURATION < 0: {dur_neg:,}")
log(f"- Distinct CURRENCY_CODE: {cur_n}; format-invalid: {cur_bad:,} (format only; no external ISO table used)")
log(f"- ORDERING_BIC8 == BENEFICIARY_BIC8: {same_bic:,}")
log(f"- Complete paths whose segment count != PARTICIPANT_COUNT: {path_mis:,}")
log(f"- EPOCH_SECONDS: {emin} -> {utc(emin).isoformat()} ; {emax} -> {utc(emax).isoformat()}")
for c in ["ORDERING_TYPE", "BENEFICIARY_TYPE", "CONTINUITY_QFLAG", "TRANSACTION_TYPE_CODE"]:
    log(f"- `{c}` values: " + ", ".join(f"{v}={n:,}" for v, n in cat[c]))
log("\n## 7. Verification\n")
log(f"- Raw {raw_n:,} = clean {clean_n:,} = parquet {pn:,} rows.")
log("- Hash-sum checks of 5 ID/BIC columns, 4 free-text columns and CURRENCY_CODE are identical between raw CSV text and parquet; sums of the 5 numeric columns match to double-precision rounding (relative error <= 1e-9; the EPOCH_SECONDS sum differs by 2 in 1.7e16, a float-summation artefact, while the epoch -> utc_dt round-trip has 0 mismatches).")
log("- Anomaly label counts identical between raw CSV and parquet.")
log("\n## 8. Engineered columns\n")
log("| Column | Definition |\n| :-- | :-- |")
for k, v in [("row_id", "1-based file order of raw row"), ("utc_dt", "UTC timestamp (timezone-naive) from EPOCH_SECONDS"),
             ("utc_hour", "0-23"), ("utc_dow", "0=Mon..6=Sun"), ("is_weekend", "Sat/Sun (UTC)"),
             ("party_pair", "ORDERING_TYPE + '2' + BENEFICIARY_TYPE"),
             ("ordering_country / beneficiary_country", "chars 5-6 of the BIC8"),
             ("ANOMALY_TYPE", "original label, NULL where unlabelled (unchanged from the raw CSV)"),
             ("ANOMALY_GROUP", "COALESCE(ANOMALY_TYPE, 'UNLABELLED'); use for grouping and filtering"),
             ("is_anomaly", "ANOMALY_TYPE IS NOT NULL"),
             ("is_exact_dup", "row is a 2nd+ copy of an identical earlier row"),
             ("dup_group_size", "number of identical rows sharing this row's content (1 = unique)")]:
    log(f"| `{k}` | {v} |")
with open(OUT_LOG, "w", encoding="utf-8") as f:
    f.write("\n".join(LOG) + "\n")
print(f"\nLog written: {OUT_LOG}")

# ── 12. FINAL SUMMARY ───────────────────────────────────────────────────────
h("GATE 1 - FINAL VERIFICATION SUMMARY")
print(f"""  Raw CSV rows                : {raw_n:>12,}
  Clean table rows            : {clean_n:>12,}
  Parquet rows                : {pn:>12,}
  Rows dropped                : {raw_n-pn:>12,}
  Numeric cast failures       : {sum(cast_fail.values()):>12,}   (zero silent coercion)
  Parquet == raw checksums    : {'PASS' if chk_ok else 'FAIL'}
  Anomaly labels raw==parquet : PASS
  Anomalies preserved         : {sum(n for v, n in anom_clean.items() if v != 'UNLABELLED'):>12,}  ({', '.join(f'{v}={n:,}' for v, n in anom_clean.items() if v != 'UNLABELLED')})
  Exact dup rows flagged      : {dup_extra:>12,}  (0 dropped)
  USD_AMOUNT <= 0             : {neg:>12,}
  BIC8 length != 8            : {bic_bad:>12,}
  Invalid CURRENCY_CODE       : {cur_bad:>12,}
  UTC range                   : {utc(emin):%Y-%m-%d %H:%M} -> {utc(emax):%Y-%m-%d %H:%M}
  Parquet                     : {OUT_PARQ} ({psize/1024**2:,.1f} MB)
  Issues log                  : {OUT_LOG}
  GATE 1 COMPLETE""")
con.close()
