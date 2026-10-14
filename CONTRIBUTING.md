# Contributing

Thank you for your interest. This repository is a reproducible scientific case, so contributions follow the same discipline as the original work: **evidence first, frozen results protected**.

## What is welcome

- Bug reports and fixes in code, tests, CI, Docker, dbt or ONNX tooling.
- Documentation improvements and translations.
- Reproducibility reports on other platforms (OS, Python build).
- New analyses that **do not** change the frozen model or reuse the holdout for decisions.

## What is out of scope

The final model (`tuned_random_forest`, rf-phase8-v1), its metrics and the 389-row holdout are frozen. The holdout was consumed by a single final evaluation (`HOLDOUT_STATUS = CONSUMED_FINAL_EVALUATION`). Pull requests that retune, recalibrate, swap the model, change features or report new holdout scores will be declined, because they would invalidate the evidence. A genuinely new model needs **new, independent data**; propose it first as an *Experiment proposal* issue.

## Workflow

1. **Open an issue** with the matching template (bug, data quality or experiment proposal) and wait for agreement before large changes.
2. **Branch** from `main`: `fix/...`, `feat/...`, `docs/...`, `chore/...`.
3. **Set up** Python 3.13 and run, from the repository root:
   ```bash
   pip install -r requirements-dev.txt
   python -B -m tools.project_checks lint
   python -B -m tools.project_checks validate-data
   python -B -m pytest -q
   ```
   Touching `dbt/` or `tools/data_contract.py`: also `pip install -r requirements-dbt.txt` and `python -B -m tools.data_contract`.
   Touching ONNX code: `pip install -r requirements-onnx.txt` and `python -B -m tools.export_onnx --check`.
4. **Commit** with [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `build:`, `chore:`), one logical change per commit.
5. **Open a pull request** and complete its checklist. All CI jobs must pass.

## Scientific integrity rules

- Never relax a test or a tolerance to make CI pass; explain and fix the cause.
- Any new number in documentation must be reproducible by a command in the repository.
- Keep claims within scope: full-observation classification, no early prediction, no causal or financial claims.
- Record platform-dependent behavior explicitly rather than hiding it.

By contributing you agree that your contribution is licensed under the Apache License 2.0 and that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
