# ML problem contract

This contract is the boundary for any later modelling work. It is grounded in
the dataset audit in [`01_dataset_audit.md`](01_dataset_audit.md) and does not
add information that is absent from the source CSV.

## BUSINESS QUESTION

For a steel plate that has already been identified as defective, can the
observable measurements in this dataset support a reliable classification of
the defect type and a useful indication of when human quality review is needed?

This is a support question for inspection, prioritisation and quality analysis.
It is not a claim about preventing defects or predicting whether a plate will
be defective.

## ANALYTICAL QUESTION

Given one row from the raw dataset, classify the plate into one of the seven
original defect classes and quantify the confidence of that classification.
The analysis will compare a full-observation scenario with a restricted-
information scenario only after the separate leakage audit establishes which
measurements are defensible in each scenario.

## TARGET

The primary target is a seven-class categorical label:

`Pastry`, `Z_Scratch`, `K_Scatch`, `Stains`, `Dirtiness`, `Bumps`, or
`Other_Faults`.

The source represents this target using seven one-hot binary columns. The audit
verified that every one of the 1,941 rows has exactly one value equal to `1` in
those columns. For analysis, the unique positive column is mapped to its column
name (equivalent to an `argmax` over the seven indicators). This creates a
derived in-memory multiclass label; it does not edit, overwrite or reinterpret
the source CSV. The seven original indicator columns are target data and must
not be included in the predictor matrix.

The target remains conditional on a plate already being identified as
defective. There is no good-plate or non-defect class in this dataset.

## UNIT_OF_ANALYSIS

One row represents one steel plate already recorded as defective, with its
observed measurements and one defect label. The row is the unit of analysis;
there is no validated production batch, machine or time-series unit.

## PREDICTION_MOMENT

The only defensible prediction moment supported by this file is after the
measurements represented in the row have been recorded for a plate already
identified as defective. The dataset does not prove that any feature was
available before inspection, before localization, or before production.

Consequently, this contract does not call the task early prediction, online
prediction, pre-production prediction, prevention or detection before
production. Any later claim about timing requires external provenance evidence
and a revised contract.

## AVAILABLE_FEATURES

The candidate observations present in the raw CSV are:

- the geometric and coordinate measurements (`X_*`, `Y_*`, perimeter and size
  measures);
- image-derived area, luminosity, index, log and sigmoid measurements;
- steel indicators (`TypeOfSteel_A300`, `TypeOfSteel_A400`);
- `Steel_Plate_Thickness`;
- `Length_of_Conveyer`.

The technical `id` is present as a row identifier. Its provenance is not
documented by the dataset materials. If it is only an identifier, it will not
be a predictive feature. It must not be used as a signal merely because it is
numeric or unique.

The audit marked coordinates, image-derived variables and
`Length_of_Conveyer` as `QUESTIONABLE/PENDING_LEAKAGE_AUDIT`. They remain
candidate observations for the purpose of comparing information scenarios, but
they are not certified predictors by this contract and are not excluded
definitively here. That decision belongs to Fase 3.

## UNAVAILABLE_INFORMATION

The dataset does not contain:

- plates known to be good;
- production timestamps or a validated sequence;
- machine or line identity;
- shift;
- supplier;
- maintenance records;
- operator or process context;
- provenance proving when each measurement became available.

These omissions prevent claims about defect incidence, time-to-event behaviour,
machine drift, shift effects, supplier effects, process causality, prevention,
scrap reduction or plant savings.

## DECISION_SUPPORTED

Subject to validation, the output may support:

- a proposed defect class for an already defective plate;
- prioritisation of human review using class and confidence;
- aggregation of classification results for descriptive quality analysis;
- identification of segments where classification is less reliable.

The output is decision support. A human quality process remains responsible for
the final interpretation and action.

## MODEL_DOES_NOT_DECIDE

The model must not automatically decide:

- acceptance or rejection of a plate;
- scrap or rework disposition;
- line stoppage;
- process parameter changes;
- maintenance scheduling;
- supplier action;
- whether a future plate will be defective;
- causal explanations for a defect.

Any cost or priority value added later is illustrative decision support, not a
measured saving or an estimate of causal impact.

## SUCCESS_CRITERIA

Success is conditional and will be assessed only after the authorized
validation phases implement a leakage-safe, stratified protocol. The planned
criteria are:

1. demonstrate a reproducible improvement over a stratified dummy baseline;
2. use macro-F1 as the primary classification metric because the seven classes
   are imbalanced and each class matters to review coverage;
3. report balanced accuracy, macro precision/recall, weighted F1 and log loss
   when probabilities are available;
4. inspect per-class recall, confusion pairs, confidence and calibration rather
   than relying on accuracy alone;
5. show that the result is stable under the fixed resampling protocol and does
   not depend on target columns, `id`, or an unresolved proxy;
6. preserve an untouched test set until model selection is complete.

These are acceptance criteria for evidence, not a promise that the dataset
will meet them.

## STOP_CRITERIA

Stop model development or report the result as blocked when any of the
following holds:

- the target mapping is not one-to-one for a row;
- a target indicator or target-derived value enters the predictors;
- feature availability or leakage status cannot be justified;
- a model does not show reproducible lift over the dummy baseline;
- minority-class performance collapses or confidence is materially misleading;
- results are unstable under the planned stratified validation;
- the test set is used during tuning or selection;
- the data schema, provenance or reproducibility evidence changes without
  review;
- the result would require claims about good plates, production timing,
  causality, prevention, scrap or savings that this dataset cannot support.

## Scope boundary

This contract authorizes no model, feature selection, calibration, API,
monitoring, Power BI change or production claim. Those activities require
separate evidence and authorization in later phases. Fase 3 must resolve the
`QUESTIONABLE/PENDING_LEAKAGE_AUDIT` groups and document the comparison between
full observation and restricted information before any performance result is
treated as methodologically defensible.
