# Dataset audit

## Scope and reproducibility

This audit is descriptive only. It validates the raw CSV and records risks to
resolve before any model training. It does not fit a model, learn a transform,
or claim production-time availability.

Reproduce the machine-readable audit from the repository root with:

```powershell
$env:PYTHONPATH = "src"
python -m quality_ml.data.audit --csv data/raw/steel_plates_faults.csv > audit.json
```

The source dataset is `data/raw/steel_plates_faults.csv`. Its repository
fingerprint should be captured again when the training/evidence workflow is
authorized.

## Dataset identity and schema

| Check | Result |
|---|---:|
| Observations | 1,941 |
| Columns | 35 |
| Missing cells | 0 |
| Full-row duplicates | 0 |
| Target columns | 7 one-hot defect labels |
| Rows with exactly one target | 1,941 / 1,941 |
| Numeric columns | 35 (including targets and `id`) |
| Binary columns | 9: two steel indicators plus seven target indicators |

The source contains an identifier (`id`), geometry and image-derived measures,
steel indicators, thickness, conveyor-length information, and the seven defect
indicators. It does not contain a timestamp, machine, shift, supplier,
maintenance record, or a non-defective class.

The seven original target labels are:

| Target | Count | Share |
|---|---:|---:|
| `Pastry` | 158 | 8.14% |
| `Z_Scratch` | 190 | 9.79% |
| `K_Scatch` | 391 | 20.14% |
| `Stains` | 72 | 3.71% |
| `Dirtiness` | 55 | 2.83% |
| `Bumps` | 402 | 20.71% |
| `Other_Faults` | 673 | 34.67% |

The class distribution is materially imbalanced: the largest class is 12.2
times the smallest. Accuracy alone would therefore be insufficient for model
evaluation. This observation is recorded for the later validation phase; no
metric or model is selected here.

## Quality checks

All 35 columns are numeric in the CSV. The two steel columns are complementary
binary indicators in this snapshot. The seven defect columns are also binary,
and every row has exactly one positive defect indicator. These checks support a
multiclass target derived from the one-hot labels, but the labels themselves
must never be included as predictors.

Cardinality is heterogeneous. `id` has 1,941 unique values, while
`Steel_Plate_Thickness` has 24, `Length_of_Conveyer` has 84, and
`Outside_Global_Index` has 3. Low cardinality is not evidence that a variable
is safe or causal; it only describes the observed sample.

The full cardinality profile is available in the JSON emitted by the audit
module. The most relevant values are:

| Feature | Unique values |
|---|---:|
| `id` | 1,941 |
| `Y_Maximum` | 1,940 |
| `Y_Minimum` | 1,939 |
| `Sum_of_Luminosity` | 1,909 |
| `X_Maximum` | 994 |
| `X_Minimum` | 962 |
| `Pixels_Areas` | 920 |
| `Steel_Plate_Thickness` | 24 |
| `Length_of_Conveyer` | 84 |
| `Outside_Global_Index` | 3 |

## Outliers and plausible derived variables

Using the descriptive 1.5×IQR rule on non-target numeric columns, the largest
flag counts are:

| Feature | IQR flags | Interpretation to verify |
|---|---:|---|
| `Sum_of_Luminosity` | 399 | highly skewed image-derived magnitude |
| `Pixels_Areas` | 395 | highly skewed defect area |
| `Outside_X_Index` | 370 | bounded ratio with a long upper tail |
| `X_Perimeter` | 352 | long-tailed geometry measure |
| `Steel_Plate_Thickness` | 240 | discrete industrial settings, not automatic errors |
| `Y_Minimum`, `Y_Maximum` | 81 each | position-like values; temporal meaning unknown |

An IQR flag is not a data-quality failure. These observations may represent
real defect morphology or a mixture of regimes and require domain review before
removal, clipping, or transformation.

Several variables are plausibly derived from others or from the same image
segmentation step: `X_Maximum - X_Minimum`, `Y_Maximum - Y_Minimum`, area,
perimeters, log indices, and luminosity summaries. The audit does not add these
features. Their redundancy and measurement timing should be assessed in the
leakage review.

## Correlation screening

The audit computes Pearson correlations among numeric candidate features and
reports the strongest pairs in its JSON output. High correlation is an
association and is not evidence of causation or leakage. In particular,
coordinate, size, perimeter, and log-area variables are expected to be related
by construction. Correlation screening cannot establish whether a value was
available before or after inspection.

The ten strongest absolute correlations in this snapshot are:

| Feature A | Feature B | Pearson r |
|---|---|---:|
| `TypeOfSteel_A300` | `TypeOfSteel_A400` | -1.00 |
| `Y_Minimum` | `Y_Maximum` | 1.00 |
| `X_Minimum` | `X_Maximum` | 0.99 |
| `Pixels_Areas` | `Sum_of_Luminosity` | 0.98 |
| `Pixels_Areas` | `X_Perimeter` | 0.97 |
| `X_Perimeter` | `Sum_of_Luminosity` | 0.91 |
| `X_Perimeter` | `Y_Perimeter` | 0.91 |
| `LogOfAreas` | `Log_X_Index` | 0.89 |
| `LogOfAreas` | `Log_Y_Index` | 0.88 |
| `LogOfAreas` | `SigmoidOfAreas` | 0.88 |

The perfect negative steel-indicator correlation is expected because the two
columns encode the same binary attribute. It is a redundancy concern, not
evidence that either column is a defect label.

## Preliminary leakage and availability matrix

This is an initial risk register, not the final leakage decision. `SAFE` means
safe to retain provisionally for data understanding; `QUESTIONABLE` means the
feature requires an availability/proxy check; `EXCLUDE` means it is the target
or a direct target encoding. The detailed policy belongs to Fase 3.

| Feature group | Meaning in this file | Availability evidence | Possible leakage | Initial status | Action |
|---|---|---|---|---|---|
| `Pastry` … `Other_Faults` | one-hot observed defect label | known only because the dataset is labeled | direct target encoding | EXCLUDE | exclude from X |
| `id` | row identifier | present in file; generation process undocumented | may encode collection/order | QUESTIONABLE | audit before use; default exclude |
| `X_*`, `Y_*` | bounding coordinates | image-derived; inspection timing undocumented | position or collection proxy | QUESTIONABLE | retain only with availability evidence |
| `Pixels_Areas`, perimeters, indices, luminosity, logs | image/segmentation measurements | observable for an already inspected plate; exact timing undocumented | may be computed after defect localization | QUESTIONABLE | compare full-observation vs restricted scenario later |
| `TypeOfSteel_A300`, `TypeOfSteel_A400` | steel-type indicators | observable attribute in file; acquisition process undocumented | no direct target encoding seen | QUESTIONABLE | validate source and redundancy |
| `Steel_Plate_Thickness` | plate thickness | observable attribute in file | possible product-mix proxy | QUESTIONABLE | retain provisionally; test segment stability later |
| `Length_of_Conveyer` | conveyor-related measurement | present, but no machine/sequence/timestamp context | process-position or batch proxy | QUESTIONABLE | require provenance before interpreting |

No feature can be declared production-early from this CSV alone. The dataset
contains only defective plates, so any later model contract must remain
conditional on a plate already being identified as defective.

## Findings and limits

The data is structurally complete for a descriptive audit, but provenance and
temporal availability are incomplete. The strongest immediate risks are target
columns accidentally entering predictors, use of `id` as a signal, and
overstating image-derived measurements as pre-inspection information. The next
authorized phase must formalize the problem contract and test leakage scenarios;
this audit does not authorize training or business claims.
