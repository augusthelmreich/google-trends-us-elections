# Google Trends and US presidential elections

Does state-level Google search attention add information to forecasts of US presidential vote swing? Across the five elections from 2008 to 2024, the search features tested here did not improve state-level forecasts, on either of two versions of the data. A theory-driven test of issue ownership is not supported on either version.

## Result

Search attention to five issues (unemployment, health insurance, tax, climate change, crime) and to the two nominees, measured for each state over August–September of the election year, was added to a regression that already knows each state's previous result. Three chronological tests (train before 2016, 2020, 2024; test on that year) give small losses or near-ties against the baseline on mean absolute error (2016: 4.34 vs 4.29 pp; 2020: 1.71 vs 1.64; 2024: 2.82 vs 2.83). Most of that error is the year's mean state-level swing, which a state-level feature cannot address. The part it can address is each state's deviation from that mean; the table reports the change in MAE on that part (geographic MAE, `geo_mae` in the code), a diagnostic that isolates what a state feature could contribute, on both data paths:

| Change in geographic MAE vs. baseline (pp; positive = better) | Issues | Candidates | Combined |
|---|---|---|---|
| 2016, package scores | −0.230 | −0.709 | −0.979 |
| 2020, package scores | +0.032 | −0.026 | +0.012 |
| 2024, package scores | +0.013 | −0.006 | +0.012 |
| 2016, direct API maps | −0.469 | −0.502 | −0.844 |
| 2020, direct API maps | −0.043 | −0.050 | −0.091 |
| 2024, direct API maps | −0.120 | −0.012 | −0.156 |

A shuffle benchmark (features permuted across states within each year, 10,000 draws) puts the package-path issue features at the 72nd percentile of random columns pooled over the three years: worse than 88% of random draws in 2016, where five coefficients are learned from two elections, and better than 96% and 93% in 2020 and 2024, where the training set is larger. On the direct-API path the same features are worse than random in every year (pooled 3rd percentile). The candidate contrast is worse than every random draw on both paths: the relation between relative candidate attention and swing reverses between elections, so learning it from past elections misleads. The fitted signs match the ownership coding for climate change and crime and contradict it for tax and health insurance.

**Issue ownership, tested directly.** A second test weights five issues by the party that owns them in the political-science literature (health insurance, unemployment and climate change Democratic; tax and crime Republican; one coding, with signs from Egan 2013 and Fagan 2019) and asks whether states whose attention leans toward Democratic-owned issues swing relatively more Democratic. Across the five elections the mean correlation with the deviation from mean swing is −0.16 on both data paths (permutation p ≈ 0.99): the relation runs opposite to the prediction in four of five elections and survives every pre-specified robustness check. The documented analysis plan, test and result are in `docs/PREREG_party_index.md`. Leave-one-out shows the negative relation is carried mainly by unemployment attention, whose state map tracks the unemployment rate rather than political interest.

**Two normalisations of the same data.** The package divides a state's topic searches by its searches for a fixed control basket (gmail, map, translate, wikipedia, youtube); the direct API maps are Google's own share-of-all-searches figures. After the same centring step, the two agree closely for unemployment (r = 0.90–0.95 across states in every year) and loosely for the topics with little geographic signal (crime 0.27–0.81, health insurance 0.42–0.78; mean over all topic-years 0.75). The package also keeps years on one scale, which the per-request maps cannot: its unemployment score in August–September 2020 is six to ten times its level in any other election year. The cost is coverage: scaled jointly with a control term, immigration rounds to zero in all 51 states in every year, whereas the direct maps have 6–24 zero states. Immigration is excluded on both paths.

**What the instrument measures.** The unemployment map tracks the unemployment rate (2020, direct map: Nevada, Kentucky, New Jersey, Michigan on top). Nominee maps peak in battleground states rather than home states, so candidate search measures where the campaign is being fought. And issue search geography has become partisan geography: climate change attention correlates with a state's prior Democratic share at +0.03 in 2008 and +0.63 in 2020 (package scores; +0.71 on the direct maps), so at state level "attention to an issue" and "how blue the state is" are hard to separate. An exploratory check that controls for prior partisanship (`src/07_exploratory.py`) leaves the unemployment relation unchanged and turns climate change mildly positive in 2020 and 2024; that is one topic in two elections and is proposed as a hypothesis, not a result.

## Design

- **Outcome.** Democratic share of the two-party vote in each of the 50 states and DC, and its change since the previous election (the swing). Source: MIT Election Data and Science Lab, *U.S. President 1976–2024*.
- **Search data.** Collected and scored with the `globaltrends` R package (Puhr & Müllner 2021; GitHub version 0.2.1), which queries the Google Trends Research API and normalises each topic by a control basket per state and month. Monthly scores for August and September of each election year are averaged, then each map is divided by its mean across states and centred, so features compare states within an election. One topic dictionary serves both tests: six issue topics chosen from the issue-ownership literature, of which a topic is used only if no state is below Google's reporting threshold in any training year (this removes immigration). Topic IDs, ownership signs and their sources are in `data/raw/topics.csv`; every ID was checked by the geography of its map before use. The same features built from one-term-per-request API maps are kept as a robustness path (`src/robustness/`).
- **Models.** Ordinary least squares on previous share, with and without the search features. Nothing more complex: with five elections, the year-level component is learned from two to four data points.
- **Evaluation.** Chronological folds only. MAE and RMSE, plus the split of each error into a mean part (the year's mean state-level miss) and a geographic part (spread across states), and the MAE on the geographic part alone as a diagnostic.

## Running it

Python 3.10+ with `pip install -r requirements.txt`; R 4.x with `globaltrends` from GitHub (`remotes::install_github("ha-pu/globaltrends")`) and a conda environment holding `google-api-python-client` for its API backend; a Google Trends Research API key, entered when the R scripts ask for it (never stored in the repo).

```
python src/01_elections.py              # outcome table from the MIT file
python src/02_baselines.py              # no-swing, historical OLS, oracle tide
# in an R session started at the repo root (the scripts prompt for the conda path and the key):
#   source("src/globaltrends_check.R")     # setup check: one topic, five states
#   source("src/globaltrends_collect.R")   # collection: all topics x 51 states, 2008-2024
python src/03_features.py               # package scores -> features, coverage audit, comparison with the API maps
python src/04_evaluate.py               # models, metrics, decomposition
python src/05_permutation.py            # shuffle benchmark
python src/06_party_index.py            # party-weighted issue index (pre-specified test)
python src/07_exploratory.py            # exploratory partial correlations
```

Scripts 04–07 accept `FEATURE_SET=api` to run on the direct-API features; see `src/robustness/README.md`. The package database and the API cache live under `data/private/` and are not committed; everything from `03_features.py` on runs offline once they exist.

## Data

See `data/README.md`. The election results are public and included. Raw Google Trends data are not committed, as Google's terms for the Research API describe them as non-transferable; the derived tables can be regenerated with a key.

## Decisions

Every methodological choice and its reason is logged in `docs/DECISIONS.md`.

## Citation

Search data were collected and scored with the `globaltrends` package. Please cite:

Puhr, H., & Müllner, J. (2021). *Let me Google that for you: Capturing globalization using Google Trends.* SSRN Working Paper 3969013. https://doi.org/10.2139/ssrn.3969013

## Context

Interdisciplinary Project in Data Science (5 ECTS), TU Wien. Supervisors: Jakob Müllner (WU Vienna), Allan Hanbury (TU Wien).
