"""
Features from the globaltrends package (main path), and a comparison with the
direct-API path from src/robustness/features_api.py.

Package scores come from src/globaltrends_collect.R (data/processed/globaltrends_scores.csv).

Both paths rest on the same API. They differ in the denominator:
  API map    : Google rescales a state's topic share of ALL searches to 0..100 per request
  globaltrends: topic searches / searches for a control basket (gmail, map, translate,
                wikipedia, youtube) per state and month, averaged over Aug-Sep here
Both are then put through the same feature step, x = value / mean_states(value) - 1,
so the comparison isolates the effect of the denominator.

Inputs : data/processed/globaltrends_scores.csv   keyword, state, year, score_aug_sep, n_months
         data/processed/features_api.csv          from robustness/features_api.py (API path)
         data/raw/topics.csv
Outputs: data/processed/features.csv               main feature table (package path)
         data/processed/coverage_audit.csv         per (topic, year): zeros, min, max, mean, eligible
         data/processed/globaltrends_comparison.csv one row per (feature, year): r, n, zeros
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
YEARS = [2008, 2012, 2016, 2020, 2024]

topics = pd.read_csv(ROOT / "data/raw/topics.csv")
api = pd.read_csv(ROOT / "data/processed/features_api.csv")
gt = pd.read_csv(ROOT / "data/processed/globaltrends_scores.csv")

# ---- 1. coverage of the package scores -------------------------------------------------
print(f"package scores: {len(gt)} rows, {gt.keyword.nunique()} keywords, years {sorted(gt.year.unique())}")
bad = gt[(gt.n_months != 2) | gt.score_aug_sep.isna()]
print(f"rows with missing months or NA score: {len(bad)}")
if len(bad):
    print(bad.groupby(["keyword", "year"]).size().to_string())

# ---- 2. label the keywords with the topic names used in features.csv -------------------
issues = topics[(topics.kind == "issue") & (topics.set == "included")][["name", "term"]]
cands = topics[topics.kind == "candidate"][["name", "term", "party", "year"]].astype({"year": int})

gi = gt.merge(issues, left_on="keyword", right_on="term").assign(kind="issue", party=None)
gc = gt.merge(cands, left_on=["keyword", "year"], right_on=["term", "year"]).assign(kind="candidate")
maps = pd.concat([gi, gc], ignore_index=True).rename(columns={"score_aug_sep": "value"})
assert maps.groupby(["kind", "name", "party", "year"], dropna=False).size().eq(51).all(), "expected 51 states per map"

# ---- 3. same feature step as robustness/features_api.py -----------------------------------------------
summary = (maps.groupby(["kind", "name", "party", "year"], dropna=False)["value"]
               .agg(zeros=lambda v: int((v == 0).sum()), min="min", max="max", mean="mean").reset_index())
print("\nPACKAGE SCORES per map (zeros = states with score 0)")
print(summary.pivot(index=["kind", "name", "party"], columns="year", values="zeros").to_string())
print("\nmean score per map (x1000):")
print((summary.pivot(index=["kind", "name", "party"], columns="year", values="mean") * 1000).round(2).to_string())

summary["eligible"] = summary.zeros == 0
summary.to_csv(ROOT / "data/processed/coverage_audit.csv", index=False)
allzero = summary[summary["max"] == 0][["kind", "name", "year"]]
if len(allzero):
    print("\nmaps with score 0 in all 51 states (below threshold when scaled jointly with the control term):")
    print(allzero.to_string(index=False))

# same feature step as robustness/features_api.py; an all-zero map has no mean to divide by, so every
# state sits at the floor (x = -1), exactly where a zero state sits in a normal map
mean = maps.groupby(["name", "party", "year"], dropna=False)["value"].transform("mean")
maps["x"] = np.where(mean > 0, maps["value"] / mean.where(mean > 0, 1) - 1, -1.0)
chk_all = maps.groupby(["name", "party", "year"], dropna=False)["x"].mean()
assert np.allclose(chk_all[chk_all > -1], 0), chk_all[~np.isclose(chk_all, 0) & (chk_all > -1)]

issue_x = (maps[maps.kind == "issue"]
           .pivot(index=["year", "state"], columns="name", values="x")
           .rename(columns=lambda c: "x_" + c.replace(" ", "_"))
           .reset_index())
cand = maps[maps.kind == "candidate"].pivot(index=["year", "state"], columns="party", values="x").reset_index()
cand["cand_contrast"] = cand["D"] - cand["R"]
cand = cand[["year", "state", "cand_contrast"]]

feat_cols = [c for c in api.columns if c.startswith("x_")] + ["cand_contrast"]
gt_feat = (api[["year", "state_po", "dem_share_2p_prev", "swing"]]
           .merge(issue_x, left_on=["year", "state_po"], right_on=["year", "state"], how="left")
           .merge(cand, on=["year", "state"], how="left")
           .drop(columns="state"))[api.columns]
assert len(gt_feat) == len(api) == 255
gt_feat.to_csv(ROOT / "data/processed/features.csv", index=False)
print(f"\nwrote data/processed/features.csv  ({len(gt_feat)} rows, NA cells: {int(gt_feat.isna().sum().sum())})")

# ---- 4. agreement between the two paths, per feature and year -------------------------
both = api.merge(gt_feat, on=["year", "state_po"], suffixes=("_api", "_gt"))
rows = []
for c in feat_cols:
    for y in YEARS:
        g = both[both.year == y]
        a, b = g[c + "_api"], g[c + "_gt"]
        ok = a.notna() & b.notna()
        r = np.corrcoef(a[ok], b[ok])[0, 1] if ok.sum() > 2 else np.nan
        rows.append(dict(feature=c, year=y, r=r, n=int(ok.sum()),
                         zeros_api=int((a <= -1 + 1e-9).sum()), zeros_gt=int((b <= -1 + 1e-9).sum()),
                         sd_api=a.std(), sd_gt=b.std()))
comp = pd.DataFrame(rows)
comp.to_csv(ROOT / "data/processed/globaltrends_comparison.csv", index=False)

print("\nCORRELATION across states, API feature vs package feature (same x transform)")
print(comp.pivot(index="feature", columns="year", values="r").round(2).to_string())
print("\nSTATES AT THE FLOOR (x = -1: zero in the map), API / package")
z = comp.assign(s=lambda d: d.zeros_api.astype(str) + "/" + d.zeros_gt.astype(str))
print(z.pivot(index="feature", columns="year", values="s").to_string())
print("\nSD of the feature by year, package path (compare with robustness/features_api.py output)")
print(comp.pivot(index="feature", columns="year", values="sd_gt").round(3).to_string())
print("\nmean r over all feature-years:", round(comp.r.mean(), 3))
