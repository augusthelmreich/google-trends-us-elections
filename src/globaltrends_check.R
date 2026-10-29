# ---------------------------------------------------------------------------
# globaltrends, setup check: set up the Research API backend and run ONE small test.
#
# Purpose: collect the same topics through the supervisor's package (Puhr & Müllner
# 2021, globaltrends) so its control-basket search scores can be compared with the
# mean-normalised maps in data/processed/features.csv.
#
# Before running, in Terminal:
#   conda create -n gtrends python=3.11 google-api-python-client -c conda-forge
#   conda env list          # note the path printed for "gtrends"
# and have your API key ready; the script asks for it without echo.
#
# Run in R / RStudio with the repo folder as working directory:
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

CONDA_ENV <- readline("Path of the conda env (from `conda env list`, row 'gtrends'): ")
api_key   <- if (requireNamespace("getPass", quietly = TRUE)) getPass::getPass("API key: ") else readline("API key (will echo): ")

# --- database: one SQLite file in data/private (git-ignored) ---------------------
dir.create("data/private/globaltrends_v2", showWarnings = FALSE, recursive = TRUE)   # fresh db for the GitHub version
setwd("data/private/globaltrends_v2")
if (!file.exists("db.sqlite")) initialize_db()
start_db()
setwd("../../..")

# --- Research API backend --------------------------------------------------------
initialize_python(api_key = api_key, conda_env = CONDA_ENV)
rm(api_key)

# --- what the package knows about locations and time -------------------------------
cat("\nus_states available in the package:", length(globaltrends::us_states), "\n")
print(head(globaltrends::us_states, 6))

# --- control batch: the package's default basket ---------------------------------
ctrl <- add_control_keyword(keyword = c("gmail", "map", "translate", "wikipedia", "youtube"))
cat("control batch id:", ctrl, "\n")

# --- object batch: ONE topic for the test -----------------------------------------
obj <- add_object_keyword(keyword = "/m/02gqxg")      # health insurance
cat("object batch id:", obj, "\n")

# --- test download on a few states, one short period -------------------------------
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
cat("\nSetup check done. If the table above has 660 rows, run src/globaltrends_collect.R next.\n")
