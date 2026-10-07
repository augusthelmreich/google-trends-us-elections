"""
Station 2 -- Build the outcome table from the MIT election file.

Input : data/raw/1976-2024-president.csv   (MIT Election Lab, public)
Output: data/processed/elections.csv       one row per state x election, 2008-2024

Columns written:
  year, state_po, dem_votes, rep_votes, total_votes,
  dem_share_all   = Dem votes / all votes           (for reference only)
  dem_share_2p    = Dem votes / (Dem + Rep votes)   <- the share we model
  dem_share_2p_prev, swing = dem_share_2p - dem_share_2p_prev   <- the target

Three notes on the source file.:
  1. Fusion voting: the same nominee appears under several party labels
     (e.g. Clinton 2016 under DEMOCRAT, WORKING FAMILIES, WOMEN'S EQUALITY).
     -> aggregate by CANDIDATE NAME, never by party label.
  2. totalvotes is repeated on every candidate row of a state-year.
     -> take it once per state-year and check it is identical across rows.
  3. Unnamed write-ins (candidate "OTHER" or blank) labelled Democrat/Republican cannot
     be attributed to a nominee. -> excluded; listed in the output so the exclusion is visible.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/1976-2024-president.csv"
OUT = ROOT / "data/processed/elections.csv"

FIRST_MODELLED_YEAR = 2008      # 2004 is loaded only to give 2008 its "previous share"
YEARS = list(range(2004, 2025, 4))

d = pd.read_csv(RAW)
d = d[d.year.isin(YEARS)].copy()

# ---- 1. identify each year's nominees by national vote under the simplified party label
nominee = {}
for y in YEARS:
    for party in ("DEMOCRAT", "REPUBLICAN"):
        s = d[(d.year == y) & (d.party_simplified == party) & (d.candidate != "OTHER")]
        nominee[(y, party)] = s.groupby("candidate").candidatevotes.sum().idxmax()
    print(f"{y}: D = {nominee[(y, 'DEMOCRAT')]:<22} R = {nominee[(y, 'REPUBLICAN')]}")

# ---- 2. sum ALL rows for that candidate name in each state (handles fusion voting)
rows = []
for y in YEARS:
    dy = d[d.year == y]
    dem, rep = nominee[(y, "DEMOCRAT")], nominee[(y, "REPUBLICAN")]
    for st, g in dy.groupby("state_po"):
        totals = g.totalvotes.unique()
        assert len(totals) == 1, f"{y} {st}: totalvotes differs across rows: {totals}"
        rows.append(dict(
            year=y, state_po=st,
            dem_votes=int(g.loc[g.candidate == dem, "candidatevotes"].sum()),
            rep_votes=int(g.loc[g.candidate == rep, "candidatevotes"].sum()),
            total_votes=int(totals[0]),
            # write-ins recorded as "OTHER" but labelled Democrat/Republican: could belong to the
            # nominee, but the file does not say so -- excluded, counted here
            unattributed_writein=int(g.loc[(g.candidate.isna() | (g.candidate == "OTHER")) &
                                           g.party_simplified.isin(["DEMOCRAT", "REPUBLICAN"]),
                                           "candidatevotes"].sum()),
        ))
e = pd.DataFrame(rows)

# ---- 3. checks: 51 jurisdictions, both nominees present, votes consistent
for y in YEARS:
    ey = e[e.year == y]
    assert len(ey) == 51, f"{y}: expected 51 jurisdictions, got {len(ey)}"
    assert (ey.dem_votes > 0).all() and (ey.rep_votes > 0).all(), f"{y}: a nominee has 0 votes somewhere"
    assert (ey.dem_votes + ey.rep_votes <= ey.total_votes).all(), f"{y}: nominee votes exceed total"

# ---- 4. shares and the target
e["dem_share_all"] = 100 * e.dem_votes / e.total_votes
e["dem_share_2p"] = 100 * e.dem_votes / (e.dem_votes + e.rep_votes)
e = e.sort_values(["state_po", "year"])
e["dem_share_2p_prev"] = e.groupby("state_po").dem_share_2p.shift(1)
e["swing"] = e.dem_share_2p - e.dem_share_2p_prev
print("Dem/Rep-labelled write-ins that could not be attributed:",
      e[e.unattributed_writein > 0][["year", "state_po", "unattributed_writein"]].to_dict("records"))
e = e[e.year >= FIRST_MODELLED_YEAR].reset_index(drop=True)
assert e.swing.notna().all() and len(e) == 255

OUT.parent.mkdir(parents=True, exist_ok=True)
e.to_csv(OUT, index=False)

# ---- 5. what was built
print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(e)} rows)")
print("\nswing (pp) by election -- compare with the report:")
print(e.groupby("year").swing.agg(["mean", "median", "min", "max"]).round(3).to_string())
print("\nlargest |swing| rows (sanity check -- Utah 2016 is the two-party artefact):")
print(e.reindex(e.swing.abs().sort_values(ascending=False).index)
        .head(5)[["year", "state_po", "dem_share_all", "dem_share_2p", "swing"]].round(2).to_string(index=False))
