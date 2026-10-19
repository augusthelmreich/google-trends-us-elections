# Decision log

One line per decision: what was chosen, and why. Newest at the bottom.

| Date | Decision | Reason |
|---|---|---|
| 2026-10-02 | Repository rebuilt from scratch rather than importing earlier project code | Earlier versions had overlapping scope and inconsistent structure; rebuilding each step verifies it |
| 2026-10-02 | Raw Google Trends API responses are kept out of git | Google's Research API guide describes raw data as non-transferable |
| 2026-10-07 | Outcome is two-party Democratic share; target is its change since the previous election | Comparable across years with different third-party strength; cost: third-party surges appear as major-party swings (Utah 2016, +12 pp) |
| 2026-10-07 | Errors reported as national (mean error) and geographic (spread) components alongside MAE | In 2024 all errors share a sign, so MAE equals the national miss and cannot register geographic improvement; the split makes the test interpretable |
| 2026-10-08 | Topic IDs are validated by geography before use; raw API responses cached once and never re-requested | Geography is the only check that catches a wrong entity; the 2020 unemployment map tracks the unemployment rate (NV, KY, NJ, MI on top), so topic meaning must be checked, not assumed |
| 2026-10-12 | Search window is Aug–Sep of each election year | Latest whole-month window that ends before early voting; identical across years; two months limits zeros |
| 2026-10-12 | Topic eligible only if no state is zero in any training year | A zero is below-threshold, not zero interest; immigration excluded (24→6 zeros, 2008–2024) |
| 2026-10-12 | Candidate maps validated by home-state rank AND top-3 states | For general-election nominees top states are battlegrounds (DC, NH, VA, CO), i.e. campaign attention, which the D−R contrast largely cancels |
| 2026-10-12 | Primary metric is MAE on raw swing; geo_mae (MAE after removing the year's mean error) is reported alongside | Raw MAE is dominated by the national swing, which centred state features cannot affect; geo_mae isolates what they can |
| 2026-10-12 | Uncertainty stated by permutation (shuffle features across states within year), not by bootstrap over states | States within an election are not independent draws; the permutation null asks the question that matters: do the features carry state-specific information |
| 2026-10-19 | Search data collected and scored with the supervisors' `globaltrends` package (GitHub 0.2.1, Research API backend); decided before the package run had finished and before any package-path result was seen | It is the instrument the supervisors built for this API (Puhr & Müllner 2021) and its control-basket score keeps years on one scale; the direct one-term-per-request pull stays as a robustness path in `src/robustness/` |
| 2026-10-19 | Package scores go through the same centring step as the API maps (divide by the cross-state mean, subtract 1) | Training pools years, so features must be comparable across years; the control basket's own drift over 2008–2024 would otherwise enter the feature; with the same step the two paths differ only in the denominator, which is what the comparison should isolate |
| 2026-10-19 | A map that is zero in all 51 states is treated as all states below threshold (feature at the floor, topic ineligible) | Scaled jointly with a control term, immigration rounds to zero everywhere in the package in every year; the topic was already ineligible on the API path |
| 2026-10-19 | Results reported for both paths; an effect that appears on one path only is called fragile, not a finding | Issue features improve the geographic component on the package path (shuffle benchmark p = 0.002 pooled) and not on the API path; the index test fails on both |
