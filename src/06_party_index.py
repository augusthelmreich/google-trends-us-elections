"""
Party-weighted issue-attention index: the test specified in docs/PREREG_party_index.md.

Implements §4-§7 of the plan and nothing else.

  index   A(s,t) = sum_i own_i * x(s,i,t) / sd_t(x(.,i,t))        (§4; secondary: unstandardised)
  target  d(s,t) = swing(s,t) - mean_s swing(.,t)                 (§5)
  test    r_t = corr(A, d) within each election; statistic r_bar = mean of the five r_t;
          one-sided permutation p (A shuffled across states within year, 10,000 draws)  (§6)
  robustness: drop Utah 2016; vote-weighted correlation; leave-one-topic-out;
          survey-weighted index if data/raw/ownership_polls.csv exists               (§7)

Input : data/processed/features.csv, data/processed/elections.csv, data/raw/topics.csv
Output: data/processed/party_index.csv (A and d per state-election)
        data/processed/party_index_result.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import os

# FEATURE_SET selects the feature table: "" (default) = main path from the globaltrends package,
# "api" = direct-API path from robustness/features_api.py. Outputs carry the same suffix.
SET = os.environ.get("FEATURE_SET", "")
SFX = f"_{SET}" if SET else ""
f = pd.read_csv(ROOT / f"data/processed/features{SFX}.csv")
e = pd.read_csv(ROOT / "data/processed/elections.csv")[["year", "state_po", "total_votes"]]
topics = pd.read_csv(ROOT / "data/raw/topics.csv")

N_PERM, SEED = 10000, 20261012
YEARS = sorted(f.year.unique())

# ---- §3 topics and signs: issue rows with a nonzero sign, core or extended, present in features
own = (topics[(topics.kind == "issue") & topics.set.isin(["core", "extended"])]
       .assign(col=lambda d: "x_" + d["name"].str.replace(" ", "_"))
       .set_index("col")["own_sign"].astype(float))
own = own[(own != 0) & own.index.isin(f.columns)]
# immigration fails the coverage rule in every year (24 zero states in 2008): excluded per plan
own = own.drop("x_immigration", errors="ignore")
TOPICS = list(own.index)
print("topics and signs:", {c[2:]: int(s) for c, s in own.items()})

f = f.merge(e, on=["year", "state_po"])
f["d"] = f.swing - f.groupby("year").swing.transform("mean")                       # §5


def build_index(df, cols, signs, standardise=True):
    a = np.zeros(len(df))
    for c in cols:
        x = df[c].values
        scale = df.groupby("year")[c].transform("std").values if standardise else 1.0
        a = a + signs[c] * x / scale
    return a


def r_by_year(df, a_col="A", weighted=False):
    out = {}
    for y, g in df.groupby("year"):
        if weighted:
            w = g.total_votes.values / g.total_votes.sum()
            ma, md = np.sum(w * g[a_col]), np.sum(w * g.d)
            cov = np.sum(w * (g[a_col] - ma) * (g.d - md))
            out[y] = cov / np.sqrt(np.sum(w * (g[a_col] - ma) ** 2) * np.sum(w * (g.d - md) ** 2))
        else:
            out[y] = np.corrcoef(g[a_col], g.d)[0, 1]
    return out


def perm_p(df, a_col, observed, rng, n=N_PERM):
    """Share of within-year shuffles of A whose mean correlation >= observed."""
    df = df.reset_index(drop=True)                      # positions, not labels (matters after filtering rows)
    idx_by_year = {y: np.array(ix) for y, ix in df.groupby("year").groups.items()}
    d = df.d.values; a = df[a_col].values
    count = 0
    for _ in range(n):
        a_s = a.copy()
        for y, ix in idx_by_year.items():
            a_s[ix] = a[rng.permutation(ix)]
        rs = [np.corrcoef(a_s[ix], d[ix])[0, 1] for ix in idx_by_year.values()]
        count += np.mean(rs) >= observed
    return count / n


# ---- §4 / §6 confirmatory ------------------------------------------------------------------
f["A"] = build_index(f, TOPICS, own, standardise=True)
f["A_raw"] = build_index(f, TOPICS, own, standardise=False)
assert np.allclose(f.groupby("year").A.mean(), 0) and np.allclose(f.groupby("year").d.mean(), 0)

rng = np.random.default_rng(SEED)
r = r_by_year(f, "A"); rbar = np.mean(list(r.values()))
p = perm_p(f, "A", rbar, rng)
rows = [dict(test="confirmatory (standardised index)", r_bar=rbar, p_one_sided=p,
             n_years_positive=sum(v > 0 for v in r.values()), **{f"r_{y}": v for y, v in r.items()})]

print("\nCONFIRMATORY TEST  r_t = corr(index, deviation from national swing)")
for y, v in r.items():
    print(f"   {y}: r = {v:+.3f}")
print(f"   mean r = {rbar:+.4f}   permutation p (one-sided, {N_PERM} draws) = {p:.4f}")
print("   success criterion: mean r > 0 and p < 0.05  ->", "SUPPORTED" if (rbar > 0 and p < 0.05) else "NOT SUPPORTED")

# ---- secondary and §7 robustness ------------------------------------------------------------
def add(name, df, a_col, weighted=False):
    rr = r_by_year(df, a_col, weighted); rb = np.mean(list(rr.values()))
    rows.append(dict(test=name, r_bar=rb, p_one_sided=perm_p(df, a_col, rb, rng, n=2000) if not weighted else np.nan,
                     n_years_positive=sum(v > 0 for v in rr.values()), **{f"r_{y}": v for y, v in rr.items()}))
    print(f"   {name:<40} mean r = {rb:+.4f}   years>0: {sum(v > 0 for v in rr.values())}/5")

print("\nSECONDARY / ROBUSTNESS (p from 2000 draws where computed)")
add("unstandardised index", f, "A_raw")
sp = f.groupby("year")[["A", "d"]].corr(method="spearman").xs("A", level=1)["d"]
rows.append(dict(test="spearman (standardised)", r_bar=sp.mean(), p_one_sided=np.nan,
                 n_years_positive=int((sp > 0).sum()), **{f"r_{y}": v for y, v in sp.items()}))
print(f"   {'spearman':<40} mean r = {sp.mean():+.4f}   years>0: {int((sp > 0).sum())}/5")
add("drop Utah 2016", f[~((f.year == 2016) & (f.state_po == "UT"))], "A")
add("vote-weighted correlation", f, "A", weighted=True)
for c in TOPICS:
    rest = [t for t in TOPICS if t != c]
    f[f"A_wo_{c}"] = build_index(f, rest, own, True)
    add(f"leave out {c[2:]}", f, f"A_wo_{c}")

polls = ROOT / "data/raw/ownership_polls.csv"
if polls.exists():
    print("   survey-weighted index: data/raw/ownership_polls.csv found -- not yet implemented, see plan §7.4")
else:
    print("   survey-weighted index: skipped (no data/raw/ownership_polls.csv)")

f[["year", "state_po", "swing", "d", "A", "A_raw"]].to_csv(ROOT / f"data/processed/party_index{SFX}.csv", index=False)
pd.DataFrame(rows).to_csv(ROOT / f"data/processed/party_index_result{SFX}.csv", index=False)
print(f"\nwrote data/processed/party_index{SFX}.csv and party_index_result{SFX}.csv")
