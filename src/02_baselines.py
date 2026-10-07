"""
Baselines: how well can swing be predicted WITHOUT any search data?

Input : data/processed/elections.csv   (from src/01_elections.py)
Output: data/processed/baselines.csv   one row per test year x baseline, with MAE / RMSE / mean error

Evaluation is chronological: a model for test year T is fitted only on elections
before T. Test years are 2016, 2020, 2024 (training starts in 2008).

Three baselines:
  no_swing     predict 0  -> "this state votes exactly as last time"
  historical   OLS: swing ~ 1 + (previous two-party share - 50), fitted on earlier years.
               The intercept is essentially the AVERAGE PAST SWING; the slope lets
               high-share states regress toward the middle.
  oracle_tide  predict each test year's actual mean swing for every state.
               NOT a forecast (it uses the outcome). It shows how much error remains
               once the national tide is known -- the part any state-level feature
               would have to explain.

Every error is also split into a NATIONAL part (the mean error, same sign for all
states) and a GEOGRAPHIC part (the spread of errors across states):
    RMSE^2 = mean_error^2 + geographic^2
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
e = pd.read_csv(ROOT / "data/processed/elections.csv")
TEST_YEARS = [2016, 2020, 2024]


def metrics(pred, actual):
    err = pred - actual
    rmse = np.sqrt(np.mean(err ** 2))
    me = err.mean()
    return dict(mae=np.mean(np.abs(err)), rmse=rmse, mean_error=me,
                geographic=np.sqrt(max(rmse ** 2 - me ** 2, 0.0)))


def fit_ols(X, y):
    """Plain least squares. X already contains a column of ones."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


rows = []
for T in TEST_YEARS:
    train = e[e.year < T]
    test = e[e.year == T]
    y_tr, y_te = train.swing.values, test.swing.values

    # no swing
    rows.append(dict(year=T, model="no_swing", **metrics(np.zeros(len(test)), y_te)))

    # historical OLS
    X_tr = np.column_stack([np.ones(len(train)), train.dem_share_2p_prev.values - 50])
    X_te = np.column_stack([np.ones(len(test)), test.dem_share_2p_prev.values - 50])
    beta = fit_ols(X_tr, y_tr)
    rows.append(dict(year=T, model="historical", **metrics(X_te @ beta, y_te),
                     intercept=beta[0], slope=beta[1], mean_train_swing=y_tr.mean()))

    # oracle tide (diagnostic only)
    rows.append(dict(year=T, model="oracle_tide", **metrics(np.full(len(test), y_te.mean()), y_te)))

res = pd.DataFrame(rows)
res.to_csv(ROOT / "data/processed/baselines.csv", index=False)

pd.set_option("display.width", 120)
print("MAE / RMSE in percentage points; mean_error > 0 = Democratic swing over-predicted\n")
print(res[["year", "model", "mae", "rmse", "mean_error", "geographic"]].round(3).to_string(index=False))

print("\nWhat the historical model actually learned:")
h = res[res.model == "historical"]
print(h[["year", "intercept", "mean_train_swing", "slope"]].round(3).to_string(index=False))
print("\n(intercept ~ mean of past swings: with 2-4 past elections that alternate in sign,"
      "\n this is close to a coin flip, which is why 'historical' loses to 'no swing' twice.)")
