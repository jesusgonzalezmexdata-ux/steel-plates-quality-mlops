"""Run reproducible Phase 9 diagnostics without replacing Phase 8 artifacts."""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from quality_ml.data.split import build_multiclass_target
from quality_ml.models.final_holdout import _read_rows
from quality_ml.evaluation import error_analysis as errors
from quality_ml.evaluation import interpretability as importance
from quality_ml.evaluation import uncertainty
from quality_ml.evaluation.protocol import (
    ATOL, CLASSES, FEATURES, MARGIN_EDGES, analysis_protocol, assert_frozen, digest, load_phase8,
)


def analyze(root):
    """Pure artifact computation: returns frames/JSON, writes nothing."""
    final, saved, matrix = load_phase8(root)
    raw_path = root / "data/raw/steel_plates_faults.csv"
    train_ids = final["split"]["train_positions"]
    holdout_ids = final["split"]["holdout_positions"]
    training = _read_rows(raw_path, train_ids)
    X = training[list(FEATURES)]
    y = build_multiclass_target(training)
    segments = errors.training_segment_spec(X)
    protocol = analysis_protocol()
    protocol["training_segment_cuts"] = segments
    repetitions = []

    def collect(model, valid, actual, fold):
        repetitions.append(importance.fold_permutation(model, valid, actual, fold))

    oof, audit, fold_metrics = uncertainty.reconstruct_oof(X, y, train_ids, collect)
    selection = json.loads((root / "reports/ml/model_selection/selection.json").read_text())
    previous_folds = selection["evaluations"]["tuned_random_forest"]["fold_metrics"]
    for observed, previous in zip(fold_metrics, previous_folds):
        for metric, value in observed.items():
            if not np.isclose(value, previous[metric], rtol=0, atol=ATOL):
                raise ValueError(f"BLOCKED: Phase 7 fold metric mismatch: {metric}")
    policy = uncertainty.candidate_policy(oof)
    # Freeze before the first holdout policy application. No holdout input above.
    policy_hash = digest(policy)
    protocol["review_policy_candidate"] = policy
    protocol["review_policy_hash"] = policy_hash
    fold_repeats = pd.concat(repetitions, ignore_index=True)
    permutation = importance.aggregate_importance(fold_repeats)
    # Phase 8 did not persist an estimator. Reconstruct identically on TRAIN only
    # for impurity importance. Never invoke this estimator on holdout measurements.
    model = assert_frozen()
    model.fit(X, y)
    native = importance.native_importance(model)
    assert_frozen(model)

    holdout = uncertainty.prediction_frame(saved.row_index, saved.actual_class,
        saved[[f"probability_{c}" for c in sorted(CLASSES)]].to_numpy(), sorted(CLASSES))
    pd.testing.assert_series_equal(holdout.predicted_class, saved.predicted_class)
    holdout_features = _read_rows(raw_path, holdout_ids)[list(FEATURES)]
    actual = build_multiclass_target(_read_rows(raw_path, holdout_ids))
    if not np.array_equal(actual.to_numpy(), holdout.actual_class.to_numpy()):
        raise ValueError("BLOCKED: holdout labels do not match snapshot")
    segment_table = errors.segment_errors(holdout_features, holdout, segments)
    holdout_context = holdout_features.set_axis(holdout_ids)
    train_context = X.set_axis(train_ids)
    high_errors = pd.concat([
        errors.high_confidence_errors(oof, train_context, policy["high_threshold"], "DEVELOPMENT_OOF"),
        errors.high_confidence_errors(holdout, holdout_context, policy["high_threshold"], "FINAL_HOLDOUT_POST_HOC"),
    ], ignore_index=True)
    application = uncertainty.apply_policy(holdout, policy)
    if digest(policy) != policy_hash:
        raise ValueError("Candidate policy mutated after holdout")
    cases = importance.case_examples(holdout, holdout_context, policy, permutation)
    calibration = dict(
        oof=uncertainty.calibration_metrics(oof, "DEVELOPMENT_OOF"),
        holdout=uncertainty.calibration_metrics(holdout, "POST_HOC_CALIBRATION_DIAGNOSTIC"),
        probability_behavior="UNCERTAIN",
        comparison_reason="Same direction of top-label underconfidence is descriptive; aggregate differences do not establish equivalence or distribution shift",
        multiclass_brier_definition=protocol["brier_definition"],
        ece_definition=protocol["ece_definition"], confidence_edges=protocol["confidence_edges"],
        calibrated_model_validated=False,
    )
    summary = dict(
        final_model_frozen=True, post_holdout_tuning=False,
        alternative_model_evaluation=False, feature_selection_after_holdout=False,
        holdout_invalidated=False, total_holdout_rows=len(holdout),
        total_correct=int(holdout.correct_prediction.sum()),
        total_holdout_errors=int((~holdout.correct_prediction).sum()),
        holdout_error_rate=float((~holdout.correct_prediction).mean()),
        oof_rows=len(oof), oof_duplicates=int(oof.row_id.duplicated().sum()),
        oof_missing=len(set(train_ids)-set(oof.row_id)), oof_metrics=uncertainty.frame_metrics(oof),
        fold_metrics=fold_metrics, phase_7_fold_metrics_match=True,
        review_policy_candidate=policy, holdout_policy_application=application,
        high_confidence_errors_oof=int((high_errors.evidence_source == "DEVELOPMENT_OOF").sum()),
        high_confidence_errors_holdout=int((high_errors.evidence_source == "FINAL_HOLDOUT_POST_HOC").sum()),
        insufficient_data_segments=int(((segment_table.actual_class == "ALL") &
                                        (segment_table.status == "INSUFFICIENT_DATA")).sum()),
        insufficient_data_class_segments=int(((segment_table.actual_class != "ALL") &
                                              (segment_table.status == "INSUFFICIENT_DATA")).sum()),
        importance_stability=permutation.status.value_counts().to_dict(),
        shap_status="NOT_REQUIRED", association_not_causation=True,
        verdict="PASS_WITH_LIMITATION", validity_scope="FULL_OBSERVATION_CLASSIFICATION_ONLY",
        early_prediction_supported=False, environment=dict(python=platform.python_version(),
            numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__),
    )
    load_phase8(root)  # Confirm every source byte and metric is still intact.
    frames = {
        "error_analysis/confusion_pairs.csv": errors.confusion_pairs(holdout),
        "error_analysis/class_error_summary.csv": errors.class_summary(holdout),
        "error_analysis/segment_errors.csv": segment_table,
        "error_analysis/high_confidence_errors.csv": high_errors,
        "uncertainty/oof_predictions.csv": oof,
        "uncertainty/confidence_bins.csv": uncertainty.confidence_bins(oof),
        "uncertainty/margin_bins.csv": uncertainty.confidence_bins(oof, MARGIN_EDGES, "probability_margin"),
        "uncertainty/holdout_confidence_bins.csv": uncertainty.confidence_bins(holdout),
        "uncertainty/threshold_tradeoff.csv": uncertainty.threshold_tradeoff(oof),
        "interpretability/native_feature_importance.csv": native,
        "interpretability/permutation_importance.csv": permutation,
        "interpretability/permutation_by_fold.csv": fold_repeats,
    }
    documents = {
        "error_analysis/analysis_protocol.json": protocol,
        "error_analysis/analysis_summary.json": summary,
        "uncertainty/oof_fold_audit.json": audit,
        "uncertainty/calibration_metrics.json": calibration,
        "interpretability/case_examples.json": cases,
    }
    return frames, documents, matrix


def write_artifacts(output, frames, documents):
    for name, frame in frames.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False, lineterminator="\n")
    for name, value in documents.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def render_figures(output, frames, matrix):
    # Caller configures a disposable MPLCONFIGDIR for the command or test.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(8.5, 7), layout="constrained")
    ax.imshow(matrix.to_numpy(), cmap="Blues")
    ax.set(xticks=range(7), yticks=range(7), xticklabels=CLASSES, yticklabels=CLASSES,
           xlabel="Predicted class", ylabel="Actual class", title="Final holdout: frozen predictions (n=389)")
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right")
    for i in range(7):
        for j in range(7):
            value = matrix.iloc[i, j]
            ax.text(j, i, str(value), ha="center", va="center",
                    color="white" if value > matrix.to_numpy().max()/2 else "#18212b")
    fig.savefig(output / "error_analysis/confusion_matrix.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6), layout="constrained")
    ax.plot([0, 1], [0, 1], linestyle="--", color="#777777", label="Reference: confidence = accuracy")
    for name, color, label in [
        ("confidence_bins.csv", "#1769aa", "Development OOF"),
        ("holdout_confidence_bins.csv", "#ad4c11", "Holdout post-hoc")]:
        bins = frames[f"uncertainty/{name}"]
        selected = bins.loc[bins.n > 0]
        ax.plot(selected.mean_confidence, selected.accuracy, color=color, label=label)
        for _, row in selected.iterrows():
            ax.scatter(row.mean_confidence, row.accuracy, edgecolors=color,
                       facecolors=color if row.n >= 30 else "none", s=45)
    ax.set(xlim=(0, 1), ylim=(0, 1.03), xlabel="Mean predicted top-class confidence",
           ylabel="Observed accuracy", title="Confidence reliability: fixed bins")
    ax.legend(loc="lower right")
    fig.text(0.02, 0.01, "Hollow points: n < 30. Diagnostic only; top-label calibration is not classwise calibration.", fontsize=8)
    fig.get_layout_engine().set(rect=(0, 0.055, 1, 0.935))
    fig.savefig(output / "uncertainty/reliability.png", dpi=150)
    plt.close(fig)

    table = frames["interpretability/permutation_importance.csv"].iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 10), layout="constrained")
    ax.barh(table.feature, table.importance_mean, xerr=table.importance_std,
            color="#1769aa", ecolor="#555555", capsize=2)
    ax.axvline(0, color="#333333", linewidth=0.7)
    ax.set(xlabel="Validation macro-F1 decrease (mean +/- fold SD)",
           title="Frozen RF: permutation importance across five folds")
    fig.text(0.02, 0.01, "5 permutations per feature/fold; SD across fold means is not a confidence interval.", fontsize=9)
    fig.get_layout_engine().set(rect=(0, 0.045, 1, 0.945))
    fig.savefig(output / "interpretability/feature_importance.png", dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/ml"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    output = args.output.resolve()
    if not output.is_relative_to(root) or output == root:
        raise ValueError("Output must be a directory within this repository")
    if output.is_relative_to((root / "reports/ml/final_holdout").resolve()):
        raise ValueError("Cannot replace Phase 8 artifacts")
    frames, documents, matrix = analyze(root)
    write_artifacts(output, frames, documents)
    render_figures(output, frames, matrix)
    print(json.dumps(documents["error_analysis/analysis_summary.json"], indent=2))


if __name__ == "__main__":
    main()
