"""
Evaluation: do the search features reduce error beyond the baselines?

Input : data/processed/features.csv        (from 04_features.py)
        data/processed/coverage_audit.csv  (per-fold eligibility of issue topics)
Output: data/processed/results.csv         one row per (test year, model) with all metrics
        data/processed/coefficients.csv    fitted coefficients per fold and model

Design:
  chronological folds   train on elections before T, test on T; T in 2016, 2020, 2024
  models (all OLS with intercept, all include previous two-party share - 50)
      no_swing     predict 0
      historical   intercept + prior share
      issues       historical + eligible issue features
      candidates   historical + candidate contrast
      combined     historical + both
  eligibility     an issue topic enters a fold only if it has no zero state in any
                  TRAINING year of that fold 

Metrics per (year, model):
  mae, rmse, mean_error          
  geographic                     sqrt(rmse^2 - mean_error^2): spread of errors across states
  geo_mae                        MAE after removing the year's mean error -- the error a
                                 state-level feature could actually reduce
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
f = pd.read_csv(ROOT / "data/processed/features.csv")
audit = pd.read_csv(ROOT / "data/processed/coverage_audit.csv")

TEST_YEARS = [2016, 2020, 2024]
topics = pd.read_csv(ROOT / "data/raw/topics.csv")
CORE = set("x_" + n.replace(" ", "_") for n in topics[(topics.kind == "issue") & (topics.set == "core")]["name"])
ISSUES = [c for c in f.columns if c in CORE]
ISSUE_NAME = {c: c[2:].replace("_", " ") for c in ISSUES}          # x_health_insurance -> health insurance


def eligible_issues(train_years):
    """Issue columns whose topic has zero zero-states in every training year."""
    z = audit[(audit.kind == "issue") & audit.year.isin(train_years)].groupby("name").zeros.sum()
    return [c for c in ISSUES if z.get(ISSUE_NAME[c], 1) == 0]


def design(df, cols):
    """Design matrix: a column of ones, prior share - 50, then the requested feature columns."""
    return np.column_stack([np.ones(len(df)), df.dem_share_2p_prev.values - 50] +
                           [df[c].values for c in cols])


def fit(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def metrics(pred, actual):
    err = pred - actual
    me, rmse = err.mean(), np.sqrt(np.mean(err ** 2))
    return dict(mae=np.abs(err).mean(), rmse=rmse, mean_error=me,
                geographic=np.sqrt(max(rmse ** 2 - me ** 2, 0.0)),
                geo_mae=np.abs(err - me).mean())


rows, coefs = [], []
for T in TEST_YEARS:
    train, test = f[f.year < T], f[f.year == T]
    y_tr, y_te = train.swing.values, test.swing.values
    iss = eligible_issues([int(y) for y in sorted(train.year.unique())])
    specs = {"historical": [], "issues": iss, "candidates": ["cand_contrast"], "combined": iss + ["cand_contrast"]}

    rows.append(dict(year=T, model="no_swing", **metrics(np.zeros(len(test)), y_te)))
    for name, cols in specs.items():
        beta = fit(design(train, cols), y_tr)
        rows.append(dict(year=T, model=name, n_features=len(cols), **metrics(design(test, cols) @ beta, y_te)))
        coefs.append(dict(year=T, model=name, intercept=beta[0], prior_share=beta[1],
                          **{c: b for c, b in zip(cols, beta[2:])}))
    print(f"{T}: trained on {[int(y) for y in sorted(train.year.unique())]}, eligible issues = {[ISSUE_NAME[c] for c in iss]}")

res = pd.DataFrame(rows)
res.to_csv(ROOT / "data/processed/results.csv", index=False)
pd.DataFrame(coefs).to_csv(ROOT / "data/processed/coefficients.csv", index=False)

pd.set_option("display.width", 140)
order = ["no_swing", "historical", "issues", "candidates", "combined"]
tab = res.pivot(index="year", columns="model", values="mae")[order]
print("\nMAE (pp)")
print(tab.round(3).to_string())

print("\nDECOMPOSITION: mean error (national miss) | geographic spread | geo_mae (error a state feature could reduce)")
for T in TEST_YEARS:
    r = res[res.year == T].set_index("model").loc[order]
    print(f"\n  {T}")
    print(r[["mae", "mean_error", "geographic", "geo_mae"]].round(3).to_string())

print("\nGAIN ON THE GEOGRAPHIC PART (geo_mae of historical minus geo_mae of model; positive = search features helped)")
g = res.pivot(index="year", columns="model", values="geo_mae")
print((g[["issues", "candidates", "combined"]].sub(g["historical"], axis=0) * -1).round(4).to_string())

print("\nCOEFFICIENTS (same feature, different training sets -- watch the signs)")
print(pd.DataFrame(coefs).round(2).to_string(index=False))

# robustness: the two-party artefact 
utah = f[(f.year == 2016) & (f.state_po == "UT")]
if len(utah):
    train = f[f.year < 2016]; test = f[(f.year == 2016) & (f.state_po != "UT")]
    iss = eligible_issues([2008, 2012])
    b_h = fit(design(train, []), train.swing.values); b_i = fit(design(train, iss), train.swing.values)
    print(f"\n2016 without Utah: historical MAE {metrics(design(test, []) @ b_h, test.swing.values)['mae']:.3f}, "
          f"issues MAE {metrics(design(test, iss) @ b_i, test.swing.values)['mae']:.3f}")
