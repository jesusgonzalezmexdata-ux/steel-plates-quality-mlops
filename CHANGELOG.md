# Changelog

All notable changes to this project are documented here. Versions follow
[Semantic Versioning](https://semver.org/). The frozen model, its metrics and
the consumed holdout have not changed since v1.0.0.

## [1.3.0] - 2026-10-14

### Added
- `steel-predict` command installable with `pip install .`.
- English README as the main entry point; Spanish version in `README.es.md`.
- Packaging tests (entry point, version consistency, license metadata, pinned dependencies).

### Changed
- `streamlit` and `plotly` pinned to the versions validated in CI.

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

[1.3.0]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jesusgonzalezmexdata-ux/steel-plates-quality-mlops-/releases/tag/v1.0.0
