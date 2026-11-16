# Methodology: how we reverse-engineer the generator

The dataset was produced by hard-coded rules plus random draws (the file's own disclaimer says so).
Recovering such a generator is a structure-discovery problem, not a prediction problem, so we use
the simplest method that answers each question and validate every rule on all 10M rows.

| Step | What we do | Idea it comes from |
|---|---|---|
| 1. Profile every column | Domains, formats, missing values, distributions | Exploratory data analysis (Tukey, 1977) |
| 2. Find exact dependencies | Test "X determines Y" on all rows; 100% match = structural rule (e.g. `PARTICIPANT_COUNT` = BICs in path) | Functional-dependency discovery in databases (Huhtala et al., 1999) |
| 3. Identify the random draws | Fit the noise: geometric path length, log-normal amounts, Bernoulli 5% per link | Generative / structural causal models: each variable = function of its parents + independent noise (Pearl, 2009; Peters et al., 2017) |
| 4. Order the variables causally | Ask which variable could have been generated first (country → bank → account format → currency → conversions) and check that a child is independent of other variables once its parents are fixed | Conditional-independence reasoning behind constraint-based causal discovery (Spirtes et al., 2000) |
| 5. Rule out confounders | Re-test every effect inside strata (per currency, per flow, domestic vs cross-border) | Stratification / Simpson's paradox (Simpson, 1951) |
| 6. Validate and grade | `rule_check` gives scope, matches and exceptions; each rule is graded Proven / Supported / Open / Rejected | Falsification: a rule must survive a test it could fail |
| 6b. Hold out | Learn each rule on the first 2/3 of the period and score it on the last 1/3 (and, for FX, on country pairs and path lengths never used for learning) | Out-of-sample validation |
| 7. Explain | Give an economic reason and check a second prediction of that reason in the data | — |

Why not a machine-learning model: a model that predicts well does not state the rule. Where a tree or
regression helps to locate a candidate rule, the final evidence is still a group comparison anyone can re-run.

Limits we keep in view: three months of data only; UTC timestamps; a rule that fits may not be the
generator's exact formula (several formulas can give the same distribution), so we state parameters
with the precision the data supports.

## References (APA) — verify each entry before it goes on a slide
- Huhtala, Y., Kärkkäinen, J., Porkka, P., & Toivonen, H. (1999). TANE: An efficient algorithm for discovering functional and approximate dependencies. *The Computer Journal, 42*(2), 100–111.
- Pearl, J. (2009). *Causality: Models, reasoning, and inference* (2nd ed.). Cambridge University Press.
- Peters, J., Janzing, D., & Schölkopf, B. (2017). *Elements of causal inference: Foundations and learning algorithms*. MIT Press.
- Simpson, E. H. (1951). The interpretation of interaction in contingency tables. *Journal of the Royal Statistical Society: Series B, 13*(2), 238–241.
- Spirtes, P., Glymour, C., & Scheines, R. (2000). *Causation, prediction, and search* (2nd ed.). MIT Press.
- Tukey, J. W. (1977). *Exploratory data analysis*. Addison-Wesley.
