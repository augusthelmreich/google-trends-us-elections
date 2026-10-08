"""
Google Trends as an instrument

Reusable part:
  fetch_regions(term, start, end)  -> DataFrame[state, value] for one term and one
                                      month window, via the Research API's regions.list.
                                      Raw JSON is cached in data/private/regions/ and
                                      never re-requested. Later scripts import this.

Demonstration part (python3 src/03_trends_api.py): five maps that show
  A  what a map looks like, and the geographic sanity check
  B  the same topic in a different window -> values change, ratios roughly hold
  C  a zero-heavy topic (immigration, Aug-Sep 2012) -> why it was excluded
  D  topic ID vs plain keyword for the same concept
  E  unemployment in Aug-Sep 2020 -> the COVID confound in plain sight

What a value means: the term's share of all searches in that state, divided by the
same share in the top state, times 100, rounded to an integer. Comparable across
states WITHIN one request; not comparable across requests. 0 = below Google's
reporting threshold, not "no searches".

Key, in order of precedence: GOOGLE_TRENDS_API_KEY in the shell; .env (git-ignored);
otherwise a hidden prompt when run interactively. Never written to disk by this code.
"""
from __future__ import annotations

import getpass
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/private/regions"
BASE = "https://www.googleapis.com/trends/v1beta/regions"


def _api_key() -> str:
    key = os.environ.get("GOOGLE_TRENDS_API_KEY")
    if not key and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("GOOGLE_TRENDS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key and sys.stdin.isatty():                           # interactive: ask, hidden
        key = getpass.getpass("Google Trends API key (hidden): ").strip()
    if not key:
        raise SystemExit("No API key: export GOOGLE_TRENDS_API_KEY, create .env, or run interactively")
    os.environ["GOOGLE_TRENDS_API_KEY"] = key                     # ask once per process
    return key


def fetch_regions(term: str, start: str, end: str, geo: str = "US") -> pd.DataFrame:
    """One state map. start/end are 'YYYY-MM'. Cached by request parameters."""
    params = {"term": term, "restrictions.geo": geo,
              "restrictions.startDate": start, "restrictions.endDate": end}
    digest = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{digest}.json"

    if path.exists():
        payload = json.loads(path.read_text())
    else:
        url = BASE + "?" + urllib.parse.urlencode({**params, "key": _api_key()})
        with urllib.request.urlopen(url, timeout=60) as r:       # one HTTPS GET
            body = json.load(r)
        payload = {"request": params,                             # the key is NOT stored
                   "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "response": body}
        path.write_text(json.dumps(payload, indent=1))
        time.sleep(1.0)                                            # be polite to the quota

    rows = payload["response"].get("regions", [])
    df = pd.DataFrame({"state": [r["regionCode"].replace("US-", "") for r in rows],
                       "state_name": [r["regionName"] for r in rows],
                       "value": [r.get("value", 0) for r in rows]})
    assert len(df) == 51, f"{term} {start}..{end}: expected 51 regions, got {len(df)}"
    return df.sort_values("value", ascending=False).reset_index(drop=True)


def describe(df: pd.DataFrame, label: str) -> None:
    top = ", ".join(f"{s} {v}" for s, v in df.head(5)[["state", "value"]].values)
    bot = ", ".join(f"{s} {v}" for s, v in df.tail(5)[["state", "value"]].values)
    print(f"{label}\n   top5: {top}\n   bottom5: {bot}\n   zeros: {(df.value == 0).sum()}   "
          f"mean: {df.value.mean():.1f}   min>0: {df.value[df.value > 0].min()}")


if __name__ == "__main__":
    TOPICS = {"health insurance": "/m/02gqxg", "immigration": "/m/03wn_", "unemployment": "/m/07s_c"}
    maps = []

    def pull(term, start, end, label):
        df = fetch_regions(term, start, end)
        maps.append(df.assign(label=label, term=term, start=start, end=end))
        return df

    print("A  health insurance topic, Feb 2020")
    a = pull(TOPICS["health insurance"], "2020-02", "2020-02", "A_hi_2020-02")
    describe(a, "   ")

    print("\nB  same topic, Jan-Mar 2020 -- values change; does the ORDER of states hold?")
    b = pull(TOPICS["health insurance"], "2020-01", "2020-03", "B_hi_2020-01..03")
    describe(b, "   ")
    ab = a.merge(b, on="state", suffixes=("_a", "_b"))
    print(f"   correlation of A vs B across states: {ab.value_a.corr(ab.value_b):.3f}")

    print("\nC  immigration topic, Aug-Sep 2012 -- the zero problem")
    c = pull(TOPICS["immigration"], "2012-08", "2012-09", "C_imm_2012-08..09")
    describe(c, "   ")
    print("   zero states:", ", ".join(c[c.value == 0].state))

    print("\nD  'health insurance' as a plain KEYWORD, Feb 2020 -- vs the topic in A")
    d = pull("health insurance", "2020-02", "2020-02", "D_hi_keyword_2020-02")
    describe(d, "   ")
    ad = a.merge(d, on="state", suffixes=("_topic", "_kw"))
    print(f"   correlation topic vs keyword: {ad.value_topic.corr(ad.value_kw):.3f}")

    print("\nE  unemployment topic, Aug-Sep 2020 -- what is this measuring?")
    e = pull(TOPICS["unemployment"], "2020-08", "2020-09", "E_unemp_2020-08..09")
    describe(e, "   ")

    out = ROOT / "data/processed/trends_station4.csv"
    pd.concat(maps).to_csv(out, index=False)
    print(f"\nwrote {out.relative_to(ROOT)}  ({sum(len(m) for m in maps)} rows, 5 maps)")
    print(f"raw responses cached in {CACHE.relative_to(ROOT)}/ (git-ignored)")
