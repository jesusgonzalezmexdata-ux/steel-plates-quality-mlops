# Project execution state

LAST_COMPLETED_PHASE = 6
G5_BASELINE = PASS_WITH_LIMITATION
G6_CANDIDATES = PASS_WITH_LIMITATION
PRIMARY_METRIC = macro_f1
BASELINE_SIGNAL_DETECTED = TRUE
HOLDOUT_STATUS = SEALED
NEXT_PHASE = 7_CONTROLLED_TUNING_AND_SELECTION

VALIDITY_SCOPE = FULL_OBSERVATION_CLASSIFICATION_ONLY
EARLY_PREDICTION_SUPPORTED = FALSE
TEMPORAL_FEATURE_AVAILABILITY = NOT_DEMONSTRATED

PHASE_5_CHECKPOINT = 6def86eb1f185a400720c95d952275b718006c75
PHASE_5_STATE_CHECKPOINT = 47f1fb6e8bd5da51a431e08610909ff3cd12e500
PHASE_6_CHECKPOINT = b60c589971d3385854326514da905164224a529b

The baseline signal is based on five stratified folds over the 1,552-row
training partition. The 389-row holdout was not accessed, and no model
candidate tuning, calibration, Power BI change or push has been performed.
Candidate comparison is valid under full-observation classification only; the
complete repository suite remains limited by missing predeclared dependencies
for the legacy Streamlit and DuckDB tests.
