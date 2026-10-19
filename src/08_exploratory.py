"""
EXPLORATORY follow-up to the party-index test. Not pre-specified; nothing here changes
the confirmatory verdict in docs/PREREG_party_index.md.

Question. The index correlated NEGATIVELY with the deviation from national swing
(mean r = -0.16). Two candidate explanations:
  (a) partisanship: the index tracks how Democratic a state already is, and in 2020/2024
      the bluest states moved most toward the Republican candidate relative to others;
  (b) economics: the index is carried by unemployment attention, which tracks the local
      unemployment rate, and worse local conditions went with relative movement away
      from the Democratic candidate.

Checks.
  1. Partial correlation: residualise both the index and the target on previous two-party
     share within each year, then correlate. If the negative relation vanishes -> (a).
  2. The same for each topic separately, so the carrier is visible.
  3. Correlation of each topic with previous share, to see which topics are partisanship proxies.

Input : data/processed/party_index.csv, data/processed/features.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
pi = pd.read_csv(ROOT / "data/processed/party_index.csv")
f = pd.read_csv(ROOT / "data/processed/features.csv")
df = pi.merge(f.drop(columns=["swing"]), on=["year", "state_po"])
TOPICS = ["x_unemployment", "x_health_insurance", "x_climate_change", "x_tax", "x_crime"]


def resid(y, x):
    """Residual of y after a straight-line fit on x (within one year)."""
    X = np.column_stack([np.ones(len(x)), x])
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ b


def corr_by_year(a, b, partial_on=None):
    out = {}
    for y, g in df.groupby("year"):
        u, v = g[a].values, g[b].values
        if partial_on is not None:
            z = g[partial_on].values
            u, v = resid(u, z), resid(v, z)
        out[y] = np.corrcoef(u, v)[0, 1]
    return out


def show(label, r):
    print(f"   {label:<34} " + "  ".join(f"{y}: {v:+.2f}" for y, v in r.items()) + f"   mean {np.mean(list(r.values())):+.3f}")


print("1. INDEX vs DEVIATION, raw and partialling out previous two-party share")
show("raw", corr_by_year("A", "d"))
show("partial on prior share", corr_by_year("A", "d", "dem_share_2p_prev"))

print("\n2. EACH TOPIC vs DEVIATION (sign as in the index), raw -> partial")
for c in TOPICS:
    show(c[2:] + " raw", corr_by_year(c, "d"))
    show(c[2:] + " partial", corr_by_year(c, "d", "dem_share_2p_prev"))

print("\n3. EACH TOPIC vs PREVIOUS SHARE (is the topic a partisanship proxy?)")
for c in TOPICS:
    show(c[2:], corr_by_year(c, "dem_share_2p_prev"))

print("\n4. PREVIOUS SHARE vs DEVIATION (do blue states move differently from the rest?)")
show("prior share", corr_by_year("dem_share_2p_prev", "d"))
