# Payment Routing — exploratory evidence

- Source: `swift_enriched.csv.gz`
- Rows analyzed: **5,000**

## Structural mismatches (verify definitions and exceptions)

- `continuity_gap_mismatch`: **0**
- `direct_two_participants_mismatch`: **0**
- `fx_bound_mismatch`: **0**
- `gap_routes`: **392**
- `observed_end_mismatch`: **234**
- `observed_start_mismatch`: **251**
- `participant_count_mismatch`: **0**

## Next deep-rule questions

1. Which factors determine Direct, Indirect and Covered classification besides path length?
2. Does duration still depend on participants after controlling for route type, FX steps and path continuity?
3. Can currency conversions be reconstructed from currencies implied by bank routes? Test on held-out data.
4. Explain endpoint mismatches (do not overwrite BIC endpoints).

**Caution:** These counts, plots and consistency checks are not by themselves causal proof.
