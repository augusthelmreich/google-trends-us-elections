# Pre-registration: party-weighted issue-attention index

Written 2026-10-12, before the index was computed or compared with any outcome. Frozen on
commit. Deviations are recorded in the final section, not by editing the plan.

## 1. Hypothesis

Issue-ownership theory (Petrocik 1996; Egan 2013) holds that each party is trusted on a
set of issues and gains when those issues are salient. Applied to states:

> **H1.** States where Democratic-owned issues are relatively more salient than
> Republican-owned issues, compared with other states in the same election, swing more
> Democratic than the national average.

The direction is fixed in advance: a positive relation between the index and the
deviation from national swing.

## 2. Data already in the repository

- `data/processed/features.csv`: per (state, election), the relative-attention feature
  `x = value / mean(value) − 1` for each issue topic, from Google Trends state maps for
  August–September of 2008, 2012, 2016, 2020, 2024; and the swing in Democratic
  two-party share.
- `data/raw/topics.csv`: issue topics with an ownership sign (`own_sign`) and the source
  supporting it (`own_source`).

## 3. Topics and signs (fixed from the literature, not from data)

| Topic | own_sign | Source |
|---|---|---|
| health insurance | +1 | Fagan 2019, App. Table 2 (Egan long-run score −12) |
| unemployment | +1 | Egan 2013, Table 3.2 (jobs → Democratic), as applied in Noble 2025, suppl. C.2 |
| climate change | +1 | Fagan 2019, App. Table 2 (environment, −18) |
| tax | −1 | Egan 2013, pp. 2 and 10; Table 3.2 via Noble 2025 (taxes → Republican) |
| crime | −1 | Fagan 2019, App. Table 2 (law and crime, +7) |

Excluded, with reasons recorded in `topics.csv`: immigration (fails the coverage rule in
every year: 24 zero states in 2008), education (no Google topic with adequate state
coverage), abortion and gun control (non-consensus issues in Egan's framework; ownership
does not apply), inflation (no pre-2022 ownership evidence). Coverage for the five
included topics was checked before this plan was written: no zero states in any year.

## 4. Index

For state s and election t, with the five topics i:

```
A(s,t) = Σ_i  own_i · x(s,i,t) / sd_t( x(·,i,t) )
```

Each topic's feature is divided by its standard deviation across states in that election,
so every topic enters with equal weight regardless of how spread out its map is (climate
change has about twice the spread of health insurance). The index is zero-mean within
each election by construction.

Secondary, reported but not used for the decision: the unstandardised sum Σ own_i · x.

## 5. Target

```
d(s,t) = swing(s,t) − mean_s swing(·,t)
```

the state's swing minus the equal-weighted mean swing of the 51 jurisdictions in that
election. This removes the national component, which state-level features cannot address.

## 6. Test — one confirmatory statistic

For each election t, the Pearson correlation r_t between A(·,t) and d(·,t) across the 51
jurisdictions. The confirmatory statistic is the mean of the five correlations, r̄.

Inference by permutation: shuffle A across states within each election (10,000 draws,
seed 20261012), recompute r̄ each time, and report p = share of draws with r̄ ≥ observed.
This is one-sided in the direction fixed in §1.

**Success criterion.** r̄ > 0 and p < 0.05. Anything else is reported as "no support for
H1".

Also reported, not decisive: r_t per election; the number of elections with r_t > 0;
Spearman correlations; and r̄ for the unstandardised index.

## 7. Robustness checks, fixed now

1. Drop Utah 2016 (two-party artefact from a third-party candidate).
2. Vote-weighted correlation (weights = total votes cast in the state).
3. Leave-one-topic-out: r̄ with each of the five topics removed in turn. Reported as a
   table; if H1 is supported only when one particular topic is present, that is stated.
4. Survey-weighted index, exploratory: replace own_i by the pre-election handling gap
   (% Democrats − % Republicans)/100 from the latest poll before the election, for the
   elections where such polls exist for all five topics. Labelled exploratory because
   poll coverage is incomplete (known for 2020 and 2024; partial for 2008 and 2012; none
   found for 2016).

## 8. What has and has not been seen

- The regression coefficients for health insurance, tax and unemployment in
  `05_evaluate.py` were observed before this plan was written (tax positive in every
  fold, health insurance positive, unemployment changing sign). The signs in §3 come from
  the cited literature and in the case of tax contradict the observed coefficient. They
  were not chosen to fit the data.
- Climate change and crime have not been compared with any outcome.
- No correlation between any feature and swing has been computed in this repository.
- The 2016 fold of the core evaluation showed that the candidate contrast reverses
  between elections; that finding concerns candidates, not issues, and does not inform
  the signs above.

## 9. Power, stated in advance

255 state-elections, five elections. A correlation of 0.15 within each election gives
r̄ = 0.15 with roughly p ≈ 0.01 under the permutation null; a correlation of 0.08 would
not reach significance. The test can detect a moderate, consistent effect; it cannot
detect a small one. A null is therefore evidence against a sizeable effect, not against
any effect.

## 10. Commitments

1. The result is reported whatever it is.
2. No topic, sign, transformation or test is changed after the result is seen without
   being recorded below as a deviation.
3. The script `src/07_party_index.py` implements exactly §4–§7 and nothing else.

---

## Deviations from plan

None. The script was run once after this plan was written; one indexing bug in the
robustness block (row labels vs. positions after filtering) was fixed and the script rerun,
with no change to the confirmatory numbers.

## Result (2026-10-12)

**H1 not supported.** Topics in the index: unemployment (+1), health insurance (+1),
climate change (+1), tax (−1), crime (−1).

| Election | r_t |
|---|---|
| 2008 | +0.195 |
| 2012 | −0.151 |
| 2016 | −0.123 |
| 2020 | −0.323 |
| 2024 | −0.392 |

Mean r = −0.159; one-sided permutation p = 0.995 (10,000 draws). The relation runs in the
direction opposite to H1 in four of five elections and grows stronger over time.

Robustness (§7): unstandardised index −0.151; Spearman −0.139; without Utah 2016 −0.168;
vote-weighted −0.231 (no positive year). Leave-one-topic-out: removing unemployment
weakens the result most (−0.083); removing climate change strengthens it (−0.183). The
survey-weighted version was not run (no poll file).

Interpretation, stated as hypothesis and not tested here: the negative relation is carried
mainly by the unemployment topic, whose state map tracks the unemployment rate rather
than political attention (see `03_trends_api.py`). States with relatively more
unemployment searching before the election moved relatively toward the Republican
candidate in these cycles regardless of which party held the presidency. That is a
retrospective-economic pattern, not an issue-ownership one, and it would need to be tested
against the unemployment rate itself.

Any follow-up analysis (for example controlling for prior partisanship) is exploratory
and lives in a separate script, not in `07_party_index.py`.
