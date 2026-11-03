# Google Trends and US presidential elections

Does state-level Google search attention add information to forecasts of US presidential vote swing? Across the five elections from 2008 to 2024, the search features tested here did not improve state-level forecasts, and in one election made them markedly worse, because the relation between a topic's geography and the swing reversed between elections. A theory-driven test of issue ownership shows no relation with either data source.

## Result

Search attention to six issues (unemployment, health insurance, tax, immigration, climate change, crime) and to the two nominees, measured for each state over August–September of the election year, was added to a regression that already knows each state's previous result. Three chronological tests (train before 2016, 2020, 2024; test on that year) give a small gain in 2016, a clear loss in 2020 and a near-tie in 2024 on mean absolute error (issues vs baseline: 4.11 vs 4.29 pp; 2.17 vs 1.64; 2.80 vs 2.83). Most of that error is the year's mean state-level swing, which a state-level feature cannot address. The part it can address is each state's deviation from that mean; the table reports the change in MAE on that part (geographic MAE, `geo_mae` in the code), a diagnostic that isolates what a state feature could contribute, for both data sources:

| Change in geographic MAE vs. baseline (pp; positive = better) | Issues | Candidates | Combined |
|---|---|---|---|
| 2016, `globaltrends` scores | +0.054 | −0.709 | −0.681 |
| 2020, `globaltrends` scores | −0.842 | −0.026 | −0.890 |
| 2024, `globaltrends` scores | −0.019 | −0.006 | −0.015 |
| 2016, direct API maps | −0.142 | −0.502 | −0.523 |
| 2020, direct API maps | −0.764 | −0.050 | −0.813 |
| 2024, direct API maps | −0.203 | −0.012 | −0.245 |

A shuffle benchmark (features permuted across states within each year, 10,000 draws) puts the issue features below 98.5% of random columns pooled over the three years on the package path and below 99.96% on the direct-API path. The 2020 loss has one source: trained on 2008–2016, the model learned that states with high immigration attention swing Democratic (coefficient +6.5), because the immigrant-heavy states did so in 2016; in 2020 those same states swung Republican relative to the rest, and the model was pulled the wrong way. The candidate contrast fails the same way in 2016, worse than every random draw on both paths. A relation between a search map and the swing can reverse between elections, so learning it from past elections misleads. The fitted signs match the ownership coding for climate change and crime and contradict it for tax, health insurance and immigration.

**Issue ownership, tested directly.** A second test weights five issues by the party that owns them in the political-science literature (health insurance and climate change Democratic; tax, crime and immigration Republican; one coding, each sign backed by at least two of Egan 2013, Fagan 2021 and Noble 2025) and asks whether states whose attention leans toward Democratic-owned issues swing relatively more Democratic. Across the five elections the mean correlation with the deviation from mean swing is −0.07 with the `globaltrends` scores and −0.05 with the direct API maps (two of five elections positive; permutation p = 0.86 and 0.79): no relation. A side-balanced variant that weights the two parties' topics equally gives −0.08 on both. Unemployment is not in the index because the sources code *jobs* Democratic but *the economy* Republican, so its sign is undetermined; it stays in the forecasting models, where it is the best-validated topic. The documented analysis plan, test and result are in `docs/PREREG_party_index.md`; an earlier specification of the index that included unemployment (mean r = −0.16, carried entirely by that topic) is recorded there as the first result.

**Two normalisations of the same data.** The package divides a state's topic searches by its searches for a fixed control basket (gmail, map, translate, wikipedia, youtube); the direct API maps are Google's own share-of-all-searches figures. After the same centring step, the two agree closely for unemployment (r = 0.90–0.95 across states in every year) and loosely for the topics with little geographic signal (crime 0.27–0.81, health insurance 0.42–0.78; mean over all topic-years 0.75). The package also keeps years on one scale, which the per-request maps cannot: its unemployment score in August–September 2020 is six to ten times its level in any other election year. Coverage depends on entity size: the narrow entity "Immigration to the United States" had 6–24 zero states in the direct maps and, scaled jointly with a control term, rounded to zero in all 51 states in the package; the broad "Immigration" entity has no zero state on either path and agrees between them at r = 0.72–0.92.

**What the instrument measures.** The unemployment map tracks the unemployment rate (2020, direct map: Nevada, Kentucky, New Jersey, Michigan on top). Nominee maps peak in battleground states rather than home states, so candidate search measures where the campaign is being fought. And issue search geography has become partisan geography: climate change attention correlates with a state's prior Democratic share at +0.03 in 2008 and +0.63 in 2020 (package scores; +0.71 on the direct maps), so at state level "attention to an issue" and "how blue the state is" are hard to separate. An exploratory check that controls for prior partisanship (`src/07_exploratory.py`) leaves the unemployment relation unchanged and turns climate change mildly positive in 2020 and 2024; that is one topic in two elections and is proposed as a hypothesis, not a result.

## Design

- **Outcome.** Democratic share of the two-party vote in each of the 50 states and DC, and its change since the previous election (the swing). Source: MIT Election Data and Science Lab, *U.S. President 1976–2024*.
- **Search data.** Collected and scored with the `globaltrends` R package (Puhr & Müllner 2021; GitHub version 0.2.1), which queries the Google Trends Research API and normalises each topic by a control basket per state and month. Monthly scores for August and September of each election year are averaged, then each map is divided by its mean across states and centred, so features compare states within an election. One topic dictionary serves both tests: six issue topics chosen from the issue-ownership literature, each validated by the geography of its map and used only if no state is below Google's reporting threshold in any training year. Four further candidates (a health-care entity, Social Security, the national debt, foreign policy) were checked the same way and rejected; the tools are in `src/dictionary/` and the reasons in the dictionary. Topic IDs, ownership signs and their sources are in `data/raw/topics.csv`; every ID was checked by the geography of its map before use. The same features built from one-term-per-request API maps are kept as a robustness path (`src/robustness/`).
- **Models.** Ordinary least squares on previous share, with and without the search features. Nothing more complex: with five elections, the year-level component is learned from two to four data points.
- **Evaluation.** Chronological folds only (model fitting never sees the test year). Note that topic entities were chosen by inspecting their maps across all five elections, so the test years informed the measurement design: this is a retrospective evaluation with chronological training, not a real-time forecast. MAE and RMSE, plus the split of each error into a mean part (the year's mean state-level miss) and a geographic part (spread across states), and the MAE on the geographic part alone as a diagnostic.

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

Scripts 04–07 accept `FEATURE_SET=api` to run on the direct-API features; see `src/robustness/README.md`. The two scripts in `src/dictionary/` are how topics were chosen: `topic_lookup.py` resolves a term to entity IDs, `check_topics.py` pulls a candidate's five maps and reports coverage, stability and geography against the written rule. The package database and the API cache live under `data/private/` and are not committed; everything from `03_features.py` on runs offline once they exist.

## Data

See `data/README.md`. The election results are public and included. Raw Google Trends data are not committed, as Google's terms for the Research API describe them as non-transferable; the derived tables can be regenerated with a key.

## Decisions

Every methodological choice and its reason is logged in `docs/DECISIONS.md`.

## Citation

Search data were collected and scored with the `globaltrends` package. Please cite:

Puhr, H., & Müllner, J. (2021). *Let me Google that for you: Capturing globalization using Google Trends.* SSRN Working Paper 3969013. https://doi.org/10.2139/ssrn.3969013

## Context

Interdisciplinary Project in Data Science (5 ECTS), TU Wien. Supervisors: Jakob Müllner (WU Vienna), Allan Hanbury (TU Wien).
