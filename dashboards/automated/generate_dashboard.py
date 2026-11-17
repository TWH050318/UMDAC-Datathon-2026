#!/usr/bin/env python3
"""Rebuild eight UMDAC Swift evidence dashboards from approved aggregate CSVs.

No raw transaction data is loaded or exported. Run from an extracted
UMDAC_Swift_Dashboard_Starter_Pack directory, or pass --input /path/to/pack.
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd

NAVY = "#172A44"
INK = "#24364D"
MUTED = "#65748B"
TEAL = "#0A978B"
BLUE = "#6277CE"
GOLD = "#D69E49"
RED = "#B85B61"
PALE = "#F3F6FA"
BORDER = "#DDE5EF"
WHITE = "#FFFFFF"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.titlesize": 11, "axes.labelsize": 9,
    "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
    "pdf.fonttype": 42, "savefig.facecolor": PALE,
})

ROOT = None


def read(group: str, filename: str) -> pd.DataFrame:
    path = ROOT / group / "data" / filename
    if not path.is_file():
        raise FileNotFoundError(f"Missing aggregate CSV: {path}\nExtract the dashboard starter pack and pass --input to its root directory.")
    return pd.read_csv(path)


def card(fig, xywh, color=WHITE, lw=0.9, rad=.016):
    x, y, w, h = xywh
    r = FancyBboxPatch((x,y),w,h,boxstyle=f"round,pad=0.004,rounding_size={rad}",
                       edgecolor=BORDER if color==WHITE else color,
                       facecolor=color,linewidth=lw,transform=fig.transFigure,zorder=-2)
    fig.patches.append(r)


def textwrap_fig(s: str, width: int) -> str:
    return "\n".join(textwrap.wrap(s, width=width, break_long_words=False, break_on_hyphens=False))


def setup_page(page, title, subtitle, metrics, rule, meaning, caveat, sources, chart_titles, three=False):
    fig = plt.figure(figsize=(16, 9), facecolor=PALE)
    fig.add_artist(Rectangle((0,.874),1,.126,transform=fig.transFigure,facecolor=NAVY,edgecolor=NAVY,zorder=-5))
    fig.text(.045,.956,f"FEATURE GROUP {page:02d} / 08",fontsize=10,fontweight="bold",color="#8ED3CF",va="center")
    fig.text(.045,.913,title,fontsize=25,fontweight="bold",color=WHITE,va="center")
    fig.text(.96,.949,"UMDAC DATATHON 2026  |  SWIFT",ha="right",color="#D0DCEB",fontsize=10,weight="bold")
    fig.text(.96,.912,subtitle,ha="right",color="#C2D0DF",fontsize=9)
    for i,(value, label) in enumerate(metrics):
        x = .045 + i*.310
        card(fig,(x,.749,.294,.108))
        fig.text(x+.017,.815,str(value),fontsize=21,color=NAVY,weight="bold",va="center")
        fig.text(x+.017,.772,str(label),fontsize=9.3,color=MUTED,va="center")
    n = 3 if three else 2
    x_positions = [.045,.365,.685] if three else [.045,.525]
    widths = [.294]*3 if three else [.454,.454]
    axes = []
    for i in range(n):
        x, w = x_positions[i], widths[i]
        card(fig,(x,.357,w,.375))
        fig.text(x+.017,.698,chart_titles[i],fontsize=11,weight="bold",color=INK,va="center")
        ax = fig.add_axes([x+.038,.398,w-.073,.265],facecolor=WHITE)
        for spine in ax.spines.values():spine.set_visible(False)
        ax.grid(axis="y",alpha=.22,color="#8194AB")
        ax.set_axisbelow(True)
        ax.tick_params(axis="both",length=0,pad=7)
        axes.append(ax)
    card(fig,(.045,.059,.934,.280))
    fig.text(.065,.306,"RECONSTRUCTED RULE / OBSERVED PATTERN",fontsize=9,weight="bold",color=TEAL)
    fig.text(.065,.275,textwrap_fig(rule,95),fontsize=11.25,weight="bold",color=INK,va="top",linespacing=1.45)
    fig.text(.065,.157,"INTERPRETATION",fontsize=9,weight="bold",color=TEAL)
    fig.text(.065,.132,textwrap_fig(meaning,137),fontsize=9.4,color=INK,va="top",linespacing=1.34)
    fig.text(.065,.075,"LIMITATION: "+textwrap_fig(caveat,157),fontsize=8.6,color=MUTED,va="top")
    fig.text(.047,.026,f"EVIDENCE: {sources}",fontsize=7.9,color=MUTED,va="center")
    fig.text(.98,.026,f"{page:02d} / 08",fontsize=8.5,color=MUTED,ha="right",va="center")
    return fig,axes


def annotate_bars(ax,bars,fmt=lambda n: f"{n:.1f}",dy=3):
    for r in bars:
        ax.annotate(fmt(r.get_height()),(r.get_x()+r.get_width()/2,r.get_height()),
                    xytext=(0,dy),textcoords="offset points",ha="center",va="bottom",fontsize=8.1,color=INK)


def save_page(pdf,fig,out,page):
    pdf.savefig(fig,facecolor=PALE)
    fig.savefig(out/f"dashboard_{page:02d}.png",dpi=125,facecolor=PALE)
    plt.close(fig)
    print(f"  Page {page:02d}/08 created",flush=True)


def page1():
    g="01_Payment_Routing"
    p=read(g,"routing_participant_count.csv")
    c=read(g,"routing_covered_by_k_domestic.csv")
    p=p.query("2 <= k <= 9").copy()
    q=p.query("3 <= k <= 9")
    fig,(a,b,d)=setup_page(1,"Payment Routing","Route structure and probabilistic selection",
        [("10.0M","payments in source dataset"),(f"{p.loc[p.k.eq(2),'share'].iloc[0]:.1%}","2-bank paths"),(f"{q.ratio_to_previous.mean():.1%}","mean continuation ratio, k=3..9")],
        "Common route lengths follow an approximately geometric progression; covered-route share differs by domestic versus cross-border status.",
        "A near-constant route-length ratio is consistent with probabilistic path extension. Domestic payments have a higher covered-route share at matched path lengths.",
        "Supported synthetic-generator hypotheses, not recovered source code; longer paths are sparse.",
        "routing_participant_count.csv; routing_covered_by_k_domestic.csv",
        ["Payments by number of BICs","Continuation ratio","Covered routing share"],True)
    a.bar(p.k.astype(str),p.n/1e6,color=TEAL)
    a.set_ylabel("Millions of payments");a.yaxis.set_major_locator(MaxNLocator(5))
    b.plot(q.k,q.ratio_to_previous*100,"o-",lw=2.2,color=BLUE)
    b.axhline(36.8,color=GOLD,lw=1.6,ls="--",label="36.8% reference")
    b.set_ylim(33,41);b.set_xlabel("Observed BIC count");b.set_ylabel("Ratio (%)")
    b.legend(loc="lower right",fontsize=7,frameon=False)
    for value,lab,color in [(False,"Cross-border",BLUE),(True,"Domestic",TEAL)]:
        s=c[(c.IS_DOMESTIC==value)&c.k.between(3,7)].sort_values("k")
        d.plot(s.k,s.share_covered*100,"o-",lw=2,label=lab,color=color)
    d.set_xlabel("Observed BIC count");d.set_ylabel("Covered share (%)")
    d.set_ylim(0,25);d.set_xticks([3,4,5,6,7]);d.legend(fontsize=7,frameon=False)
    return fig


def page2():
    g="02_Duration_Continuity"
    gap=read(g,"continuity_gap_model.csv").query("k<=10")
    dur=read(g,"duration_by_participants.csv").query("k<=9")
    v=read(g,"validation_summary.csv")
    r2=float(v.loc[v.measure.str.contains("R² on test",regex=False),"held_out_value"].iloc[0])
    f2=float(v.loc[v.measure.str.contains("share of test payments within a factor of 2",regex=False),"held_out_value"].iloc[0])
    fig,(a,b)=setup_page(2,"Duration & Continuity","Testing path gaps and bank-dependent processing time",
        [(f"{r2:.2%}", "held-out R² | 76.7% test coverage"),(f"{f2:.1%}","bank-pair within 2x"),("~5%","estimated gap per link")],
        "Observed route-gap probability closely matches 1 - (0.95)^(k-1); payment duration increases with the number of intermediaries.",
        "Independent link-level interruptions offer a simple explanation for missing paths. Bank-specific processing delays can explain much of direct-payment duration on eligible pairs.",
        "98.2% held-out R² covers frequent, eligible bank pairs (~76.7% of test payments); 3-bank additive accuracy is materially weaker (~60.7% within 2x).",
        "continuity_gap_model.csv; duration_by_participants.csv; validation_summary.csv",
        ["Path gap: observed vs model","Mean and median duration by BIC count"])
    a.plot(gap.k,gap.observed_p_gap*100,"o-",lw=2.2,color=TEAL,label="Observed")
    a.plot(gap.k,gap.model_p_5pct_per_link*100,"--",lw=2,color=BLUE,label="5% per link model")
    a.set_xlabel("Observed BICs (k)");a.set_ylabel("Probability of gap (%)")
    a.legend(frameon=False,fontsize=8)
    b.plot(dur.k,dur.med,"o-",lw=2.2,color=TEAL,label="Median")
    b.plot(dur.k,dur["mean"],"s--",lw=1.7,color=GOLD,label="Mean")
    b.set_xlabel("Observed BICs (k)");b.set_ylabel("Duration (seconds)");b.legend(frameon=False,fontsize=8)
    return fig


def page3():
    g="03_Currency_Conversions"
    fx=read(g,"fx_rule_summary.csv")
    v=read(g,"validation_summary.csv")
    unseen=float(v.loc[v.rule.str.contains("NOT seen in train",case=False),"held_out_value"].iloc[0])
    paths=float(v.loc[v.rule.str.contains("3-6 bank paths",case=False),"held_out_value"].iloc[0])
    s=fx.share_converting.values*100
    fig,(a,b)=setup_page(3,"Currency Conversions","Currency-area crossings as a generating mechanism",
        [(f"{unseen:.2%}","held-out unseen country pairs"),(f"{paths:.2%}","held-out 3–6-bank paths"),("100%","cross-area links with FX")],
        "An FX step occurs at links crossing inferred currency-area boundaries; same-area links show no FX conversion in the tested direct-payment links.",
        "The synthetic generator appears to model currency conversion using economic currency areas rather than simply testing whether two bank countries differ.",
        "Currency areas were inferred from training data. Unseen country pairs means pairs absent from training, not necessarily unseen countries; results are not 100%.",
        "fx_rule_summary.csv; validation_summary.csv",["Currency-area boundary evidence","Held-out rule accuracy"])
    labels=["Same country","Cross-country,\nsame area","Different\ncurrency area"]
    bars=a.bar(labels,s,color=[BLUE,BLUE,TEAL],width=.58)
    a.set_ylim(0,118);a.set_ylabel("Links with conversion (%)")
    annotate_bars(a,bars,lambda x:f"{x:.0f}%")
    vals=[unseen*100,paths*100]
    bars=b.bar(["Unseen country\npairs","Unseen 3–6\nbank paths"],vals,color=[BLUE,TEAL],width=.52)
    b.set_ylim(0, 105)
    b.set_ylabel("Held-out accuracy (%)")
    annotate_bars(b,bars,lambda x:f"{x:.2f}%")
    return fig


def page4():
    g="04_Payment_Amounts"
    amounts=read(g,"amount_by_flow.csv")
    rounds=read(g,"amount_roundness.csv")
    bb=float(amounts.loc[amounts.FLOW.eq("B2B"),"median_usd"].iloc[0])
    cc=float(amounts.loc[amounts.FLOW.eq("C2C"),"median_usd"].iloc[0])
    usd=float(rounds.loc[rounds.is_usd==True,"share_whole_units"].iloc[0])
    fig,(a,b)=setup_page(4,"Payment Amounts","Party-type scale and payment-currency rounding",
        [(f"${bb:,.0f}","B2B median USD eq., unlabelled"),(f"${cc:,.0f}","C2C median USD eq., unlabelled"),(f"{usd:.1%}","unlabelled USD: whole units")],
        "Payment values differ strongly by sender/recipient party type, with approximately multiplicative business effects; USD-denominated amounts show pronounced rounding.",
        "The synthetic mechanism plausibly assigns higher payment scales to business parties and allows currency-specific conventions for round-number payments.",
        "These amount and roundness aggregates cover unlabelled payments only; unlabelled does not mean confirmed normal. The log-normal approximation is not exact.",
        "amount_by_flow.csv; amount_roundness.csv",["Median payment value by party flow","Whole-unit and $100 rounding"])
    bars=a.bar(amounts.FLOW,amounts.median_usd,color=[TEAL,BLUE,BLUE,GOLD],width=.56)
    a.set_ylabel("Median USD-equivalent value");a.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:f"${x/1000:.0f}k"))
    annotate_bars(a,bars,lambda x:f"${x:,.0f}")
    names=["Non-USD", "USD"]
    ss=rounds.sort_values("is_usd")
    xx=np.arange(2);w=.32
    r1=b.bar(xx-w/2,ss.share_whole_units*100,width=w,color=TEAL,label="Whole units")
    r2=b.bar(xx+w/2,ss.share_multiple_of_100*100,width=w,color=BLUE,label="Multiples of 100")
    b.set_xticks(xx,names);b.set_ylim(0,46);b.set_ylabel("Share (%)");b.legend(frameon=False,fontsize=8)
    return fig


def page5():
    g="05_Currency_Patterns"
    cc=read(g,"currency_overview.csv").head(8)
    ch=read(g,"currency_choice_rule.csv")
    eur=float(cc.loc[cc.CURRENCY_CODE.eq("EUR"),"share"].iloc[0])
    usd=float(cc.loc[cc.CURRENCY_CODE.eq("USD"),"share"].iloc[0])
    xborder=ch[ch.IS_DOMESTIC==False].copy(); domestic=ch[ch.IS_DOMESTIC==True].copy()
    sender=float(xborder.loc[xborder.currency_choice.str.contains("2 sender home"),"share"].iloc[0])
    d_both=float(domestic.loc[domestic.currency_choice.str.contains("both home"),"share"].iloc[0])
    fig,(a,b)=setup_page(5,"Currency Patterns","Choosing payment currency from country-currency preferences",
        [(f"{eur:.1%}","EUR share, unlabelled payments"),(f"{sender:.1%}","cross-border: sender home"),(f"{d_both:.1%}","domestic: both home")],
        "Currency choice is strongly associated with the parties' inferred home currencies, with different rules for domestic and cross-border payments.",
        "Home-currency preference resembles local invoicing conventions, while USD/EUR vehicle currencies can represent international settlement choices.",
        "Home currencies are inferred from data. Domestic and cross-border results have different denominators and should not be pooled as one rule.",
        "currency_overview.csv; currency_choice_rule.csv",["Eight most frequent currencies","Currency-choice categories by geography"])
    bars=a.bar(cc.CURRENCY_CODE,cc.share*100,color=[TEAL if k=="EUR" else BLUE for k in cc.CURRENCY_CODE])
    a.set_ylabel("Share of currency-coded payments (%)")
    keys=ch.currency_choice.drop_duplicates().tolist()
    short=["Both home","Sender home","Receiver home","Vehicle","Other"]
    xx=np.arange(len(keys));w=.35
    dmap=dict(zip(domestic.currency_choice,domestic.share));xmap=dict(zip(xborder.currency_choice,xborder.share))
    b.bar(xx-w/2,[100*dmap.get(k,0) for k in keys],width=w,label="Domestic",color=TEAL)
    b.bar(xx+w/2,[100*xmap.get(k,0) for k in keys],width=w,label="Cross-border",color=BLUE)
    b.set_xticks(xx,short,rotation=15,ha="right");b.set_ylabel("Within-group share (%)")
    b.legend(frameon=False,fontsize=8)
    return fig


def page6():
    g="06_Temporal_Patterns"
    dow=read(g,"time_day_of_week.csv")
    local=read(g,"time_weekend_local_vs_utc.csv")
    saturday=float(dow.loc[dow.DOW.eq(6),"B_vs_weekday"].iloc[0])
    sunday=float(dow.loc[dow.DOW.eq(7),"B_vs_weekday"].iloc[0])
    fig,(a,b)=setup_page(6,"Temporal Patterns","Weekday effects and alternative local-time representations",
        [(f"{saturday:.1%}","Sat business vs weekday"),(f"{sunday:.1%}","Sun business vs weekday"),("7 days","daily pattern observed")],
        "Daily activity levels vary by weekday; both business and consumer payments show a pronounced weekend reduction in the analysed time series.",
        "Scheduled business activity and consumer payment routines may explain weekly cycles; local-time adjustments offer a plausible geographic explanation for timing patterns.",
        "The exact generator's time-zone logic is not established by this plot; these panels compare reported temporal summaries rather than proving local-hour scheduling.",
        "time_day_of_week.csv; time_weekend_local_vs_utc.csv",["Business vs consumer weekday profiles","Business: UTC vs local-normalised pattern"])
    xx=np.arange(1,8)
    a.plot(xx,dow.B_vs_weekday,"o-",color=TEAL,lw=2.3,label="Business")
    a.plot(xx,dow.C_vs_weekday,"s--",color=BLUE,lw=2,label="Consumer")
    a.axhline(1,color=GOLD,ls=":",lw=1.5)
    a.set_xticks(xx,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
    a.set_ylabel("Relative to weekday average");a.legend(frameon=False,fontsize=8)
    b.plot(xx,local.UTC_business,"o-",color=BLUE,lw=2,label="UTC")
    b.plot(xx,local.local_business,"s-",color=TEAL,lw=2,label="Local time")
    b.set_xticks(xx,["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])
    b.set_ylabel("Normalised business activity");b.legend(frameon=False,fontsize=8)
    return fig



def page7():
    g = "07_Parties_Geography"
    pr = read(g, "entity_proximity.csv")
    mix = read(g, "party_flow_mix.csv")

    close = pr.iloc[1]

    fig, (a, b) = setup_page(
        7,
        "Customer Identifier Proximity",
        "Customer-number differences versus random assignment",
        [
            (f"{close.lift:.2f}x", "lift for ID differences of 10–99"),
            ("2.98M", "payments with both accounts IBAN-style"),
            ("4 flows", "B2B / B2C / C2B / C2C")
        ],
        "Payments with numerically similar sender and receiver "
        "customer IDs occur more often than expected under "
        "random receiver assignment.",
        "The pattern may reflect customer-number assignment or "
        "synthetic community generation. It does not establish "
        "physical geographical proximity.",
        "Customer-ID proximity was analysed on 2,978,599 payments "
        "with both accounts IBAN-style. Identifier assignment "
        "may explain the observed association.",
        "entity_proximity.csv; party_flow_mix.csv",
        [
            "Customer-number proximity vs random",
            "Party-flow mix: observed vs independent (all 10M)"
        ]
    )

    labels = [
        "<10", "10–99", "100–999",
        "1k–10k", "10k–100k", "100k+"
    ]

    x = np.arange(len(labels))

    a.bar(
        x,
        pr.lift,
        color=[TEAL] * 4 + [BLUE] * 2
    )

    a.axhline(1, color=GOLD, ls="--", lw=1.6)
    a.set_xticks(x, labels, rotation=18, ha="right")
    a.set_ylabel("Lift (observed / random)")
    a.set_ylim(0, 5.5)

    flow = (mix.o + "2" + mix.b).tolist()
    xx = np.arange(len(flow))
    w = 0.33

    b.bar(
        xx - w / 2,
        mix.share * 100,
        width=w,
        color=TEAL,
        label="Observed"
    )

    b.bar(
        xx + w / 2,
        mix.expected_if_independent * 100,
        width=w,
        color=BLUE,
        label="Independent baseline"
    )

    b.set_xticks(xx, flow)
    b.set_ylabel("Share of payments (%)")
    b.legend(fontsize=8, frameon=False)

    return fig


def page8():
    g="08_Anomaly_Patterns"
    ov=read(g,"anomaly_overview.csv");ov=ov[ov.ANOMALY!="NONE"].copy()
    dup=read(g,"anomaly_duplicate_group_sizes.csv")
    romance=read(g,"anomaly_romance_escalation.csv")
    fig,(a,b,c)=setup_page(8,"Anomaly Patterns","Distinct labelled anomaly mechanisms",
        [(f"{int(ov.n.sum()):,}","payments carrying anomaly labels"),(f"{int(dup.n_groups.sum()):,}","duplicate-payment clusters"),("2–5","duplicate cluster sizes")],
        "Labelled anomalies exhibit different structures: duplicate-payment labels form short clusters, while romance-scam series show increasing relative payment amounts.",
        "These mechanisms can represent user re-submission mistakes and escalating fraud sequences; they were intentionally planted in the synthetic dataset.",
        "Unlabelled payments are not verified normal. Other labels (including CUSTOMER_RECALL) do not all have validated generating rules.",
        "anomaly_overview.csv; anomaly_duplicate_group_sizes.csv; anomaly_romance_escalation.csv",
        ["Labelled payments by category","Duplicate group sizes","Romance-scam amount sequence"],True)
    s=ov.sort_values("n",ascending=True)
    names={"ROMANCE_SCAM":"Romance", "FAT_FINGER_MISTAKE":"Fat finger", "CEO_SCAM":"CEO scam", "DUPLICATE_PAYMENT":"Duplicate", "ACCOUNT_REPLACEMENT_SCAM":"Account swap", "CUSTOMER_RECALL":"Recall"}
    a.barh([names.get(v,v) for v in s.ANOMALY],s.n,color=TEAL)
    a.set_xlabel("Labelled payments")
    b.bar(dup.copies.astype(str),dup.n_groups,color=BLUE)
    b.set_xlabel("Copies per cluster");b.set_ylabel("Number of clusters")
    c.plot(romance.step,romance.median_rel_amount,"o-",color=TEAL,lw=2)
    c.set_xlabel("Payment sequence step");c.set_ylabel("Median amount / first")
    
    # Show how the romance-scam sample size decreases by sequence step
    c.text(
        0.04, 0.94,
        "n = 500 at step 1; 69 at step 8",
        transform=c.transAxes,
        fontsize=7.5,
        color=MUTED,
        ha="left",
        va="top"
    )

    c.set_yscale("log");c.set_yticks([1,2,4,8,16]);c.get_yaxis().set_major_formatter(FuncFormatter(lambda v,pos:f"{v:g}x"))
    return fig


def main():
    global ROOT
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument("--input",type=Path,default=Path(__file__).resolve().parent,help="Extracted starter-pack root with 01_... / 08_... folders")
    pa.add_argument("--output",type=Path,default=Path("dashboard_output"),help="Output directory for PDF and 8 PNG pages")
    args=pa.parse_args()
    ROOT=args.input.expanduser().resolve()
    dest=args.output.expanduser().resolve()
    dest.mkdir(parents=True,exist_ok=True)
    output_pdf=dest/"UMDAC_Swift_8_Page_Dashboard.pdf"
    print(f"Reading approved aggregate data from: {ROOT}",flush=True)
    print("Generating 8 dashboard pages (no raw payment data needed)...",flush=True)
    with PdfPages(output_pdf,metadata={"Title":"UMDAC Datathon 2026 - Swift Payment Rule Dashboards","Author":"UMDAC analysis team", "Subject":"Evidence summaries from corrected aggregate results"}) as pdf:
        for i,fun in enumerate((page1,page2,page3,page4,page5,page6,page7,page8),start=1):
            fig=fun();save_page(pdf,fig,dest,i)
    print(f"DONE: {output_pdf}",flush=True)
    print(f"Page images: {dest / 'dashboard_01.png'} through {dest / 'dashboard_08.png'}",flush=True)


if __name__=="__main__":
    main()
