"""Read-only, chunked Swift payment economics exploratory aggregation.
Run: python src/payment_economics/aggregate_evidence.py data/processed/swift_enriched.csv.gz --out findings/payment_economics/exploration
Produces only aggregated JSON, Markdown, PNG files. Requires pandas/matplotlib.
"""
from __future__ import annotations
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLUMNS = ['EPOCH_SECONDS','CURRENCY_CODE','USD_AMOUNT','ORDERING_TYPE','BENEFICIARY_TYPE']


def bump(table, key, count, total):
    table[str(key)][0] += int(count)
    table[str(key)][1] += float(total)


def serialize(table):
    return [{'group': k, 'records': v[0], 'total_usd': round(v[1], 2),
             'mean_usd': round(v[1]/v[0], 2) if v[0] else None} for k,v in
            sorted(table.items(), key=lambda kv: -kv[1][0])]


def bar(labels, values, title, ylabel, path, rotate=0):
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(range(len(labels)), values)
    ax.set_xticks(range(len(labels)), labels, rotation=rotate, ha='right' if rotate else 'center')
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def run(path: Path, out: Path, chunk_size: int, max_rows: int|None):
    out.mkdir(parents=True, exist_ok=True)
    currency, party, bands = (defaultdict(lambda:[0,0.]) for _ in range(3))
    hours, weekdays = Counter(), Counter()
    total, invalid_amount, invalid_time = 0, 0, 0
    cut=[float('-inf'), 100, 1000, 10_000, 100_000, 1_000_000, float('inf')]
    labels=['<100','100–999','1k–9.9k','10k–99.9k','100k–999.9k','>=1m']
    for chunk in pd.read_csv(path, usecols=COLUMNS, dtype=str, keep_default_na=False, chunksize=chunk_size):
        if max_rows is not None:
            chunk=chunk.head(max_rows-total)
        if chunk.empty:
            break
        total += len(chunk)
        amount = pd.to_numeric(chunk['USD_AMOUNT'],errors='coerce')
        invalid_amount += int(amount.isna().sum())
        epoch = pd.to_numeric(chunk['EPOCH_SECONDS'],errors='coerce')
        dt = pd.to_datetime(epoch, unit='s', utc=True, errors='coerce')
        invalid_time += int(dt.isna().sum())
        freq=chunk['CURRENCY_CODE'].value_counts()
        sums=amount.groupby(chunk['CURRENCY_CODE']).sum(min_count=1)
        for key,num in freq.items():
            bump(currency,key,num,sums.get(key, 0))
        combo=chunk['ORDERING_TYPE']+'→'+chunk['BENEFICIARY_TYPE']
        freq=combo.value_counts()
        sums=amount.groupby(combo).sum(min_count=1)
        for key,num in freq.items():
            bump(party,key,num,sums.get(key,0))
        cuts=pd.cut(amount,bins=cut,labels=labels,right=False)
        for key,num in cuts.value_counts().items():
            bump(bands,key,num,0)
        hours.update(dt.dt.hour.dropna().astype(int).tolist())
        weekdays.update(dt.dt.dayofweek.dropna().astype(int).tolist())
        if total % 1_000_000 < chunk_size:
            print(f'economics: {total:,} payments processed',flush=True)
        if max_rows is not None and total >= max_rows:
            break
    result={
        'source': path.name, 'rows_analyzed':total, 'invalid_amount':invalid_amount, 'invalid_timestamp':invalid_time,
        'currency':serialize(currency), 'party_combinations':serialize(party),
        'amount_bands':serialize(bands),
        'utc_hours':[{'hour':h,'records':hours[h]} for h in range(24)],
        'utc_weekdays':[{'weekday_mon0':d,'records':weekdays[d]} for d in range(7)],
        'interpretation_warning':'These are descriptive aggregates, not reconstructed causal rules. Hours are UTC, not local time. Synthetic traffic may not represent actual economic sizes.'
    }
    (out/'economics_aggregates.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    top=result['currency'][:12]
    bar([x['group'] for x in top],[x['records'] for x in top],'Top payment currencies (descriptive)','Payments',out/'currency_counts.png',45)
    bar(labels,[bands[l][0] for l in labels],'Payment amounts (USD bands)','Payments',out/'amount_bands.png')
    bar([str(h) for h in range(24)],[hours[h] for h in range(24)],'Payment frequency by UTC hour','Payments',out/'utc_hourly_counts.png')
    text=[
        '# Payment Economics — exploratory evidence', '',f'- Source: `{path.name}`',f'- Rows analyzed: **{total:,}**',
        f'- Unparseable amounts: **{invalid_amount:,}**; unparseable timestamps: **{invalid_time:,}**.',
        '- Charts: `currency_counts.png`, `amount_bands.png`, `utc_hourly_counts.png`.', '',
        '## Next: construct and test generating-rule hypotheses','',
        '1. Test whether currency preferences depend on participant countries, payment type, or party class.',
        '2. Test conditional amount distributions, controlling for party type and currency.',
        '3. Test UTC temporal patterns by relevant segments; do not equate UTC with local business hours.',
        '4. Measure effect sizes, uncertainty, counterexamples and alternative explanations before writing a final rule.',
        '', '**Caution:** This report is exploratory. No causal rules are established by marginal counts alone.'
    ]
    (out/'economics_evidence.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    print('Wrote',out)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('dataset',type=Path); p.add_argument('--out',type=Path,default=Path('findings/payment_economics/exploration'));p.add_argument('--chunk-size',type=int,default=50_000);p.add_argument('--max-rows',type=int)
    a=p.parse_args();run(a.dataset,a.out,a.chunk_size,a.max_rows)
