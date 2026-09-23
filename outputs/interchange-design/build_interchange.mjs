// Run with NODE_PATH set to the bundled Codex Node packages.
import crypto from "node:crypto";
import fs from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { FileBlob, SpreadsheetFile } = require("@oai/artifact-tool");

const outputDir = path.dirname(fileURLToPath(import.meta.url));
const policyPath = path.resolve(outputDir, "../../archive/interchange/references/policy.json");
const outputPath = `${outputDir}/interchange.xlsx`;
const previewDir = await fs.mkdtemp(path.join(os.tmpdir(), "interchange-workbook-"));
const policyBytes = await fs.readFile(policyPath);
const policy = JSON.parse(policyBytes.toString("utf8"));

const colors = {
  blue: "#D9EAF7",
  paleGreen: "#E2F0D9",
  paleAmber: "#FFF2CC",
  line: "#9FBAD0",
  grid: "#D9E2F3",
  text: "#1F2937",
};
const font = "Arial";

function displayHouse(house) {
  return {
    codex: "Codex",
    opencode: "OpenCode / Go pool",
    claude: "Claude",
    grok: "Grok",
  }[house] ?? house;
}

function profileEvidenceState(profile) {
  if (profile.house === "grok") {
    return "CLI model and effort documented; exact runtime unverified";
  }
  if (profile.house === "claude") {
    return "Profile documented; exact runtime unverified";
  }
  if (profile.evidence.includes("smoke-tested")) {
    return "Smoke-tested";
  }
  return "Supported by metadata; routing unverified";
}

function setSourceReference(sheet, labelColumn, valueColumn, status = false) {
  sheet.getRange("A3").values = [[`Policy source: Interchange policy v${policy.version}`]];
  sheet.getRange(`${labelColumn}3`).values = [["Approved on"]];
  sheet.getRange(`${valueColumn}3`).values = [[new Date(`${policy.approved_on}T00:00:00`)]];
  sheet.getRange(`${valueColumn}3`).format.numberFormat = "yyyy-mm-dd";
  if (status) {
    sheet.getRange("G3").values = [[policy.status]];
  }
}

function addSection(sheet, address, label, endColumn) {
  const row = address.match(/\d+/)[0];
  sheet.getRange(address).values = [[label]];
  const range = sheet.getRange(`${address}:${endColumn}${row}`);
  range.format.fill = colors.blue;
  range.format.font = { name: font, size: 10, bold: true, color: colors.text };
  range.format.borders = { preset: "outside", style: "thin", color: colors.line };
}

function addHeader(sheet, address) {
  const range = sheet.getRange(address);
  range.format.fill = "#1F4E78";
  range.format.font = { name: font, size: 10, bold: true, color: "#FFFFFF" };
  range.format.horizontalAlignment = "center";
  range.format.verticalAlignment = "center";
  range.format.wrapText = true;
  range.format.borders = { preset: "inside", style: "thin", color: "#FFFFFF" };
}

function addBodyBorders(sheet, address) {
  sheet.getRange(address).format.borders = {
    insideHorizontal: { style: "thin", color: colors.grid },
    bottom: { style: "thin", color: colors.grid },
  };
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const profiles = workbook.worksheets.getItem("Profiles");
const routing = workbook.worksheets.getItem("Routing");
const monitoring = workbook.worksheets.getItem("Monitoring");
const governance = workbook.worksheets.getItem("Governance & Recovery");

setSourceReference(profiles, "D", "E", true);
setSourceReference(routing, "C", "D");
setSourceReference(monitoring, "B", "C");
setSourceReference(governance, "B", "C");

// Profiles: refresh the configured roster, retaining its register layout.
const profileEndRow = 15 + policy.profiles.length;
profiles.getRange("A8:C11").values = [
  ["Allowed fixed profiles", null, "Select only when the assigned role, pool, and task fit."],
  ["Smoke-tested fixed profiles", null, "Smoke tests show CLI or session operation. They do not establish comparative quality."],
  ["Documented profiles pending exact runtime check", null, "Grok, Opus and Fable entries must not be treated as smoke-tested profiles."],
  ["Routing calibration", "Unverified", "Do not infer speed, cost, or quality estimates from this workbook."],
];
profiles.getRange("B8").formulas = [[`=COUNTIFS($G$16:$G$${profileEndRow},"Allowed fixed profile")`]];
profiles.getRange("B9").formulas = [[`=COUNTIFS($H$16:$H$${profileEndRow},"Smoke-tested")`]];
profiles.getRange("B10").formulas = [[`=COUNTIFS($H$16:$H$${profileEndRow},"CLI model and effort documented; exact runtime unverified")+COUNTIFS($H$16:$H$${profileEndRow},"Profile documented; exact runtime unverified")`]];
profiles.getRange("B8:B10").format.numberFormat = "#,##0";
profiles.getRange("A8:C11").format.rowHeight = 42;

profiles.getRange(`A16:I${profileEndRow}`).values = policy.profiles.map((profile) => [
  profile.id,
  displayHouse(profile.house),
  profile.model,
  profile.effort,
  profile.role,
  profile.delegation ? "Yes" : "No",
  "Allowed fixed profile",
  profileEvidenceState(profile),
  profile.evidence,
]);
profiles.getRange(`A16:I${profileEndRow}`).format.font = { name: font, size: 10, color: colors.text };
profiles.getRange(`A16:I${profileEndRow}`).format.verticalAlignment = "center";
profiles.getRange(`A16:I${profileEndRow}`).format.wrapText = true;
profiles.getRange(`A16:I${profileEndRow}`).format.rowHeight = 38;
for (const [index, profile] of policy.profiles.entries()) {
  if (profile.id.startsWith("brainstorm-")) profiles.getRange(`A${16 + index}:I${16 + index}`).format.rowHeight = 76;
}
profiles.getRange(`F16:F${profileEndRow}`).format.horizontalAlignment = "center";
profiles.getRange(`G16:G${profileEndRow}`).format.fill = colors.paleGreen;
profiles.getRange(`G16:G${profileEndRow}`).format.font = { name: font, size: 10, bold: true, color: colors.text };
profiles.getRange(`H16:H${profileEndRow}`).format.fill = colors.paleAmber;
for (let row = 16; row <= profileEndRow; row += 1) {
  const state = profileEvidenceState(policy.profiles[row - 16]);
  if (state === "Smoke-tested") {
    profiles.getRange(`H${row}`).format.fill = colors.paleGreen;
  } else {
    profiles.getRange(`H${row}`).format.fill = colors.paleAmber;
  }
}
addBodyBorders(profiles, `A16:I${profileEndRow}`);

// Routing: replace policy rules and add the requested readable selection rules section.
routing.unmergeCells("A8:D60");
routing.getRange("A8:D60").clear({ applyTo: "all" });
const routingEndRow = 7 + policy.routing.length;
routing.getRange(`A8:D${routingEndRow}`).values = policy.routing.map((rule) => [
  rule.task,
  rule.first,
  rule.fallback,
  rule.reason,
]);
routing.getRange(`A8:D${routingEndRow}`).format.font = { name: font, size: 10, color: colors.text };
routing.getRange(`A8:D${routingEndRow}`).format.verticalAlignment = "center";
routing.getRange(`A8:D${routingEndRow}`).format.wrapText = true;
routing.getRange(`A8:D${routingEndRow}`).format.rowHeight = 46;
addBodyBorders(routing, `A8:D${routingEndRow}`);

const selectionTitleRow = routingEndRow + 3;
const selectionHeaderRow = selectionTitleRow + 1;
const selectionStartRow = selectionHeaderRow + 1;
const selectionEndRow = selectionHeaderRow + policy.selection_rules.length;
addSection(routing, `A${selectionTitleRow}`, "Selection rules", "D");
for (let row = selectionHeaderRow; row <= selectionEndRow; row += 1) {
  routing.unmergeCells(`B${row}:D${row}`);
}
routing.mergeCells(`A${selectionHeaderRow}:D${selectionHeaderRow}`);
routing.getRange(`A${selectionHeaderRow}`).values = [["Approved selection rule"]];
addHeader(routing, `A${selectionHeaderRow}:D${selectionHeaderRow}`);
for (let row = selectionStartRow; row <= selectionEndRow; row += 1) {
  routing.mergeCells(`A${row}:D${row}`);
}
routing.getRange(`A${selectionStartRow}:A${selectionEndRow}`).values = policy.selection_rules.map((rule, index) => [`${index + 1}. ${rule}`]);
routing.getRange(`A${selectionStartRow}:D${selectionEndRow}`).format.font = { name: font, size: 10, color: colors.text };
routing.getRange(`A${selectionStartRow}:D${selectionEndRow}`).format.verticalAlignment = "center";
routing.getRange(`A${selectionStartRow}:A${selectionEndRow}`).format.horizontalAlignment = "left";
routing.getRange(`A${selectionStartRow}:A${selectionEndRow}`).format.wrapText = true;
routing.getRange(`A${selectionStartRow}:D${selectionEndRow}`).format.rowHeight = 42;
addBodyBorders(routing, `A${selectionStartRow}:D${selectionEndRow}`);

// Monitoring: refresh policy rows and retain the existing three-column layout.
monitoring.unmergeCells("A8:C60");
monitoring.getRange("A8:C60").clear({ applyTo: "all" });
const monitoringEndRow = 7 + policy.monitoring.length;
monitoring.getRange(`A8:C${monitoringEndRow}`).values = policy.monitoring.map((item) => [
  item.rule,
  item.value,
  item.meaning,
]);
monitoring.getRange(`A8:C${monitoringEndRow}`).format.font = { name: font, size: 10, color: colors.text };
monitoring.getRange(`A8:C${monitoringEndRow}`).format.verticalAlignment = "center";
monitoring.getRange(`A8:C${monitoringEndRow}`).format.wrapText = true;
monitoring.getRange(`A8:C${monitoringEndRow}`).format.rowHeight = 50;
addBodyBorders(monitoring, `A8:C${monitoringEndRow}`);

// Governance and recovery: rebuild both policy-backed sections in place.
governance.unmergeCells("A8:C80");
governance.getRange("A8:C80").clear({ applyTo: "all" });
const governanceEndRow = 7 + policy.governance.length;
governance.getRange(`A8:B${governanceEndRow}`).values = policy.governance.map((item) => [
  item.rule,
  item.policy,
]);
governance.getRange(`A8:B${governanceEndRow}`).format.font = { name: font, size: 10, color: colors.text };
governance.getRange(`A8:B${governanceEndRow}`).format.verticalAlignment = "center";
governance.getRange(`A8:B${governanceEndRow}`).format.wrapText = true;
governance.getRange(`A8:B${governanceEndRow}`).format.rowHeight = 48;
addBodyBorders(governance, `A8:B${governanceEndRow}`);

const recoveryTitleRow = governanceEndRow + 3;
const recoveryHeaderRow = recoveryTitleRow + 1;
const recoveryStartRow = recoveryHeaderRow + 1;
const recoveryEndRow = recoveryHeaderRow + policy.recovery.length;
addSection(governance, `A${recoveryTitleRow}`, "Recovery playbook", "C");
governance.getRange(`A${recoveryHeaderRow}:C${recoveryHeaderRow}`).values = [[
  "Failure",
  "First action",
  "Escalation",
]];
addHeader(governance, `A${recoveryHeaderRow}:C${recoveryHeaderRow}`);
governance.getRange(`A${recoveryStartRow}:C${recoveryEndRow}`).values = policy.recovery.map((item) => [
  item.failure,
  item.action,
  item.escalation,
]);
governance.getRange(`A${recoveryStartRow}:C${recoveryEndRow}`).format.font = { name: font, size: 10, color: colors.text };
governance.getRange(`A${recoveryStartRow}:C${recoveryEndRow}`).format.verticalAlignment = "center";
governance.getRange(`A${recoveryStartRow}:C${recoveryEndRow}`).format.wrapText = true;
governance.getRange(`A${recoveryStartRow}:C${recoveryEndRow}`).format.rowHeight = 56;
addBodyBorders(governance, `A${recoveryStartRow}:C${recoveryEndRow}`);

workbook.recalculate();

const validation = {};
for (const [sheetName, range] of [
  ["Profiles", `A1:I${profileEndRow}`],
  ["Routing", `A1:D${selectionEndRow}`],
  ["Monitoring", `A1:C${monitoringEndRow}`],
  ["Governance & Recovery", `A1:C${recoveryEndRow}`],
]) {
  const inspected = await workbook.inspect({
    kind: "table",
    range: `${sheetName}!${range}`,
    include: "values,formulas",
    tableMaxRows: 60,
    tableMaxCols: 12,
  });
  validation[sheetName] = inspected.ndjson;
}
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
validation.formulaErrors = errors.ndjson;

await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName, range] of [
  ["Profiles", `A1:I${profileEndRow}`],
  ["Routing", `A1:D${selectionEndRow}`],
  ["Monitoring", `A1:C${monitoringEndRow}`],
  ["Governance & Recovery", `A1:C${recoveryEndRow}`],
]) {
  const preview = await workbook.render({ sheetName, range, scale: 1.25, format: "png" });
  const name = sheetName.replace(/[^a-z0-9]+/gi, "_").toLowerCase();
  await fs.writeFile(`${previewDir}/${name}.png`, new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);

const saved = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
validation.savedSheets = (await saved.inspect({ kind: "sheet", include: "id,name" })).ndjson;
await fs.writeFile(path.join(previewDir, "validation.json"), JSON.stringify(validation, null, 2));

const workbookHash = crypto.createHash("sha256").update(await fs.readFile(outputPath)).digest("hex");
const policyHash = crypto.createHash("sha256").update(policyBytes).digest("hex");
console.log(JSON.stringify({ outputPath, previewDir, policyHash, workbookHash, selectionRules: policy.selection_rules.length }, null, 2));
