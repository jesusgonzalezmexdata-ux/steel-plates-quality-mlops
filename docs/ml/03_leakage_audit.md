# Leakage audit

## Purpose and boundary

This audit classifies columns using documented meaning, provenance evidence and
the defensible prediction moment from the problem contract. It does not train a
model, tune a model, rank features by performance, or call high correlation
leakage. Association and predictive power can result from legitimate redundant
measurements, a shared acquisition process, or a proxy; they do not establish
that a feature contains the target.

Reproduce and validate the lists from the repository root with:

```powershell
$env:PYTHONPATH = "src"
python -m quality_ml.data.leakage --csv data/raw/steel_plates_faults.csv
```

The module fails closed if a target is missing or a schema column has no
explicit status. It also asserts that target and technical identifier columns
are absent from both predictor scenarios.

## Status definitions

| Status | Meaning in this audit |
|---|---|
| `EXCLUDE` | Not a predictor: a source target column or an identifier confirmed/treated as technical. |
| `SAFE` | No direct target construction or post-result evidence is documented, so it is provisionally usable in both scenarios. This does not prove production-time availability. |
| `QUESTIONABLE` | Meaning, provenance, or availability timing could permit a post-result or process-position proxy; retain for the full-observation sensitivity scenario only. |

The distinction is based on evidence available in this repository. It is not a
claim that a `SAFE` feature is causal or early-available.

## Evidence by feature group

| Feature group | Status | Evidence and unresolved issue |
|---|---|---|
| `Pastry`, `Z_Scratch`, `K_Scatch`, `Stains`, `Dirtiness`, `Bumps`, `Other_Faults` | `EXCLUDE` | These are the seven original target indicators. They define the label and cannot enter `X`. |
| `id` | `EXCLUDE` | It is unique in the snapshot and documented only as a technical row identifier. No provenance supports a process meaning. |
| `TypeOfSteel_A300`, `TypeOfSteel_A400`, `Steel_Plate_Thickness` | `QUESTIONABLE` | Plate attributes with no direct construction from the target shown in the repository, but their exact upstream availability is not documented. The repository cannot justify a `SAFE` classification. |
| `X_Minimum`, `X_Maximum`, `Y_Minimum`, `Y_Maximum` | `QUESTIONABLE` | Coordinates are image/inspection measurements. Their acquisition timing and any relation to inspection sequencing are undocumented. |
| `Pixels_Areas`, `X_Perimeter`, `Y_Perimeter`, luminosity fields, indices, log fields and `SigmoidOfAreas` | `QUESTIONABLE` | These are image-derived or segmentation-derived measurements. The repository does not establish whether they exist before defect localization or after the result is known. |
| `Length_of_Conveyer` | `QUESTIONABLE` | A conveyor-related field may be a legitimate observation or a process-position/batch proxy. No machine, timestamp or sequence provenance is available. |

The `QUESTIONABLE` status is deliberately retained instead of inventing an
availability justification. Fase 3 cannot resolve external provenance that the
dataset does not contain.

## Reproducible feature sets

The lists below are generated in source-column order by
`quality_ml.data.leakage`. They are schema-validated and do not change the raw
CSV.

### FULL_OBSERVATION_FEATURES

This sensitivity set uses all non-target observations except the technical
identifier. It represents the maximum information present in the file after a
defect has already been identified; it is not an early-prediction scenario.

```text
TypeOfSteel_A300, TypeOfSteel_A400, Steel_Plate_Thickness,
X_Minimum, X_Maximum, Y_Minimum, Y_Maximum, Pixels_Areas, X_Perimeter,
Y_Perimeter, Sum_of_Luminosity, Minimum_of_Luminosity,
Maximum_of_Luminosity, Length_of_Conveyer, Edges_Index, Empty_Index,
Square_Index, Outside_X_Index, Edges_X_Index, Edges_Y_Index,
Outside_Global_Index, LogOfAreas, Log_X_Index, Log_Y_Index,
Orientation_Index, Luminosity_Index, SigmoidOfAreas
```

### RESTRICTED_INFORMATION_FEATURES

No feature can currently be placed in this set. The repository contains no
verifiable evidence that steel type or thickness, or any other candidate,
would be available at the defined prediction moment. The reproducible output
is therefore an empty list until provenance is supplied:

```text
<empty>
```

This must not be described as a production-early set. The full-observation set
remains a sensitivity scenario, and no restricted-information performance
comparison is authorized until this list has defensible members.

## Programmatic assertions

The module validates that:

- every original target column is present in the schema and excluded from both
  predictor sets;
- `id` is excluded from both predictor sets when treated as a technical ID;
- `RESTRICTED_INFORMATION_FEATURES` may intentionally overlap with
  `FULL_OBSERVATION_FEATURES` because both are predictor sets;
- neither predictor set overlaps with excluded targets or technical IDs;
- no prohibited predictor/target/identifier overlap exists;
- the sets cover the complete schema without silently dropping a column;
- every classified feature has exactly one reproducible status;
- no target-derived or performance-derived rule is used to assign status.

## Unresolved provenance

The following questions remain open and must not be answered by assumption:

1. Were coordinate and image-segmentation measurements recorded before or after
   the defect label was established?
2. Does `Length_of_Conveyer` encode a physical measurement, a process position,
   a batch, or another acquisition artifact?
3. Does `id` have any meaning beyond technical row identity?
4. At what point were steel type and thickness available in the actual quality
   workflow?
5. Are rows independent observations, or can unobserved production sequence
   create related groups?

Until these are answered, results using `QUESTIONABLE` variables must be
reported as conditional sensitivity evidence rather than early detection,
causal evidence or production performance.
