# Human gate: Power BI Desktop runtime validation

HUMAN_GATE_POWER_BI_RUNTIME_VALIDATION = OPEN
PHASE_10_STATUS = IN_PROGRESS_PENDING_RUNTIME
PHASE_11_STATUS = NOT_STARTED

This gate is required by the authorized closeout program, Phase 10.12.
The available tools cannot run the native Power BI Desktop UI or prove its
refresh/compilation/render/save results. The text draft and Python evidence are
prepared; the following operations require direct Desktop evidence.

## Prepared files

- Open [steel-plates-quality-bi.pbip](../../powerbi/project/steel-plates-quality-bi.pbip).
- Existing [PBIX](../../powerbi/artifacts/steel-plates-quality-bi.pbix) is unchanged.
- New dataset: [ml_holdout_evaluation.csv](../../powerbi/data/ml_holdout_evaluation.csv).
- New page: MODEL PERFORMANCE & REVIEW (12 visuals).
- New table: ML_Holdout; new expression: RutaMLCSV.
- Expected results: [reconciliation](powerbi_ml_reconciliation.md).
- All pre-change file hashes: [baseline](pre_ml_powerbi_hashes.json).

PRE_ML_PBIX_SHA256 = 0a87a4e33b78cf786d1a76250b39f154d19508480f256fa1898e8f818d9bdba5
PRE_ML_PBIP_SHA256 = 343a455fa0dd01f26d6196f213808b13b90ed333e001ee468c6afed782ee77f7
POST_ML_PBIX_SHA256 = NOT_AVAILABLE
POST_ML_PBIP_STATUS = TEXT_DRAFT_PENDING_DESKTOP_SAVE

## Exact validation sequence

1. Open the PBIP in a compatible Power BI Desktop version. Record the version
   and any opening errors. Do not start from the old PBIX, which has no ML page.
2. In Transform data / Power Query, select the existing RutaCSV query and change
   its text value to the actual checkout's `data/raw/steel_plates_faults.csv`.
   The saved parameter is a placeholder (`C:\path\to\...`); the PBIX may still hold the former local path until it is re-saved.
   RutaMLCSV derives the repository root from `/data/raw/` and locates
   `powerbi/data/ml_holdout_evaluation.csv`; inspect its resolved value.
   This is a local-file source; no cloud service or network is required.
3. Refresh preview, Close & Apply, then Refresh the report. Confirm no Power Query
   errors, the 27 source measurements, seven one-hot labels and existing tables.
   ML_Holdout must contain exactly 389 rows with role FINAL_HOLDOUT_EVALUATION;
   the original defect fact must still contain 1,941 rows.
4. Inspect Model view. Existing star-schema relationships must match the prior
   project. ML_Holdout stays disconnected; remove any unintended auto-detected
   relationship only after recording it. Confirm all new ML measures compile
   and no original measure has broken.
5. Open MODEL PERFORMANCE & REVIEW. Check the four score/count cards, three
   slicers and four analytic tables plus the context note. Check legibility,
   no blank/broken visuals, and full-holdout score labels.
6. Clear all filters and compare every total and class/prediction/review count
   against the reconciliation document. Final Macro-F1 must be 0.8146728101764369
   and Balanced Accuracy 0.8048726799979933 before display rounding.
7. Select A300: 156 rows, 121 correct, 122 review. Select A400 instead:
   233 rows, 186 correct, 139 review. Clear steel, select Pastry:
   32 rows, 20 correct, 29 review. Check thickness filtering and clear all filters.
   Final score cards stay fixed; selected-group error/review/count tables change.
8. Confirm the confusion table shows errors such as Bumps -> Other_Faults (21).
   Check confidence and review tables, and inspect row_id 1277 in Data view:
   Other_Faults -> K_Scatch, confidence 1.0, HIGH_CONFIDENCE, correct_prediction=0.
9. Visit all four original pages, exercise their slicers and check their measures
   and visuals. Preserve their content and analytical qualifications. Legacy
   COPQ uses assumed costs, not demonstrated savings.
10. Save the PBIP through Desktop. Then use Save As through Desktop to save the
    updated PBIX at `powerbi/artifacts/steel-plates-quality-bi.pbix`.
    Reopen both saved formats to verify successful persistence of the ML page.
    Do not edit PBIX bytes outside Desktop.
11. Capture the Desktop version, refresh/model/measure/visual/filter/save outcomes,
    observed reconciliation values and supporting screenshots or exported tables.
    Record failures explicitly. Recompute PBIX SHA256 after the save, for example:
    `Get-FileHash -LiteralPath 'powerbi/artifacts/steel-plates-quality-bi.pbix' -Algorithm SHA256`.
12. Review the Desktop-generated Git diff for unintended changes, verify original
    page functionality, rerun Python export/artifact tests and record the actual
    post-save PBIP status/hash. Only then mark runtime PASS and continue Phase 11.

The pre-change preservation tests intentionally detect later Desktop edits to
existing objects. If Desktop rewrites formatting or the source parameter, compare
the recorded baseline and classify that diff; do not delete the baseline or weaken
tests simply to force PASS. The generation script recreates the draft, so do not
rerun it over a Desktop-refined page without reviewing the intended overwrite.

## Required completion evidence

| Control | Current result |
|---|---|
| Desktop opens PBIP | NOT_EXECUTED |
| Power Query refresh | NOT_EXECUTED |
| Model relationships | NOT_EXECUTED |
| DAX measures compile | NOT_EXECUTED |
| ML dataset imported | NOT_EXECUTED |
| ML page renders | NOT_EXECUTED |
| Filters interact correctly | NOT_EXECUTED |
| Existing visuals remain intact | NOT_EXECUTED |
| Python / Desktop values reconcile | NOT_EXECUTED |
| Save and reopen PBIP | NOT_EXECUTED |
| Save and reopen PBIX | NOT_EXECUTED |

No phase is promoted from this handoff alone. No certificate or production
readiness is implied. Phase 11 README/model card/evidence pack/clean-clone/
adversarial/export closeout remains gated on this runtime evidence.