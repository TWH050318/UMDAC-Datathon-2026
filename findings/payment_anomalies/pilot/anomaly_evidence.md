# Party & Anomaly Patterns — exploratory evidence

- Source: `swift_enriched.csv.gz`
- Rows analyzed: **5,000**
- Labelled records: **6**.
- Unlabelled payment records are **not confirmed legitimate**.

## Next deep-rule questions

1. Compare each labelled category with appropriately matched unlabelled controls; avoid assuming unlabeled = benign.
2. For duplicates, investigate time windows and repeated payment fingerprints without deleting records.
3. For amount-entry mistakes, test exact shifts in log amounts and matched payment pairs.
4. For account replacement and scams, evaluate changes in account destinations and party-type restrictions.
5. Investigate undocumented `CUSTOMER_RECALL` if observed; ask organisers about its intended definition.
6. Test which token structures are predictive after controlling for party type, and document false positives.

**Caution:** These aggregate counts and token markers are not reconstructed generating rules yet.
