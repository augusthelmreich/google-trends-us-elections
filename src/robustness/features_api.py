"""
From state maps to features: the direct-API path (secondary).

The main feature table is built by src/03_features.py from the supervisors'
globaltrends package; this script builds the same table from one-term-per-request
regions.list maps, as a comparison and robustness path. Run the analysis scripts on it
with FEATURE_SET=api (e.g. FEATURE_SET=api python3 src/04_evaluate.py).

Inputs : data/raw/topics.csv            the issue dictionary and candidate IDs (hand-made)
         data/processed/elections.csv   from 01_elections.py
         Google Trends Research API     via fetch_regions() from robustness/trends_api.py (cached)
Outputs: data/processed/coverage_audit_api.csv  one row per (topic, year): zeros, min, max, mean
         data/processed/features_api.csv        one row per (year, state): issue features + candidate contrast

Window: August-September of each election year: a common
pre-election window with an information cutoff before October.

Feature definitions (fixed before any model is fitted):
  issue      x[s,k,t] = r[s,k,t] / mean_s(r[.,k,t]) - 1
             "how far this state's relative attention to issue k sits above/below the
             51-state mean", zero-mean within each election, invariant to the per-request
             rescaling Google applies.
  candidate  c[s,t]   = xDem[s,t] - xRep[s,t]
             the Democratic nominee's relative attention minus the Republican's, each
             normalised against its own map (the two maps are NOT on a common scale).

Coverage rule (applied here per year for the audit; the evaluation
script applies it per training fold): a topic is eligible only if every state has a
strictly positive value. A zero is "below Google's threshold", not "no interest".
"""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

# load the collector by path so this script runs from any working directory
_spec = importlib.util.spec_from_file_location("trends_api", ROOT / "src/robustness/trends_api.py")
trends_api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trends_api)
fetch_regions = trends_api.fetch_regions

YEARS = [2008, 2012, 2016, 2020, 2024]
WINDOW = ("08", "09")                                   # Aug..Sep of the election year

topics = pd.read_csv(ROOT / "data/raw/topics.csv")
elections = pd.read_csv(ROOT / "data/processed/elections.csv")

# ---- 1. pull every map (issues x years, and each nominee in their year) ----------------
maps = []
for _, t in topics[(topics.kind == "issue") & (topics.set == "included")].iterrows():
    for y in YEARS:
        m = fetch_regions(t.term, f"{y}-{WINDOW[0]}", f"{y}-{WINDOW[1]}")
        maps.append(m.assign(name=t["name"], kind="issue", party=None, year=y))
for _, t in topics[(topics.kind == "candidate") & (topics.set == "included")].iterrows():
    y = int(t.year)
    m = fetch_regions(t.term, f"{y}-{WINDOW[0]}", f"{y}-{WINDOW[1]}")
    maps.append(m.assign(name=t["name"], kind="candidate", party=t.party, year=y))
maps = pd.concat(maps, ignore_index=True)
print(f"{maps[['name','year','kind']].drop_duplicates().shape[0]} maps, {len(maps)} rows")

# ---- 2. coverage audit --------------------------------------------------------------------
audit = (maps.groupby(["kind", "name", "party", "year"], dropna=False)["value"]
             .agg(zeros=lambda v: int((v == 0).sum()), min="min", max="max", mean="mean")
             .reset_index())
audit["eligible"] = audit.zeros == 0
audit.to_csv(ROOT / "data/processed/coverage_audit_api.csv", index=False)

print("\nCOVERAGE AUDIT  (zeros = states below Google's threshold)")
issues = audit[audit.kind == "issue"].pivot(index="name", columns="year", values="zeros")
print(issues.to_string())
print("\nissue mean value by year (low means rounding dominates):")
print(audit[audit.kind == "issue"].pivot(index="name", columns="year", values="mean").round(1).to_string())

# ---- 3. candidate sanity check: does the home state rank near the top? ------------------
print("\nCANDIDATE MAPS  home-state rank out of 51 (lower = more plausible)")
home = topics[topics.kind == "candidate"].set_index(["name", "year"]).home_state
for (name, party, y), g in maps[maps.kind == "candidate"].groupby(["name", "party", "year"]):
    g = g.sort_values("value", ascending=False).reset_index(drop=True)
    hs = home.get((name, y))
    rank = int(g.index[g.state == hs][0]) + 1 if hs in set(g.state) else None
    print(f"   {y} {party} {name:<8} home {hs}: rank {rank:>2}   top3 {', '.join(g.state.head(3))}   zeros {(g.value == 0).sum()}")

# ---- 4. features ----------------------------------------------------------------------------
maps["x"] = maps["value"] / maps.groupby(["name", "party", "year"], dropna=False)["value"].transform("mean") - 1
assert np.allclose(maps.groupby(["name", "party", "year"], dropna=False)["x"].mean(), 0)   # zero-mean by construction

issue_x = (maps[maps.kind == "issue"]
           .pivot(index=["year", "state"], columns="name", values="x")
           .rename(columns=lambda c: "x_" + c.replace(" ", "_"))
           .reset_index())

cand = maps[maps.kind == "candidate"].pivot(index=["year", "state"], columns="party", values="x").reset_index()
cand["cand_contrast"] = cand["D"] - cand["R"]
cand = cand[["year", "state", "cand_contrast"]]

features = (elections[["year", "state_po", "dem_share_2p_prev", "swing"]]
            .merge(issue_x, left_on=["year", "state_po"], right_on=["year", "state"], how="left")
            .merge(cand, on=["year", "state"], how="left")
            .drop(columns="state"))
assert len(features) == 255 and features.isna().sum().sum() == 0, features.isna().sum()
features.to_csv(ROOT / "data/processed/features_api.csv", index=False)

print(f"\nwrote data/processed/features_api.csv  ({len(features)} rows)")
print(features.drop(columns=["state_po"]).groupby("year").std().round(3).to_string())
print("\n(std of each feature by year: how much geographic variation there is to work with)")
