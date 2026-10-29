# ---------------------------------------------------------------------------
# globaltrends, collection: all topics through the supervisors' package.
#
# All 51 jurisdictions, window 2008-01..2024-12 (monthly), control basket = the
# package default (gmail, map, translate, wikipedia, youtube), objects = the
# project's issue topics and nominee IDs from data/raw/topics.csv.
#
# Output: data/processed/globaltrends_scores.csv
#   one row per (keyword, location, year) with the mean of the August and
#   September search scores of that election year -- the package's control-basket
#   equivalent of the project's Aug-Sep state maps.
#
# Needs: the conda env from globaltrends_check.R and the API key. Run from the repo root:
#   source("src/globaltrends_collect.R")
# Takes roughly 30-60 minutes (about 700 requests, paced by the package).
# Safe to rerun: downloads already in the database are skipped by the package.
# ---------------------------------------------------------------------------
library(globaltrends); library(dplyr)
stopifnot(packageVersion("globaltrends") >= "0.2.0")

REPO <- getwd()
CONDA_ENV <- readline("Path of the conda env: ")
api_key   <- if (requireNamespace("getPass", quietly = TRUE)) getPass::getPass("API key: ") else readline("API key: ")

topics <- read.csv(file.path(REPO, "data/raw/topics.csv"), stringsAsFactors = FALSE)
issue_ids <- unique(topics$term[topics$kind == "issue" & topics$set == "included" & topics$term != ""])
cand_ids  <- unique(topics$term[topics$kind == "candidate"])
objects   <- c(issue_ids, cand_ids)
cat("objects to collect:", length(objects), "\n"); print(objects)

# --- database (same folder as the check script); stay here until the end ---------------------
db_dir <- file.path(REPO, "data/private/globaltrends_v2")
dir.create(db_dir, showWarnings = FALSE, recursive = TRUE)
setwd(db_dir)
if (!dir.exists("db")) initialize_db()
start_db()
initialize_python(api_key = api_key, conda_env = CONDA_ENV)
rm(api_key)

START <- "2008-01"; END <- "2024-12"   # the package takes start_date/end_date per batch
LOCS <- globaltrends::us_states          # 51 incl. DC

# --- control batch for the full window ------------------------------------------------
ctrl <- add_control_keyword(keyword = c("gmail", "map", "translate", "wikipedia", "youtube"), start_date = START, end_date = END)
cat("control batch:", ctrl, "\n")
download_control(control = ctrl, locations = LOCS)

# --- object batches: the package downloads objects together with a control term, so
#     keep batches small (4 keywords) ---------------------------------------------------
chunks <- split(objects, ceiling(seq_along(objects) / 4))
obj_ids <- integer(0)
for (ch in chunks) {
  id <- add_object_keyword(keyword = ch, start_date = START, end_date = END)
  cat("object batch", id, ":", paste(ch, collapse = ", "), "\n")
  obj_ids <- c(obj_ids, id)
}
for (id in obj_ids) {
  cat("\n== downloading object batch", id, "==\n")
  download_object(object = id, control = ctrl, locations = LOCS)
  compute_score(control = ctrl, object = id, locations = LOCS)
}

# --- export: Aug-Sep mean per election year -------------------------------------------
sc <- bind_rows(lapply(objects, function(k) export_score(keyword = k)))
sc <- sc %>%
  mutate(date = as.Date(date), year = as.integer(format(date, "%Y")), month = as.integer(format(date, "%m")),
         state = sub("^US-", "", location)) %>%
  filter(year %in% c(2008, 2012, 2016, 2020, 2024), month %in% c(8, 9)) %>%
  group_by(keyword, state, year) %>%
  summarise(score_aug_sep = mean(score, na.rm = TRUE), n_months = n(), .groups = "drop")

out <- file.path(REPO, "data/processed/globaltrends_scores.csv")
write.csv(sc, out, row.names = FALSE)
cat("\nwrote", out, ":", nrow(sc), "rows\n")
print(sc %>% count(keyword, year) %>% tidyr::pivot_wider(names_from = year, values_from = n))

disconnect_db()
setwd(REPO)
cat("\nCollection done. Next: python3 src/03_features.py\n")
