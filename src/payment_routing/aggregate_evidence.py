"""Read-only, chunked exploratory Swift routing aggregation (no individual BIC IDs exported)."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from collections import Counter, defaultdict
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLUMNS=['BIC8_PATH','ORDERING_BIC8','BENEFICIARY_BIC8','PARTICIPANT_COUNT','CURRENCY_CONVERSION_COUNT','TOTAL_DURATION','TRANSACTION_TYPE_CODE','CONTINUITY_QFLAG']

def path_data(path: str):
    observed=[t.strip() for t in path.split(';') if t.strip() and t.strip() != '...']
    return len(observed), ('...' in [t.strip() for t in path.split(';')]), (observed[0] if observed else ''), (observed[-1] if observed else '')

def add_stat(table,key,amount):
    x=table[str(key)]; x[0]+=1
    if pd.notna(amount): x[1]+=float(amount);x[2]+=1

def as_rows(table):
    return [{'group':k,'records':v[0],'valid_values':v[2], 'mean':round(v[1]/v[2],4) if v[2] else None}
            for k,v in sorted(table.items(),key=lambda kv: (-kv[1][0],kv[0]))]

def bar(labels,values,title,ylabel,file):
    fig,ax=plt.subplots(figsize=(9,5));ax.bar(range(len(labels)),values)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_title(title);ax.set_ylabel(ylabel);fig.tight_layout();fig.savefig(file,dpi=170);plt.close(fig)

def run(source:Path,out:Path,chunk_size:int,max_rows:int|None):
    out.mkdir(parents=True,exist_ok=True)
    counts=Counter();route_types=Counter();duration_by_part=defaultdict(lambda:[0,0.,0]);fx_by_part=defaultdict(lambda:[0,0.,0]);duration_by_type=defaultdict(lambda:[0,0.,0]);route_type_part=Counter()
    rows=0
    for chunk in pd.read_csv(source,usecols=COLUMNS,dtype=str,keep_default_na=False,chunksize=chunk_size):
        if max_rows is not None: chunk=chunk.head(max_rows-rows)
        if chunk.empty: break
        rows+=len(chunk)
        participants=pd.to_numeric(chunk['PARTICIPANT_COUNT'],errors='coerce')
        fx=pd.to_numeric(chunk['CURRENCY_CONVERSION_COUNT'],errors='coerce')
        duration=pd.to_numeric(chunk['TOTAL_DURATION'],errors='coerce')
        for path,ordering,beneficiary,p,n_fx,secs,route_type,continuity in zip(
            chunk['BIC8_PATH'],chunk['ORDERING_BIC8'],chunk['BENEFICIARY_BIC8'],participants,fx,duration,
            chunk['TRANSACTION_TYPE_CODE'],chunk['CONTINUITY_QFLAG']):
            obs,gap,start,end=path_data(path)
            counts['gap_routes']+=int(gap)
            counts['participant_count_mismatch']+=int(pd.isna(p) or int(p)!=obs)
            counts['continuity_gap_mismatch']+=int((continuity=='N') != gap)
            counts['direct_two_participants_mismatch']+=int((route_type=='Direct') != (p==2))
            counts['fx_bound_mismatch']+=int(pd.isna(n_fx) or pd.isna(p) or not (0<=n_fx<=p-1))
            counts['observed_start_mismatch']+=int(start != ordering)
            counts['observed_end_mismatch']+=int(end != beneficiary)
            route_types[route_type]+=1
            if pd.notna(p):
                add_stat(duration_by_part,int(p),secs)
                add_stat(fx_by_part,int(p),n_fx)
                route_type_part[f'{route_type} | {int(p)}']+=1
            add_stat(duration_by_type,route_type,secs)
        if rows%1_000_000 < chunk_size:print(f'routing: {rows:,} payments processed',flush=True)
        if max_rows is not None and rows>=max_rows:break
    result={'source':source.name,'rows_analyzed':rows,'structural_checks':dict(counts),'route_types':dict(route_types),
        'duration_by_participants':as_rows(duration_by_part),'fx_by_participants':as_rows(fx_by_part),
        'duration_by_type':as_rows(duration_by_type),'transaction_type_by_participants':dict(route_type_part),
        'interpretation_warning':'Perfect structural matches do not identify the full hidden generating mechanism. Route endpoints and economic bank-country logic need separate investigation.'}
    (out/'routing_aggregates.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    r=sorted(route_types.items(),key=lambda x:-x[1]);bar([x[0] for x in r],[x[1] for x in r],'Payment route categories','Payments',out/'routing_types.png')
    d=sorted((int(k),v[1]/v[2]) for k,v in duration_by_part.items() if v[2]>0 and int(k)<=12)
    bar([str(k) for k,_ in d],[v for _,v in d],'Mean payment duration by participant count','Duration (seconds)',out/'duration_by_participants.png')
    d=sorted((int(k),v[1]/v[2]) for k,v in fx_by_part.items() if v[2]>0 and int(k)<=12)
    bar([str(k) for k,_ in d],[v for _,v in d],'Mean FX count by participant count','FX conversions',out/'fx_by_participants.png')
    report=['# Payment Routing — exploratory evidence','',f'- Source: `{source.name}`',f'- Rows analyzed: **{rows:,}**','',
            '## Structural mismatches (verify definitions and exceptions)','']
    report += [f'- `{k}`: **{v:,}**' for k,v in sorted(counts.items())]
    report += ['', '## Next deep-rule questions','',
      '1. Which factors determine Direct, Indirect and Covered classification besides path length?',
      '2. Does duration still depend on participants after controlling for route type, FX steps and path continuity?',
      '3. Can currency conversions be reconstructed from currencies implied by bank routes? Test on held-out data.',
      '4. Explain endpoint mismatches (do not overwrite BIC endpoints).',
      '', '**Caution:** These counts, plots and consistency checks are not by themselves causal proof.']
    (out/'routing_evidence.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('Wrote',out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('dataset',type=Path);p.add_argument('--out',type=Path,default=Path('findings/payment_routing/exploration'));p.add_argument('--chunk-size',type=int,default=50_000);p.add_argument('--max-rows',type=int);a=p.parse_args()
    run(a.dataset,a.out,a.chunk_size,a.max_rows)
