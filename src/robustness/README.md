# Robustness path: direct API maps

The main pipeline builds its features from the `globaltrends` package
(`src/globaltrends_stage2.R` -> `src/03_features.py`). This folder holds the
other way of getting the same maps, used only to check that the results do not
depend on the package's control-basket normalisation:

- `trends_api.py`: one `regions.list` request per topic and window against the
  Google Trends Research API, cached under `data/private/` (needs the key).
- `features_api.py`: the same feature construction as `03_features.py`, from those
  maps; writes `features_api.csv` and `coverage_audit_api.csv`.

`03_features.py` reports the agreement between the two feature tables per topic
and year. To run the analysis on this path:

    python3 src/robustness/features_api.py
    FEATURE_SET=api python3 src/04_evaluate.py
    FEATURE_SET=api python3 src/05_permutation.py
    FEATURE_SET=api python3 src/06_party_index.py
    FEATURE_SET=api python3 src/07_exploratory.py

Outputs carry the suffix `_api` (`results_api.csv`, `party_index_result_api.csv`, ...).
