# Decision log

One line per decision: what was chosen, and why. Newest at the bottom.

| Date | Decision | Reason |
|---|---|---|
| 2026-10-02 | Repository rebuilt from scratch rather than importing earlier project code | Earlier versions had overlapping scope and inconsistent structure; rebuilding each step verifies it |
| 2026-10-02 | Raw Google Trends API responses are kept out of git | Google's Research API guide describes raw data as non-transferable |
| 2026-10-07 | Outcome is two-party Democratic share; target is its change since the previous election | Comparable across years with different third-party strength; cost: third-party surges appear as major-party swings (Utah 2016, +12 pp) |
| 2026-10-07 | Errors reported as national (mean error) and geographic (spread) components alongside MAE | In 2024 all errors share a sign, so MAE equals the national miss and cannot register geographic improvement; the split makes the test interpretable |