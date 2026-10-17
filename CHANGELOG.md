# Changelog

All notable changes to this project are documented here. Versions follow
[Semantic Versioning](https://semver.org/). The frozen model, its metrics and
the consumed holdout have not changed since v1.0.0.

## [1.5.0] - 2026-10-17

### Added
- MVP «Triaje de revisión humana» (demo mode «Triaje de revisión»): input template and row-level validation in Spanish; band weights for the reviewed sample; per-class confidence thresholds from a weighted logistic model of P(error); out-of-sample escape estimate with Jeffreys interval; audit sample and alarm; list of parts to review; Power BI export and DAX measures (`powerbi/dax/revision_humana.dax`). Example built from the real plates with out-of-sample predictions (`tools/build_review_example.py`). Pilot protocol in `docs/MVP_PILOTO.md`.
- «Señal de campo» theme and copyright footer in the demo.

### Changed
- This repository absorbs `steel-plates-quality-bi` as its reporting layer; the former repository points here.

## [1.4.0] - 2026-10-16

### Changed
- GitHub Actions updated by the maintainer: `actions/setup-python` v7, `actions/setup-node` v7, `github/codeql-action` v4; `pytest>=9.1.1`.

### Removed
- Dependabot configuration: dependency updates are reviewed and applied manually by the maintainer, so every commit has a single author.

### Added
- Project page on GitHub Pages and a live demo on Hugging Face Spaces, published automatically from `main`.
- Input-drift monitoring (`tools/drift_check.py`, `reports/ml/monitoring/drift.json`): PSI and out-of-range share per measurement against the training plates; the holdout passes, a unit change and a luminosity recalibration are flagged.
- Per-1,000-plates cost of each review policy for illustrative ratios R = 10 and 20 in `review_cost.json`, shown in the README and executive summaries.
- Executive summary in English and Spanish (`docs/EXECUTIVE_SUMMARY.md`, `docs/RESUMEN_EJECUTIVO.md`).
- Assumption-based cost sensitivity of the development-only review policy (`tools/review_cost.py`, `reports/ml/decision/review_cost.json`): break-even ranges of the miss-to-review cost ratio for perfect and imperfect reviewers, checked against brute force. No real costs, savings or new thresholds.

## [1.3.0] - 2026-10-14

### Added
- `steel-predict` command installable with `pip install .`.
- English README as the main entry point; Spanish version in `README.es.md`.
- Packaging tests (entry point, version consistency, license metadata, pinned dependencies).
- Community and governance: `CONTRIBUTING.md` with scientific-integrity rules, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `SECURITY.md` (pickle risk and private reporting), `CODEOWNERS`.
- Issue forms for bugs, data-quality findings and pre-registered experiment proposals; pull-request checklist that protects the frozen model and the consumed holdout.
- Automation: Dependabot (frozen scientific packages excluded), CodeQL code scanning, label sync, and a release workflow that attaches the verified ONNX model, manifest, Model Card and SHA256SUMS to every published release.

### Changed
- `streamlit` and `plotly` pinned to the versions validated in CI.
- CI runs on pull requests, on `main`, weekly and on demand, with concurrency control and read-only permissions.

### Fixed
- The PBIP `RutaCSV` default no longer contains the author's local path; it ships with a placeholder, and the Power BI preservation test allows only that documented change.

## [1.2.1] - 2026-10-14

### Added
- Apache-2.0 `LICENSE` and `NOTICE` with the CC BY 4.0 attribution of the UCI dataset.
- `CITATION.cff` (software and dataset citation) and this changelog.

### Changed
- Package version aligned with the published releases.

## [1.2.0] - 2026-10-14

### Added
- ONNX export of the frozen model, verified against scikit-learn (max probability difference 8.3e-7, same class and review status) and deterministic by SHA256.
- Node.js batch inference through ONNX Runtime (`examples/onnx-node`).

## [1.1.0] - 2026-10-14

### Added
- Docker image for the Python evidence layer; CI runs the checks and the full suite inside it.
- SQL data contract with dbt + DuckDB (56 checks), reconciled row by row with the Python audit and tested against five corruptions.

## [1.0.0] - 2026-10-14

### Added
- Frozen `tuned_random_forest`, evaluated once on the 389-row holdout: macro-F1 0.8147, balanced accuracy 0.8049, log-loss 0.6893.
- Model Card, evidence pack and clean-clone reproducibility (122 tests).

[1.3.0]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops/releases/tag/v1.0.0
