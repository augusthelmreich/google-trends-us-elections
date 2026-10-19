# Google Trends and US presidential elections

Does state-level Google search attention add information to forecasts of US presidential vote swing? Across the five elections from 2008 to 2024, it does not.

## Result

Search attention to issues (unemployment, health insurance, tax) and to the two nominees, measured as Google Trends state maps for August–September of each election year, was added to a regression that already knows each state's previous result. Three chronological tests (train before 2016, 2020, 2024; test on that year) give near-ties with the baseline on mean absolute error. Most of that error, however, is the national swing, which a state-level feature cannot address. On the part it can address, the deviation of each state from the national swing, every search feature increased the error in every test year:

| Change in geographic MAE vs. baseline (pp; negative = worse) | Issues | Candidates | Combined |
|---|---|---|---|
| 2016 | −0.012 | −0.502 | −0.422 |
| 2020 | −0.034 | −0.050 | −0.074 |
| 2024 | −0.117 | −0.012 | −0.087 |

A permutation test (features shuffled across states within each year, 1,000 draws) shows the issue features are indistinguishable from random columns (pooled percentile 41). The candidate contrast is worse than every random draw: the relation between relative candidate attention and swing reverses between elections, so learning it from past elections misleads.

**Issue ownership, tested directly.** A second test weights five issues by the party that owns them in the political-science literature (health insurance, unemployment and climate change Democratic; tax and crime Republican; signs from Egan 2013 and Fagan 2019) and asks whether states whose attention leans toward Democratic-owned issues swing relatively more Democratic. Across the five elections the mean correlation with the deviation from national swing is −0.16 (permutation p = 0.995): the relation runs opposite to the prediction in four of five elections and survives every pre-specified robustness check. The plan, test and result are in `docs/PREREG_party_index.md`. Leave-one-out shows the negative relation is carried mainly by unemployment attention, whose state map tracks the unemployment rate rather than political interest.

**What the instrument measures.** Three findings about the data itself. The 2020 unemployment map tracks the unemployment rate (Nevada, Kentucky, New Jersey, Michigan on top). Nominee maps peak in battleground states rather than home states, so candidate search measures where the campaign is being fought. And issue search geography has become partisan geography: every issue topic except crime correlates increasingly with a state's prior Democratic share (climate change: −0.02 in 2008, +0.71 in 2020), so at state level "attention to an issue" and "how blue the state is" can no longer be separated. An exploratory check that controls for prior partisanship (`src/08_exploratory.py`) leaves the unemployment relation unchanged and turns climate change mildly positive in 2020 and 2024; that is one topic in two elections and is proposed as a hypothesis, not a result.

## Design

- **Outcome.** Democratic share of the two-party vote in each of the 50 states and DC, and its change since the previous election (the swing). Source: MIT Election Data and Science Lab, *U.S. President 1976–2024*.
- **Features.** Google Trends Research API, `regions.list`: one state map per topic and election, August–September. Each map is divided by its own mean and centred, so features compare states within an election and are unaffected by Google's per-request rescaling. A topic is used only if no state is below Google's reporting threshold in any training year. Topic IDs, ownership signs and their sources are in `data/raw/topics.csv`; every ID was validated by the geography of its map before use.
- **Models.** Ordinary least squares on previous share, with and without the search features. Nothing more complex: with five elections, the national component is learned from two to four data points.
- **Evaluation.** Chronological folds only. MAE and RMSE, plus the split of each error into a national part (mean error) and a geographic part (spread across states), and the MAE on the geographic part alone.

## Running it

```
pip install -r requirements.txt
cp .env.example .env          # add your Google Trends Research API key
python src/01_elections.py    # outcome table from the MIT file
python src/02_baselines.py    # no-swing, historical OLS, oracle tide
python src/03_trends_api.py   # API collector + instrument checks (needs the key)
python src/04_features.py     # topic audit and feature construction (needs the key)
python src/05_evaluate.py     # models, metrics, decomposition
python src/06_permutation.py  # permutation test
python src/07_party_index.py  # party-weighted issue index (pre-specified test)
python src/08_exploratory.py  # exploratory partial correlations
```

API responses are cached under `data/private/` after the first run; scripts 05 to 08 run offline.

## Data

See `data/README.md`. The election results are public and included. Raw Google Trends API responses are not committed, as Google's terms for the Research API describe them as non-transferable; the collector caches them locally and the derived tables can be regenerated with a key.

## Decisions

Every methodological choice and its reason is logged in `docs/DECISIONS.md`.

## Context

Interdisciplinary Project in Data Science (5 ECTS), TU Wien. Supervisors: Jakob Müllner (WU Vienna), Allan Hanbury (TU Wien).
