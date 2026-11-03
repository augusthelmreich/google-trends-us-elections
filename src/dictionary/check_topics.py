"""
Validate candidate topics before they enter the dictionary.

For each candidate, pull the Aug-Sep state map of every election year through the
direct-API collector and report what the dictionary rule asks for:
  zeros            states below Google's threshold (coverage rule: none in training years)
  top / bottom     does the geography look like the issue, or like something else?
  stability        correlation of the map with the previous election's map
  r_prior_share    correlation with the state's prior Democratic two-party share
  r_existing       correlation with the current topic it would replace (same x transform)

Usage (needs GOOGLE_TRENDS_API_KEY in .env or the environment):
    python3 src/dictionary/check_topics.py "health care=/m/XXXXX" "immigration=/m/YYYYY"
Optionally name the existing feature to compare with:
    python3 src/dictionary/check_topics.py "health care=/m/XXXXX:x_health_insurance"
Writes data/processed/topic_check_<labels>.csv, named after the candidates checked.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("trends_api", ROOT / "src/robustness/trends_api.py")
trends_api = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(trends_api)
fetch_regions = trends_api.fetch_regions

YEARS = [2008, 2012, 2016, 2020, 2024]
elections = pd.read_csv(ROOT / "data/processed/elections.csv")[["year", "state_po", "dem_share_2p_prev"]]
feat = pd.read_csv(ROOT / "data/processed/features_api.csv")

args = sys.argv[1:]
if not args:
    raise SystemExit(__doc__)

rows = []
for arg in args:
    label, rest = arg.split("=", 1)
    mid, _, existing = rest.partition(":")
    prev = None
    print(f"\n=== {label}  ({mid})" + (f"  vs {existing}" if existing else ""))
    for y in YEARS:
        m = fetch_regions(mid, f"{y}-08", f"{y}-09").sort_values("value", ascending=False)
        x = m.value / m.value.mean() - 1 if m.value.mean() > 0 else m.value * 0 - 1
        m = m.assign(x=x.values)
        d = m.merge(elections[elections.year == y], left_on="state", right_on="state_po")
        r_prior = np.corrcoef(d.x, d.dem_share_2p_prev)[0, 1] if d.x.std() > 0 else np.nan
        r_exist = np.nan
        if existing:
            e = feat[feat.year == y][["state_po", existing]]
            d2 = m.merge(e, left_on="state", right_on="state_po")
            r_exist = np.corrcoef(d2.x, d2[existing])[0, 1] if d2.x.std() > 0 else np.nan
        stab = np.nan
        if prev is not None:
            j = m[["state", "x"]].merge(prev, on="state", suffixes=("", "_prev"))
            stab = np.corrcoef(j.x, j.x_prev)[0, 1] if j.x.std() > 0 and j.x_prev.std() > 0 else np.nan
        prev = m[["state", "x"]]
        zeros = int((m.value == 0).sum())
        print(f"  {y}: zeros {zeros:>2}  mean {m.value.mean():5.1f}  "
              f"top {', '.join(m.state.head(5))}  |  bottom {', '.join(m.state.tail(5))}  "
              f"| stability {stab:+.2f}  r_prior {r_prior:+.2f}  r_existing {r_exist:+.2f}")
        rows.append(dict(label=label, mid=mid, year=y, zeros=zeros, mean=m.value.mean(), sd_x=m.x.std(),
                         top5=" ".join(m.state.head(5)), bottom5=" ".join(m.state.tail(5)),
                         stability=stab, r_prior_share=r_prior, r_existing=r_exist, existing=existing or ""))

out = pd.DataFrame(rows)
out.to_csv(ROOT / "data/processed/topic_check.csv", index=False)
print(f"\nwrote data/processed/topic_check.csv ({len(out)} rows)")
print("\nRule, written before looking: a topic enters if it has no zero state in 2008-2020 and a stable map;")
print("it replaces an existing topic only if it measures the same issue with clearly less non-political geography.")
