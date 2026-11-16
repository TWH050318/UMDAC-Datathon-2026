"""Read-only, chunked Swift party and anomaly aggregate evidence. No raw accounts or text exported."""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLUMNS=['ANOMALY_TYPE','ORDERING_TYPE','BENEFICIARY_TYPE','USD_AMOUNT','TRANSACTION_TYPE_CODE','ORDERING_TOKENS','BENEFICIARY_TOKENS']
SIGS={'business':'<business:','person_name':'<first_name:','iban':'<iban:','country_code':'<country_code:','finance_word':'<finance_word:'}

def run(source:Path,out:Path,chunk_size:int,max_rows:int|None):
    out.mkdir(parents=True,exist_ok=True)
    total=0;label=Counter();labels_by_pair=Counter();labels_by_route=Counter()
    amount_by_label=defaultdict(lambda:[0,0.,0]);pattern_by_label=Counter();party_pairs=Counter()
    for chunk in pd.read_csv(source,usecols=COLUMNS,dtype=str,keep_default_na=False,chunksize=chunk_size):
        if max_rows is not None: chunk=chunk.head(max_rows-total)
        if chunk.empty: break
        total+=len(chunk)
        lab=chunk['ANOMALY_TYPE'].str.strip().replace('', '<UNLABELLED>')
        pair=chunk['ORDERING_TYPE'].str.strip()+'→'+chunk['BENEFICIARY_TYPE'].str.strip()
        amount=pd.to_numeric(chunk['USD_AMOUNT'],errors='coerce')
        label.update(lab.value_counts().to_dict())
        party_pairs.update(pair.value_counts().to_dict())
        labels_by_pair.update((lab+' | '+pair).value_counts().to_dict())
        labels_by_route.update((lab+' | '+chunk['TRANSACTION_TYPE_CODE']).value_counts().to_dict())
        for name,g in chunk.groupby(lab):
            amounts=amount.loc[g.index].dropna()
            amount_by_label[name][0]+=len(g)
            amount_by_label[name][1]+=float(amounts.sum())
            amount_by_label[name][2]+=len(amounts)
        for side,col in [('ordering','ORDERING_TOKENS'),('beneficiary','BENEFICIARY_TOKENS')]:
            for signal,needle in SIGS.items():
                present=chunk[col].str.contains(needle,regex=False,na=False)
                pattern_by_label.update((lab.loc[present]+' | '+side+' | '+signal).value_counts().to_dict())
        if total%1_000_000 < chunk_size:print(f'anomalies: {total:,} payments processed',flush=True)
        if max_rows is not None and total>=max_rows:break
    result={'source':source.name,'rows_analyzed':total,
            'anomaly_label_counts':dict(label),'party_pair_counts':dict(party_pairs),
            'label_by_party_pair':dict(labels_by_pair),'label_by_route_type':dict(labels_by_route),
            'amount_by_label':[{'label':k,'records':v[0], 'valid_amounts':v[2], 'mean_amount_usd':round(v[1]/v[2],2) if v[2] else None} for k,v in sorted(amount_by_label.items())],
            'token_pattern_presence_by_label':dict(pattern_by_label),
            'interpretation_warning':'Unlabelled does not mean verified legitimate. Labelled-anomaly enrichment samples are intentionally non-representative; do not estimate population rates from them.'}
    (out/'anomaly_aggregates.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    labelled=sorted(((k,v) for k,v in label.items() if k!='<UNLABELLED>'),key=lambda x:-x[1])
    fig,ax=plt.subplots(figsize=(10,5));ax.barh([k for k,v in labelled][::-1],[v for k,v in labelled][::-1]);ax.set_title('Labelled anomaly categories (unlabelled records excluded)');ax.set_xlabel('Payments');fig.tight_layout();fig.savefig(out/'anomaly_categories.png',dpi=170);plt.close(fig)
    parties=sorted(party_pairs.items());fig,ax=plt.subplots(figsize=(7,4));ax.bar([k for k,v in parties],[v for k,v in parties]);ax.set_title('Ordering → beneficiary party combinations');ax.set_ylabel('Payments');fig.tight_layout();fig.savefig(out/'party_combinations.png',dpi=170);plt.close(fig)
    report=['# Party & Anomaly Patterns — exploratory evidence','',f'- Source: `{source.name}`',f'- Rows analyzed: **{total:,}**',f'- Labelled records: **{total-label.get("<UNLABELLED>",0):,}**.',
        '- Unlabelled payment records are **not confirmed legitimate**.','',
        '## Next deep-rule questions','',
        '1. Compare each labelled category with appropriately matched unlabelled controls; avoid assuming unlabeled = benign.',
        '2. For duplicates, investigate time windows and repeated payment fingerprints without deleting records.',
        '3. For amount-entry mistakes, test exact shifts in log amounts and matched payment pairs.',
        '4. For account replacement and scams, evaluate changes in account destinations and party-type restrictions.',
        '5. Investigate undocumented `CUSTOMER_RECALL` if observed; ask organisers about its intended definition.',
        '6. Test which token structures are predictive after controlling for party type, and document false positives.',
        '', '**Caution:** These aggregate counts and token markers are not reconstructed generating rules yet.']
    (out/'anomaly_evidence.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('Wrote',out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('dataset',type=Path);p.add_argument('--out',type=Path,default=Path('findings/payment_anomalies/exploration'));p.add_argument('--chunk-size',type=int,default=50_000);p.add_argument('--max-rows',type=int)
    a=p.parse_args();run(a.dataset,a.out,a.chunk_size,a.max_rows)
