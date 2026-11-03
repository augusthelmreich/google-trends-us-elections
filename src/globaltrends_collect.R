# ---------------------------------------------------------------------------
# globaltrends, collection: all topics through the globaltrends package (Puhr & Müllner 2021).
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
# Requirements: as for globaltrends_check.R (conda environment and API key, both
# prompted for). Run in an R session with the repository root as working directory:
#   source("src/globaltrends_collect.R")
# A full collection is about 700 requests, paced by the package.
# Rerunning is incremental: only entities missing from the database are added, and
# downloads already present are skipped.
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

# --- Database. The package resolves its database relative to the working directory, so
#     the script works inside data/private/globaltrends_v2 and returns to the repository
#     root only after disconnecting. ----------------------------------------------------
db_dir <- file.path(REPO, "data/private/globaltrends_v2")
dir.create(db_dir, showWarnings = FALSE, recursive = TRUE)
setwd(db_dir)
if (!dir.exists("db")) initialize_db()
start_db()
initialize_python(api_key = api_key, conda_env = CONDA_ENV)
rm(api_key)

START <- "2008-01"; END <- "2024-12"   # collection window, set per batch
LOCS <- globaltrends::us_states          # the 50 states and DC

# --- Control basket: the package default, one batch for the whole window. An existing
#     control batch is reused so that all object batches share the same denominator. ---
ctrl_tab <- dplyr::collect(gt.env$keywords_control)
ctrl_existing <- unique(ctrl_tab$batch[ctrl_tab$keyword == "gmail"])
if (length(ctrl_existing)) {
  ctrl <- ctrl_existing[1]
} else {
  ctrl <- add_control_keyword(keyword = c("gmail", "map", "translate", "wikipedia", "youtube"), start_date = START, end_date = END)
}
cat("control batch:", ctrl, "\n")
download_control(control = ctrl, locations = LOCS)

# --- Object batches. Entities already in the database keep their batch; new ones are
#     added in batches of four, because the package downloads each batch together with a
#     control term on one scale. ----------------------------------------------------------
obj_tab <- dplyr::collect(gt.env$keywords_object)
missing <- setdiff(objects, obj_tab$keyword)
cat("objects already in the database:", length(objects) - length(missing), " new:", length(missing), "\n")
chunks <- if (length(missing)) split(missing, ceiling(seq_along(missing) / 4)) else list()
for (ch in chunks) {
  id <- add_object_keyword(keyword = ch, start_date = START, end_date = END)
  cat("object batch", id, ":", paste(ch, collapse = ", "), "\n")
}
obj_tab <- dplyr::collect(gt.env$keywords_object)
obj_ids <- sort(unique(obj_tab$batch[obj_tab$keyword %in% objects]))
for (id in obj_ids) {
  cat("\n== object batch", id, "==\n")
  download_object(object = id, control = ctrl, locations = LOCS)   # already-downloaded batches are skipped
  compute_score(control = ctrl, object = id, locations = LOCS)
}

# --- Export: mean of the August and September scores for each included entity, state and
#     election year. -------------------------------------------------------------------------
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
