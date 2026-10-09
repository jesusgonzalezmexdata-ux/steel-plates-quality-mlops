from pathlib import Path

from quality_ml.models.select import classify_candidates, choose_final_candidate


def test_selection_is_pareto_style_and_reproducible():
    evaluations = {
        "logistic_regression": {"metrics_mean": {"macro_f1": 0.71, "balanced_accuracy": 0.71, "log_loss": 0.77}},
        "tuned_random_forest": {"metrics_mean": {"macro_f1": 0.79, "balanced_accuracy": 0.78, "log_loss": 0.63}},
        "tuned_hist_gradient_boosting": {"metrics_mean": {"macro_f1": 0.81, "balanced_accuracy": 0.80, "log_loss": 1.05}},
    }
    statuses = classify_candidates(
        evaluations,
        {
            "tuned_random_forest": {"high_confidence_error_rate": 0.02},
            "tuned_hist_gradient_boosting": {"high_confidence_error_rate": 0.13},
        },
    )
    final = choose_final_candidate(evaluations, statuses)
    assert set(statuses) == {"logistic_regression", "tuned_random_forest", "tuned_hist_gradient_boosting"}
    assert statuses["logistic_regression"] == "INCUMBENT_REFERENCE"
    assert statuses["tuned_random_forest"] == "SELECTABLE"
    assert statuses["tuned_hist_gradient_boosting"] == "SELECTABLE_WITH_LIMITATION"
    assert final == "tuned_random_forest"
    assert final in statuses
    assert final != "tuned_hist_gradient_boosting" or statuses[final] in {"SELECTABLE", "SELECTABLE_WITH_LIMITATION"}
