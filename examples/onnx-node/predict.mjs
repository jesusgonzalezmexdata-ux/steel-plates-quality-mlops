// Batch inference of the frozen model from Node.js through ONNX Runtime.
// Compares against the scikit-learn probabilities stored in reports/onnx/fixture.json.
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import * as ort from "onnxruntime-node";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const fixture = JSON.parse(await readFile(path.join(root, "reports/onnx/fixture.json"), "utf8"));
const session = await ort.InferenceSession.create(path.join(root, "artifacts/onnx/final_random_forest.onnx"));

const n = fixture.rows.length;
const input = new ort.Tensor("float32", Float32Array.from(fixture.rows.flat()), [n, fixture.features.length]);
const { label, probabilities } = await session.run({ input });

let maxDiff = 0;
for (let i = 0; i < n; i++) {
  const expected = fixture.expected_probabilities[i];
  const observed = Array.from(probabilities.data.slice(i * expected.length, (i + 1) * expected.length));
  observed.forEach((p, k) => { maxDiff = Math.max(maxDiff, Math.abs(p - expected[k])); });
  const top = expected.indexOf(Math.max(...expected));
  if (label.data[i] !== fixture.classes[top]) throw new Error(`row ${i}: class ${label.data[i]} != ${fixture.classes[top]}`);
  console.log(`row ${i}: ${label.data[i]} (p=${Math.max(...observed).toFixed(4)})`);
}
if (maxDiff > fixture.atol) throw new Error(`max probability diff ${maxDiff} > ${fixture.atol}`);
console.log(JSON.stringify({ status: "PASS", rows: n, max_abs_probability_diff: maxDiff }));
