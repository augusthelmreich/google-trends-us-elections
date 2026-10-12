"""
Permutation test: do the search features behave differently from random features?

Question. 05_evaluate.py found that every search-feature model increases geo_mae
(the error on the geographic part of the swing) in every test year. Adding ANY
regressor that carries no information also tends to increase out-of-sample error,
because the model fits noise in training. So the question is not "is the gain
negative" but "is the observed gain different from what uninformative features
of the same shape would produce".

Method. Within every election year, shuffle each feature column across states
(the feature keeps its distribution per year; its link to the state is destroyed).
Refit the chronological folds, record the geo_mae gain versus the historical
baseline, repeat N times. The observed gain is compared with that distribution.

Reported per model: observed gain, null mean, percentile of the observed value in
the null, and a one-sided p-value for "search features are better than random"
(share of permutations whose gain >= observed). A p around 0.5 means the real
features are indistinguishable from shuffled ones.

Input : data/processed/features.csv, data/processed/coverage_audit.csv
Output: data/processed/permutation.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
f = pd.read_csv(ROOT / "data/processed/features.csv")
audit = pd.read_csv(ROOT / "data/processed/coverage_audit.csv")

TEST_YEARS = [2016, 2020, 2024]
N_PERM = 1000
SEED = 20261012
ISSUES = [c for c in f.columns if c.startswith("x_")]
ISSUE_NAME = {c: c[2:].replace("_", " ") for c in ISSUES}


def eligible_issues(train_years):
    z = audit[(audit.kind == "issue") & audit.year.isin(train_years)].groupby("name").zeros.sum()
    return [c for c in ISSUES if z.get(ISSUE_NAME[c], 1) == 0]


def design(df, cols):
    return np.column_stack([np.ones(len(df)), df.dem_share_2p_prev.values - 50] + [df[c].values for c in cols])


def geo_mae(pred, actual):
    err = pred - actual
    return np.abs(err - err.mean()).mean()


def gains(data):
    """geo_mae(historical) - geo_mae(model), per test year and model. Positive = model helped."""
    out = {}
    for T in TEST_YEARS:
        train, test = data[data.year < T], data[data.year == T]
        iss = eligible_issues([int(y) for y in train.year.unique()])
        specs = {"issues": iss, "candidates": ["cand_contrast"], "combined": iss + ["cand_contrast"]}
        b0, *_ = np.linalg.lstsq(design(train, []), train.swing.values, rcond=None)
        base = geo_mae(design(test, []) @ b0, test.swing.values)
        for m, cols in specs.items():
            b, *_ = np.linalg.lstsq(design(train, cols), train.swing.values, rcond=None)
            out[(T, m)] = base - geo_mae(design(test, cols) @ b, test.swing.values)
    return out


def shuffled(data, rng):
    """Shuffle every feature column across states, separately within each year."""
    d = data.copy()
    feats = ISSUES + ["cand_contrast"]
    for y, idx in d.groupby("year").groups.items():
        idx = np.array(idx)
        for c in feats:
            d.loc[idx, c] = d.loc[rng.permutation(idx), c].values
    return d


observed = gains(f)
rng = np.random.default_rng(SEED)
null = {k: [] for k in observed}
for i in range(N_PERM):
    g = gains(shuffled(f, rng))
    for k in null:
        null[k].append(g[k])

rows = []
for (T, m), obs in observed.items():
    dist = np.array(null[(T, m)])
    rows.append(dict(year=T, model=m, observed_gain=obs, null_mean=dist.mean(), null_sd=dist.std(),
                     percentile=(dist < obs).mean() * 100, p_better_than_random=(dist >= obs).mean()))
# pooled: mean gain across the three test years
for m in ["issues", "candidates", "combined"]:
    obs = np.mean([observed[(T, m)] for T in TEST_YEARS])
    dist = np.mean([np.array(null[(T, m)]) for T in TEST_YEARS], axis=0)
    rows.append(dict(year="pooled", model=m, observed_gain=obs, null_mean=dist.mean(), null_sd=dist.std(),
                     percentile=(dist < obs).mean() * 100, p_better_than_random=(dist >= obs).mean()))

res = pd.DataFrame(rows)
res.to_csv(ROOT / "data/processed/permutation.csv", index=False)
pd.set_option("display.width", 140)
print(f"{N_PERM} permutations, seed {SEED}. Gain = geo_mae(historical) - geo_mae(model); positive = helped.\n")
print(res.round(4).to_string(index=False))
print("\nReading: percentile = share of random-feature runs the real features beat."
      "\n         p_better_than_random ~0.5 means indistinguishable from shuffled features;"
      "\n         small p would mean the real features are better than random.")
