# ---------------------------------------------------------------------------
# globaltrends, setup check: set up the Research API backend and run ONE small test.
#
# Purpose: collect the same topics through the globaltrends package (Puhr & Müllner
# 2021) so its control-basket search scores can be compared with the one-term-per-
# request maps of the direct API path.
#
# Requirements: a conda environment with the Google API client, created once with
#   conda create -n gtrends python=3.11 google-api-python-client -c conda-forge
# (its path is shown by `conda env list`), and a Google Trends Research API key.
# The script prompts for both; the key is read without echo and never stored.
#
# Run in an R session with the repository root as working directory:
#   source("src/globaltrends_check.R")
# ---------------------------------------------------------------------------

need <- c("RSQLite", "zoo", "reticulate", "dplyr", "remotes")
for (p in need) if (!requireNamespace(p, quietly = TRUE)) install.packages(p)
# The Research API backend (initialize_python) is only in the GitHub version, not CRAN 0.0.14.
if (!requireNamespace("globaltrends", quietly = TRUE) ||
    !"initialize_python" %in% getNamespaceExports("globaltrends")) {
  remotes::install_github("ha-pu/globaltrends", upgrade = "never")
}
library(globaltrends); library(dplyr)
cat("globaltrends version:", as.character(packageVersion("globaltrends")), "\n")
stopifnot("initialize_python" %in% getNamespaceExports("globaltrends"))

CONDA_ENV <- readline("Path of the conda environment: ")
api_key   <- if (requireNamespace("getPass", quietly = TRUE)) getPass::getPass("API key: ") else readline("API key: ")

# --- Database: one SQLite file under data/private (git-ignored). -----------------------
dir.create("data/private/globaltrends_v2", showWarnings = FALSE, recursive = TRUE)
setwd("data/private/globaltrends_v2")
if (!file.exists("db.sqlite")) initialize_db()
start_db()
setwd("../../..")

# --- Research API backend. -------------------------------------------------------------
initialize_python(api_key = api_key, conda_env = CONDA_ENV)
rm(api_key)

# --- Locations shipped with the package. -------------------------------------------------
cat("\nus_states available in the package:", length(globaltrends::us_states), "\n")
print(head(globaltrends::us_states, 6))

# --- Control basket: the package default. ------------------------------------------------
ctrl <- add_control_keyword(keyword = c("gmail", "map", "translate", "wikipedia", "youtube"))
cat("control batch id:", ctrl, "\n")

# --- One object for the test: the health insurance entity. -------------------------------
obj <- add_object_keyword(keyword = "/m/02gqxg")
cat("object batch id:", obj, "\n")

# --- Download and score for five states over the package's default window. -------------
test_locs <- c("US-NV", "US-VT", "US-TX", "US-CA", "US-WY")
cat("\nDownloading control for 5 states ...\n")
download_control(control = ctrl, locations = test_locs)
cat("Downloading object for 5 states ...\n")
download_object(object = obj, control = ctrl, locations = test_locs)

compute_score(control = ctrl, object = obj, locations = test_locs)
out <- export_score(keyword = "/m/02gqxg")
cat("\nexport_score rows:", nrow(out), "\n")
print(head(out, 12))
cat("\ndate range:", as.character(min(out$date)), "to", as.character(max(out$date)), "\n")
cat("columns:", paste(names(out), collapse = ", "), "\n")

disconnect_db()
cat("\nSetup check complete. Expected: 660 rows (5 states x 132 months). Next: src/globaltrends_collect.R\n")
