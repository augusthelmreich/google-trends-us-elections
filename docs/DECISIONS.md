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