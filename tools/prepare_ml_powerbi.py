"""Build the additive ML PBIR/TMDL draft from existing repository structures."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from quality_ml.inference.artifact import write_json
from quality_ml.inference.bi_export import BASELINE_PATH, COLUMNS

PROJECT = "powerbi/project/steel-plates-quality-bi"
REPORT = PROJECT + ".Report/definition/pages"
SEMANTIC = PROJECT + ".SemanticModel/definition"
PAGE = "ml_performance_review"
TABLE = "ML_Holdout"


def prepare(root=ROOT):
    root = Path(root)
    if not (root / BASELINE_PATH).exists():
        raise ValueError("Capture PRE_ML_POWER_BI_HASHES before any BI edits")
    base = root / REPORT
    templates = {
        "card": "5ee9939d0101076d3381/visuals/083e0e977408b7b77e25/visual.json",
        "table": "f50491653678cb19a699/visuals/53f9fbf278a14f1de6b6/visual.json",
        "slicer": "1f75dde540a696f2b18f/visuals/a3a0702d79cc235356ad/visual.json",
        "text": "1f75dde540a696f2b18f/visuals/b8db3c0b614b3b22017e/visual.json",
    }
    templates = {k: json.loads((base / v).read_text(encoding="utf-8-sig"))
                 for k, v in templates.items()}
    page = json.loads((base / "5ee9939d0101076d3381/page.json").read_text(encoding="utf-8-sig"))
    page.update(name=PAGE, displayName="MODEL PERFORMANCE & REVIEW", height=1040)
    page.pop("pageBinding", None)
    write_json(base / PAGE / "page.json", page)

    def field(name, measure=False):
        return {("Measure" if measure else "Column"): {
            "Expression": {"SourceRef": {"Entity": TABLE}}, "Property": name}}

    def visual(key, kind, fields, x, y, w, h, order):
        item = copy.deepcopy(templates[kind])
        identity = hashlib.sha256(key.encode()).hexdigest()[:20]
        item["name"] = identity
        item["position"] = dict(x=x, y=y, width=w, height=h, z=order, tabOrder=order)
        item.pop("filterConfig", None)
        view = item["visual"]
        # Retain the established visual type and query role; remove legacy bindings.
        view.pop("objects", None)
        view.pop("visualContainerObjects", None)
        role = "Data" if kind == "card" else "Values"
        projections = [dict(field=field(name, measure),
            queryRef=f"{TABLE}.{name}", nativeQueryRef=name) for name, measure in fields]
        view["query"] = dict(queryState={role: dict(projections=projections)})
        write_json(base / PAGE / "visuals" / identity / "visual.json", item)

    text = copy.deepcopy(templates["text"])
    text["name"] = hashlib.sha256(b"ml-context").hexdigest()[:20]
    text["position"] = dict(x=20, y=10, width=1240, height=95, z=0, tabOrder=0)
    text["visual"].pop("visualContainerObjects", None)
    run = text["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
    run["value"] = ("FINAL HOLDOUT: 389 known-defect observations. Full-observation classification. "
        "Review is a development-only candidate, applied post-hoc: confidence >=0.80 high; "
        "0.50-0.80 review; <0.50 low (also review). Final scores always refer to all 389 rows; "
        "other visuals follow ML filters. Small segments are descriptive; no prospective validation.")
    run["textStyle"]["fontSize"] = "14px"
    run["textStyle"]["fontStyle"] = "normal"
    write_json(base / PAGE / "visuals" / text["name"] / "visual.json", text)
    for i, measure in enumerate(["Final Macro-F1 (389)", "Final Balanced Accuracy (389)",
                                  "Candidate Review Rate", "ML Rows"]):
        visual("card-" + measure, "card", [(measure, True)], 20 + 310*i, 115, 290, 110, i+1)
    for i, column in enumerate(["steel_type", "steel_plate_thickness", "actual_defect"]):
        visual("filter-" + column, "slicer", [(column, False)], 20+415*i, 240, 395, 170, i+5)
    visual("confusions", "table", [("actual_defect", False), ("predicted_defect", False),
        ("ML Confusion Errors", True)], 20, 430, 600, 250, 8)
    visual("class-error", "table", [("actual_defect", False), ("ML Rows", True),
        ("ML Errors", True), ("Observed Error Rate", True), ("Segment Support", True)],
        640, 430, 620, 250, 9)
    visual("confidence", "table", [("confidence_bin", False), ("ML Rows", True),
        ("Mean Confidence", True), ("Observed Accuracy", True), ("Segment Support", True)],
        20, 700, 600, 300, 10)
    visual("review", "table", [("review_status", False), ("ML Rows", True),
        ("ML Errors", True), ("Observed Error Rate", True)],
        640, 700, 620, 300, 11)

    index_path = base / "pages.json"
    index = json.loads(index_path.read_text(encoding="utf-8-sig"))
    if PAGE not in index["pageOrder"]:
        index["pageOrder"].append(PAGE)
    write_json(index_path, index)

    metrics = json.loads((root / "reports/ml/final_holdout/metrics.json").read_text())["metrics"]
    measures = {
        "Final Macro-F1 (389)": (repr(metrics["macro_f1"]), "0.0000"),
        "Final Balanced Accuracy (389)": (repr(metrics["balanced_accuracy"]), "0.0000"),
        "ML Rows": ("COUNTROWS ( ML_Holdout )", "0"),
        "ML Correct": ("SUM ( ML_Holdout[correct_prediction] )", "0"),
        "ML Errors": ("[ML Rows] - [ML Correct]", "0"),
        "ML Confusion Errors": ("IF ( [ML Errors] > 0, [ML Errors], BLANK () )", "0"),
        "ML Review Rows": ("SUM ( ML_Holdout[review_required] )", "0"),
        "Candidate Review Rate": ("DIVIDE ( [ML Review Rows], [ML Rows] )", "0.00%"),
        "Observed Accuracy": ("DIVIDE ( [ML Correct], [ML Rows] )", "0.00%"),
        "Observed Error Rate": ("DIVIDE ( [ML Errors], [ML Rows] )", "0.00%"),
        "Mean Confidence": ("AVERAGE ( ML_Holdout[confidence] )", "0.00%"),
        "Segment Support": ('IF ( [ML Rows] < 30, "INSUFFICIENT_DATA", "DESCRIPTIVE" )', None),
    }
    number = {"row_id": "int64", "source_id": "int64", "correct_prediction": "int64",
              "confidence": "double", "review_required": "int64",
              "steel_plate_thickness": "double", "pixels_area": "double"}
    lines = ["table ML_Holdout"]
    for name, (expression, format_string) in measures.items():
        lines += ["", f"\tmeasure '{name}' = {expression}"]
        if format_string:
            lines += [f"\t\tformatString: {format_string}"]
    for name in COLUMNS:
        lines += ["", f"\tcolumn {name}", f"\t\tdataType: {number.get(name, 'string')}",
                  "\t\tsummarizeBy: none", f"\t\tsourceColumn: {name}"]
    headers = ", ".join(f'"{name}"' for name in COLUMNS)
    conversions = ", ".join('{"' + name + '", ' +
        ("Int64.Type" if number.get(name) == "int64" else "type number" if name in number else "type text") + "}"
        for name in COLUMNS)
    query = (
        'let\n'
        '    Origen = Csv.Document(File.Contents(RutaMLCSV), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
        '    Cabecera = Table.PromoteHeaders(Origen, [PromoteAllScalars=true]),\n'
        f'    Esperadas = {{{headers}}},\n'
        '    Schema = if List.Sort(Table.ColumnNames(Cabecera)) = List.Sort(Esperadas) then Cabecera else error "ML schema mismatch",\n'
        f'    Tipos = Table.TransformColumnTypes(Schema, {{{conversions}}}, "en-US"),\n'
        '    Validado = if Table.RowCount(Tipos) = 389 and List.Distinct(Tipos[dataset_role]) = {"FINAL_HOLDOUT_EVALUATION"}\n'
        '        then Tipos else error "Expected 389 final holdout evaluation rows"\n'
        'in\n'
        '    Validado'
    )
    lines += ["", "\tpartition ML_Holdout = m", "\t\tmode: import", "\t\tsource ="]
    lines += ["\t\t\t\t" + line for line in query.splitlines()]
    target = root / SEMANTIC / "tables/ML_Holdout.tmdl"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    # Append only; existing model definitions remain byte-for-byte prefixes.
    model_path = root / SEMANTIC / "model.tmdl"
    model_data = model_path.read_bytes()
    if b"ref table ML_Holdout" not in model_data:
        model_path.write_bytes(model_data + b"\nref table ML_Holdout\n")
    expression_path = root / SEMANTIC / "expressions.tmdl"
    expression_data = expression_path.read_bytes()
    if b"expression RutaMLCSV =" not in expression_data:
        addition = ('\nexpression RutaMLCSV =\n'
            '\t\tlet\n'
            '\t\t    Normalized = Text.Replace(Text.Trim(RutaCSV), "\\", "/"),\n'
            '\t\t    Root = if Text.Contains(Normalized, "/data/raw/") then Text.BeforeDelimiter(Normalized, "/data/raw/")\n'
            '\t\t        else error "Set RutaCSV to this repository data/raw/steel_plates_faults.csv",\n'
            '\t\t    Result = Root & "/powerbi/data/ml_holdout_evaluation.csv"\n'
            '\t\tin\n'
            '\t\t    Result\n')
        expression_path.write_bytes(expression_data + addition.encode("utf-8"))
    return dict(status="TEXT_DRAFT_CREATED", page=PAGE, visuals=12,
                runtime_validation="PENDING_DESKTOP")


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))