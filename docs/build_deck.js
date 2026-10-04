// FreshMart — Sprint 0 design review deck (structured: theme + layouts + sections)
const pptxgen = require("pptxgenjs");
const path = require("path");
const SKILL = "/root/.claude/skills/synced/336b45b9-5340-4591-98bf-ee639cfb736b_2ed94907-79b7-4ced-967a-ad4e398d37f8/pptx";
const { applyTheme } = require(path.join(SKILL, "scripts/apply_theme.js"));

const THEME = {
  name: "FreshMart Market",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2A22", lt1: "FFFFFF", dk2: "1F4D3A", lt2: "EEF4EC",
    accent1: "2E7D4F",  // market green
    accent2: "8CC63F",  // fresh lime
    accent3: "E8A317",  // amber (spike)
    accent4: "C0392B",  // red (drop)
    accent5: "5B6B63",  // muted slate-green
    accent6: "D6E6D3",  // pale green
    hlink: "2E7D4F", folHlink: "5B6B63",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "FreshMart Store Performance Platform - Sprint 0 Design";
pres.author = "NSUT Team";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const W = 13.33;

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "FM Title",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.3, w: 11.7, h: 1.4,
        fontSize: 44, bold: true, color: C.background1, fontFace: "Cambria", valign: "bottom", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.85, w: 11.7, h: 1.6,
        fontSize: 20, color: C.accent6, valign: "top", align: "left" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "FM Content",
  background: { color: C.background1 },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85,
        fontSize: 36, bold: true, color: C.text2, fontFace: "Cambria", valign: "middle", margin: 0, align: "left" }, text: "" } },
    { text: { text: "FreshMart · Sprint 0 design review", options: { x: 0.6, y: 7.0, w: 6, h: 0.3,
        fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
});

// ---------------------------------------------------------------- helpers
let n = 0;
const nm = (s) => `${s}-${++n}`;
function card(slide, x, y, w, h, fill = C.background2) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill },
    rectRadius: 0.08, objectName: nm("card") });
}
function txt(slide, text, opts) {
  slide.addText(text, { isTextBox: true, margin: 0, valign: "top", fontSize: 15, color: C.text1,
    objectName: nm("text"), ...opts });
}
function pill(slide, x, y, w, label, fill, color = C.background1) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.38, fill: { color: fill }, line: { color: fill },
    rectRadius: 0.19, objectName: nm("pill") });
  txt(slide, label, { x, y, w, h: 0.38, fontSize: 12, bold: true, color, align: "center", valign: "middle" });
}
function bullets(items, size = 15) {
  return items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, paraSpaceAfter: 6, fontSize: size,
    breakLine: i < items.length - 1 } }));
}
function table(slide, header, rows, opts) {
  const head = header.map((h) => ({ text: h, options: { bold: true, color: C.background1, fill: { color: C.text2 } } }));
  const body = rows.map((r, ri) => r.map((c) => ({ text: c, options: {
    fill: { color: ri % 2 ? C.background1 : C.background2 } } })));
  slide.addTable([head, ...body], { fontSize: 13, color: C.text1, border: { type: "solid", pt: 0.5, color: HEX.accent6 },
    margin: [0.06, 0.1, 0.06, 0.1], valign: "middle", objectName: nm("table"), ...opts });
}
function arrow(slide, x1, y1, x2, y2) {
  slide.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001,
    h: Math.abs(y2 - y1) || 0.001, flipV: y2 < y1, line: { color: C.accent5, width: 2, endArrowType: "triangle" },
    objectName: nm("arrow") });
}

// ================================================================ 1. Title
pres.addSection({ title: "Opening" });
let s = pres.addSlide({ masterName: "FM Title", sectionTitle: "Opening" });
s.addText("FreshMart Store Performance Platform", { placeholder: "title" });
s.addText("Sprint 0 · Technical design & MVP plan for SME sign-off\nNSUT · Team of 4", { placeholder: "body" });
pill(s, 0.8, 1.6, 2.6, "AWS · Python · MySQL", C.accent2, C.text1);
s.addNotes("Introduce the team and the goal of this session: walk through our understanding, design and plan, and get sign-off on the MVP scope.");

// ================================================================ 2. Problem
pres.addSection({ title: "Problem" });
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Problem" });
s.addText("Management sees store sales 2-3 days late", { placeholder: "title" });
const stats = [["45", "stores email a CSV every night"], ["2-3 days", "to merge them by hand in Excel"], ["4", "recurring data-quality problems"]];
stats.forEach(([big, small], i) => {
  const x = 0.6 + i * 4.1;
  card(s, x, 1.5, 3.8, 2.1);
  txt(s, big, { x: x + 0.3, y: 1.75, w: 3.2, h: 0.95, fontSize: 48, bold: true, color: i === 1 ? C.accent4 : C.accent1, fontFace: "Cambria" });
  txt(s, small, { x: x + 0.3, y: 2.75, w: 3.2, h: 0.6, fontSize: 15, color: C.accent5 });
});
txt(s, "Data issues: duplicate transactions · mixed date formats · inconsistent product names · missing values",
  { x: 0.6, y: 3.9, w: 12.1, h: 0.4, fontSize: 15, color: C.text1 });
card(s, 0.6, 4.6, 12.1, 1.9, C.text2);
txt(s, "Business objective", { x: 0.95, y: 4.85, w: 11.4, h: 0.4, fontSize: 16, bold: true, color: C.accent2 });
txt(s, "Turn raw store files into clean, trusted, next-morning insights automatically, and flag stores whose sales are unusual so managers can act the same day.",
  { x: 0.95, y: 5.3, w: 11.4, h: 1.0, fontSize: 20, color: C.background1 });
s.addNotes("State the pain in numbers first, then the objective in one sentence. Emphasise: next-morning freshness and trusted data are the two outcomes.");

// ================================================================ 3. Users & requirements
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Problem" });
s.addText("Who uses it and what it must do", { placeholder: "title" });
const users = [["Store billing systems", "Produce one sales CSV per store per night"],
  ["Regional managers & head office", "Read the dashboard every morning, act on alerts"],
  ["Data team", "Runs and monitors the pipeline"]];
users.forEach(([t, d], i) => {
  const y = 1.45 + i * 1.65;
  card(s, 0.6, y, 4.3, 1.4);
  txt(s, t, { x: 0.85, y: y + 0.25, w: 3.9, h: 0.4, fontSize: 17, bold: true, color: C.text2 });
  txt(s, d, { x: 0.85, y: y + 0.72, w: 3.9, h: 0.45, fontSize: 14, color: C.accent5 });
});
txt(s, "Functional requirements", { x: 5.4, y: 1.45, w: 3.6, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
txt(s, bullets(["Ingest nightly CSVs from every store", "Validate, clean and de-duplicate", "Store clean data in a queryable DB",
  "Revenue by store, region, category; top products", "Flag unusual store-days", "Never double-count a re-uploaded file"], 16),
  { x: 5.4, y: 2.05, w: 3.7, h: 4.4 });
txt(s, "Non-functional", { x: 9.4, y: 1.45, w: 3.3, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
txt(s, bullets(["Freshness: by next morning", "Security: nothing public, least privilege", "Reliability: bad rows never break a load",
  "Scalable: more stores without redesign", "Low cost: small instances, tear down"], 16),
  { x: 9.4, y: 2.05, w: 3.3, h: 4.4 });
s.addNotes("Users first, then what the system must do, then the qualities it must have. The non-functional list drives our security and scaling choices later.");

// ================================================================ 4. Clarifications
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Problem" });
s.addText("What we clarified, and what we assumed", { placeholder: "title" });
table(s, ["Question we asked", "SME answer", "Design impact"], [
  ["Data volume?", "~2-5k transactions per store per day", "Pandas is enough, no Spark"],
  ["How fresh must data be?", "Next morning is fine", "Nightly batch, not streaming"],
  ["Is product ID always present?", "Sometimes missing; names vary", "Match on cleaned product name"],
  ["What is 'unusual'?", "Your call, justify it", "Per-store z-score + 30% rule"],
  ["Same file uploaded twice?", "Must not double-count", "Audit table + primary key"],
], { x: 0.6, y: 1.45, w: 8.0, colW: [2.5, 2.9, 2.6], rowH: 0.7, fontSize: 14 });
card(s, 9.0, 1.45, 3.7, 4.2, C.background2);
txt(s, "Assumptions", { x: 9.3, y: 1.65, w: 3.1, h: 0.4, fontSize: 18, bold: true, color: C.text2 });
txt(s, bullets(["Stores upload files to S3 (we simulate it)", "30 days of history available", "Daily data fits in memory",
  "Dashboard users are internal"], 15), { x: 9.3, y: 2.15, w: 3.1, h: 2.5 });
txt(s, "If wrong: only ingestion or processing changes, storage and DB stay.", { x: 9.3, y: 4.8, w: 3.1, h: 0.7, fontSize: 13, italic: true, color: C.accent5 });
s.addNotes("Show we asked about data, timing and edge cases, not about design choices. Each answer maps to a design decision on later slides.");

// ================================================================ 5. MVP scope
pres.addSection({ title: "Design" });
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Design" });
s.addText("MVP scope: what we build today", { placeholder: "title" });
const scope = [
  ["MUST HAVE", C.accent1, ["Raw files in S3", "Pandas ETL: clean + de-duplicate", "MySQL star schema on RDS", "Dashboard with core views", "Anomaly flags", "IAM role, private database"]],
  ["NICE TO HAVE", C.accent3, ["Auto-run ETL on upload (Lambda)", "Email alert on anomaly (SNS)", "LLM summary for managers", "CloudWatch alarms", "Dashboard login"]],
  ["NOT FOR MVP", C.accent5, ["Real-time streaming (Kinesis)", "PySpark / EMR cluster", "Kubernetes, microservices", "ML forecasting", "Multi-region"]],
];
scope.forEach(([label, color, items], i) => {
  const x = 0.6 + i * 4.1;
  card(s, x, 1.45, 3.8, 4.2);
  pill(s, x + 0.3, 1.75, 2.0, label, color);
  txt(s, bullets(items, 17), { x: x + 0.3, y: 2.45, w: 3.3, h: 3.0 });
});
s.addNotes("Ask the SMEs to confirm the MUST column. This is what we commit to demo. Nice-to-haves only if time allows.");

// ================================================================ 6. Architecture
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Design" });
s.addText("Architecture on AWS (ap-southeast-2)", { placeholder: "title" });
const boxes = [
  [0.6, 2.2, "Store CSVs", "45 stores, nightly", C.accent5],
  [3.15, 2.2, "Amazon S3", "raw/ landing zone", C.accent1],
  [5.7, 2.2, "EC2: Python ETL", "Pandas + NumPy", C.text2],
  [8.25, 2.2, "Amazon RDS", "MySQL, private", C.accent1],
  [10.8, 2.2, "Dashboard", "Streamlit on EC2", C.text2],
];
boxes.forEach(([x, y, t, d, fill]) => {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 1.95, h: 1.3, fill: { color: fill }, line: { color: fill }, rectRadius: 0.1, objectName: nm("box") });
  txt(s, t, { x: x + 0.1, y: y + 0.22, w: 1.75, h: 0.45, fontSize: 15, bold: true, color: C.background1, align: "center" });
  txt(s, d, { x: x + 0.1, y: y + 0.7, w: 1.75, h: 0.4, fontSize: 12, color: C.accent6, align: "center" });
});
[[2.55, 3.15], [5.1, 5.7], [7.65, 8.25], [10.2, 10.8]].forEach(([a, b]) => arrow(s, a, 2.85, b, 2.85));
// side outputs
card(s, 4.55, 4.25, 2.65, 0.9, C.background2);
txt(s, "S3 rejected/ + reason", { x: 4.7, y: 4.45, w: 2.35, h: 0.5, fontSize: 13, bold: true, color: C.accent4, align: "center" });
card(s, 7.45, 4.25, 2.65, 0.9, C.background2);
txt(s, "etl_audit + anomalies", { x: 7.6, y: 4.45, w: 2.35, h: 0.5, fontSize: 13, bold: true, color: C.text2, align: "center" });
arrow(s, 6.4, 3.5, 5.9, 4.25);
arrow(s, 6.9, 3.5, 8.6, 4.25);
// security strip of facts
const sec = [["IAM role", "no keys in code"], ["Security groups", "DB reachable only from EC2"], ["SSM Parameter Store", "encrypted DB secret"], ["Nightly timer", "ETL at 02:00"]];
sec.forEach(([t, d], i) => {
  const x = 0.6 + i * 3.075;
  card(s, x, 5.55, 2.85, 1.0, C.background2);
  txt(s, t, { x: x + 0.2, y: 5.68, w: 2.45, h: 0.35, fontSize: 14, bold: true, color: C.text2 });
  txt(s, d, { x: x + 0.2, y: 6.05, w: 2.45, h: 0.35, fontSize: 12, color: C.accent5 });
});
txt(s, "Batch pipeline · one EC2 runs ETL and dashboard · RDS never public", { x: 0.6, y: 1.45, w: 12.1, h: 0.4, fontSize: 15, italic: true, color: C.accent5 });
s.addNotes("Walk left to right: files land in S3 untouched, EC2 cleans them, clean rows go to RDS, the dashboard reads only from RDS. Bad rows are kept with a reason. Then the four security and ops facts at the bottom.");

// ================================================================ 7. ETL / data quality
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Design" });
s.addText("How the ETL turns messy files into trusted data", { placeholder: "title" });
const steps = ["Skip if already loaded", "Read CSV from S3", "Clean & validate", "Save rows + audit in one transaction", "Write rejects with reason"];
steps.forEach((t, i) => {
  const x = 0.6 + i * 2.48;
  s.addShape(pres.shapes.OVAL, { x, y: 1.5, w: 0.55, h: 0.55, fill: { color: C.accent1 }, line: { color: C.accent1 }, objectName: nm("num") });
  txt(s, String(i + 1), { x, y: 1.5, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle" });
  txt(s, t, { x: x + 0.65, y: 1.48, w: 1.7, h: 0.65, fontSize: 13, color: C.text1, valign: "middle" });
});
table(s, ["Problem in the data", "Our fix"], [
  ["Duplicate rows", "drop_duplicates in Pandas + INSERT IGNORE on primary key"],
  ["3 date formats", "Try each known format explicitly; unknown = rejected"],
  ["'  BANANA-dozen '", "Normalise name, then match to product master"],
  ["Missing price", "Fill from product master list price"],
  ["Missing quantity", "Reject: we never guess sales"],
  ["Same file twice", "etl_audit table: file name is a primary key"],
], { x: 0.6, y: 2.55, w: 8.1, colW: [2.6, 5.5] });
card(s, 9.1, 2.55, 3.6, 3.85, C.text2);
txt(s, "Tested on 30 days of messy data", { x: 9.4, y: 2.8, w: 3.0, h: 0.6, fontSize: 15, bold: true, color: C.accent2 });
txt(s, [{ text: "90,386", options: { fontSize: 36, bold: true, color: C.background1, breakLine: true } },
        { text: "rows loaded", options: { fontSize: 13, color: C.accent6, breakLine: true } },
        { text: "947", options: { fontSize: 36, bold: true, color: C.background1, breakLine: true } },
        { text: "rejected with a reason", options: { fontSize: 13, color: C.accent6, breakLine: true } },
        { text: "1,823", options: { fontSize: 36, bold: true, color: C.background1, breakLine: true } },
        { text: "duplicates removed", options: { fontSize: 13, color: C.accent6 } }],
  { x: 9.4, y: 3.4, w: 3.0, h: 2.9, fontFace: "Calibri" });
s.addNotes("Key line: nothing is lost silently. Loaded + rejected equals exactly the unique transactions generated. The single transaction per file means a crash mid-load is safe to rerun.");

// ================================================================ 8. Tech decisions
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Design" });
s.addText("Technology choices and why", { placeholder: "title" });
table(s, ["Need", "Options", "Chosen", "Why, for this problem"], [
  ["Raw file storage", "S3 vs EC2 disk", "S3", "Cheap, durable, keeps originals for reprocessing"],
  ["Processing", "Pandas vs PySpark", "Pandas", "~225k rows/day fits in memory; Spark only at ~100x"],
  ["Run the ETL", "Lambda vs EC2", "EC2", "No 15-min limit or Pandas packaging; also hosts dashboard"],
  ["Database", "RDS MySQL vs DynamoDB", "RDS MySQL", "Relational data, needs JOIN + GROUP BY reports"],
  ["Dashboard", "Streamlit vs React + API", "Streamlit", "Python only, built in an hour; Matplotlib for trends"],
  ["DB secret", "Config file vs SSM", "SSM SecureString", "Encrypted, read by IAM role, never in code"],
], { x: 0.6, y: 1.5, w: 12.1, colW: [2.0, 2.6, 1.9, 5.6], fontSize: 15, rowH: 0.62 });
txt(s, "Principle: the simplest option that meets the requirement, with a clear path to scale.", { x: 0.6, y: 6.05, w: 12.1, h: 0.4, fontSize: 16, italic: true, color: C.accent1 });
s.addNotes("For each row say: we could have used X, but because of Y we chose Z; at scale we would switch to the other option.");

// ================================================================ 9. Database design
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Design" });
s.addText("Database: a star schema for fast reports", { placeholder: "title" });
function entity(x, y, w, title, fields, fill) {
  const h = 0.5 + fields.length * 0.34;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: C.background1 }, line: { color: fill, width: 1.5 }, rectRadius: 0.06, objectName: nm("entity") });
  s.addShape(pres.shapes.RECTANGLE, { x: x + 0.02, y: y + 0.02, w: w - 0.04, h: 0.42, fill: { color: fill }, line: { color: fill }, objectName: nm("entity-head") });
  txt(s, title, { x: x + 0.15, y: y + 0.05, w: w - 0.3, h: 0.38, fontSize: 14, bold: true, color: C.background1, valign: "middle" });
  txt(s, fields.map((f, i) => ({ text: f, options: { breakLine: i < fields.length - 1 } })), { x: x + 0.15, y: y + 0.52, w: w - 0.3, h: fields.length * 0.34, fontSize: 12, color: C.text1, paraSpaceAfter: 2 });
  return h;
}
entity(0.6, 1.6, 3.0, "dim_store", ["store_id  PK", "city", "region", "store_manager"], HEX.accent5);
entity(0.6, 4.0, 3.0, "dim_product", ["product_id  PK", "product_name", "category", "list_price"], HEX.accent5);
entity(4.5, 1.6, 3.4, "fact_sales", ["transaction_id  PK", "store_id  FK", "product_id  FK", "sale_date", "quantity, unit_price", "amount (precomputed)", "source_file (lineage)", "INDEX (sale_date, store_id)"], HEX.dk2);
arrow(s, 4.5, 2.6, 3.6, 2.4);
arrow(s, 4.5, 3.9, 3.6, 4.6);
entity(8.6, 1.6, 4.1, "sales_anomaly", ["store_id, sale_date  PK", "revenue, expected, z_score"], HEX.accent1);
entity(8.6, 3.35, 4.1, "etl_audit", ["file_name  PK  (blocks reloads)", "rows_read / loaded / rejected"], HEX.accent1);
txt(s, bullets(["DECIMAL for money, never FLOAT", "Primary key blocks duplicate sales", "Index matches the dashboard's filter"], 14), { x: 8.6, y: 5.1, w: 4.1, h: 1.4 });
s.addNotes("Fact table in the middle holds sales events; dimensions describe who and what. Point out lineage (source_file), the index and why money is DECIMAL.");

// ================================================================ 10. Anomaly detection (native chart)
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Design" });
s.addText("Flagging unusual sales: per-store z-score", { placeholder: "title" });
const days = ["17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30"];
const rev = [163.2, 174.5, 174.2, 158.3, 169.0, 163.2, 170.3, 172.6, 163.9, 147.9, 190.0, 170.0, 166.5, 473.1];
s.addChart(pres.charts.LINE, [{ name: "S003 daily revenue (Rs thousand)", labels: days, values: rev }], {
  x: 0.6, y: 1.45, w: 7.4, h: 4.9, chartColors: [HEX.accent1], lineSize: 3, lineDataSymbol: "circle", lineDataSymbolSize: 7,
  showTitle: true, title: "Store S003 revenue, 17-30 Sep (Rs thousand)", titleFontSize: 13, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
  showLegend: false, catAxisLabelColor: HEX.accent5, valAxisLabelColor: HEX.accent5, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
  catAxisLabelFontSize: 11, valAxisLabelFontSize: 11, valGridLine: { color: "E3ECE1", size: 0.75 }, catGridLine: { style: "none" },
  valAxisMinVal: 0, catAxisTitle: "September", showCatAxisTitle: true, catAxisTitleColor: HEX.accent5, catAxisTitleFontSize: 11,
  objectName: "anomaly-chart",
});
card(s, 4.4, 2.0, 1.9, 0.75, C.background2);
txt(s, "+182% vs normal", { x: 4.45, y: 2.1, w: 1.8, h: 0.55, fontSize: 14, bold: true, color: C.accent3, align: "center", valign: "middle" });
card(s, 8.4, 1.45, 4.3, 4.9, C.background2);
txt(s, "The rule", { x: 8.7, y: 1.65, w: 3.7, h: 0.4, fontSize: 18, bold: true, color: C.text2 });
txt(s, bullets(["Expected = this store's mean of the previous 14 days", "z = (today - expected) / std", "Flag if |z| > 3 AND at least 30% away from normal"], 14),
  { x: 8.7, y: 2.1, w: 3.7, h: 2.0 });
txt(s, "Why the 30% rule: a store with very steady history has tiny std, so even a 1% wobble scores high. Our test caught this; the rule keeps alerts meaningful.",
  { x: 8.7, y: 4.2, w: 3.7, h: 1.9, fontSize: 13, italic: true, color: C.accent5 });
s.addNotes("Per store because a big store's normal day would look like a spike for a small one. Previous days only, so today is not part of its own baseline. Result on test data: exactly the two planted problems flagged, nothing else.");

// ================================================================ 11. Security & scale
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Design" });
s.addText("Security today, and how it scales tomorrow", { placeholder: "title" });
card(s, 0.6, 1.45, 5.9, 4.6);
txt(s, "Security in the MVP", { x: 0.9, y: 1.7, w: 5.3, h: 0.45, fontSize: 18, bold: true, color: C.accent1 });
txt(s, bullets(["S3: public access blocked, versioned, encrypted", "IAM role: only this bucket and this secret", "RDS: not public; port 3306 open only to the app server",
  "DB connection encrypted (SSL/TLS)", "Password generated by AWS, stored in SSM", "No SSH: admin via Session Manager", "Dashboard open only to our IP"], 16),
  { x: 0.9, y: 2.3, w: 5.3, h: 3.6 });
table(s, ["Today (MVP)", "At ~100x scale"], [
  ["Pandas on EC2", "PySpark on Glue / EMR"],
  ["CSV in S3", "Parquet, partitioned by date"],
  ["RDS for reports", "Athena / Redshift for analytics"],
  ["Nightly systemd timer", "S3 event -> Lambda / Step Functions"],
  ["One EC2", "Load balancer + auto scaling"],
], { x: 6.9, y: 1.45, w: 5.8, colW: [2.6, 3.2], fontSize: 15, rowH: 0.62 });
txt(s, "S3-first design means storage never changes when we scale.", { x: 6.9, y: 5.5, w: 5.8, h: 0.5, fontSize: 15, italic: true, color: C.accent5 });
s.addNotes("Security: least privilege and nothing public. Scale: name the swap for each layer and stress that S3 stays the same.");

// ================================================================ 12. Roadmap & team
pres.addSection({ title: "Plan" });
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Plan" });
s.addText("Implementation roadmap and team split", { placeholder: "title" });
table(s, ["Time", "P1: Cloud", "P2: ETL", "P3: Database", "P4: Dashboard & tests"], [
  ["11:30-12:30", "S3, IAM, EC2, RDS, SGs", "Read + clean locally", "Schema, load masters", "Messy test data"],
  ["12:30-14:00", "Connect EC2-S3-RDS", "ETL S3 -> RDS", "Report SQL queries", "Dashboard skeleton"],
  ["14:00-15:30", "Logs, deploy dashboard", "Anomaly logic, audit", "Indexes, verify counts", "Charts + test cases"],
  ["15:30-16:30", "Freeze, screenshots", "Bug fixes", "Demo queries ready", "Rehearse demo"],
], { x: 0.6, y: 1.5, w: 12.1, colW: [1.7, 2.6, 2.5, 2.5, 2.8], fontSize: 14, rowH: 0.62 });
const rules = [["Data contract first", "File paths, columns and table names agreed before coding"], ["Thin, then thick", "End-to-end pipeline working by 14:00, then improve"], ["Everyone explains all", "Each member can walk the full architecture"]];
rules.forEach(([t, d], i) => {
  const x = 0.6 + i * 4.1;
  card(s, x, 4.95, 3.8, 1.5, C.background2);
  txt(s, t, { x: x + 0.25, y: 5.12, w: 3.3, h: 0.4, fontSize: 15, bold: true, color: C.text2 });
  txt(s, d, { x: x + 0.25, y: 5.55, w: 3.3, h: 0.8, fontSize: 14, color: C.accent5 });
});
s.addNotes("Split by pipeline stage so we can work in parallel; the data contract is agreed in the first hour. Syncs every 45 minutes.");

// ================================================================ 13. Testing, risks, demo
s = pres.addSlide({ masterName: "FM Content", sectionTitle: "Plan" });
s.addText("Testing, risks and how we will demo", { placeholder: "title" });
const cols = [
  ["Testing", C.accent1, ["Happy path: valid row loads", "Duplicates, 3 date formats, messy names", "Missing qty / bad date rejected", "Spike, drop, steady store, short history", "S3 code tested with mocked AWS"]],
  ["Risks & fallbacks", C.accent4, ["RDS slow or blocked -> MySQL on EC2", "Too little history -> state it, use 30-day sample", "AWS issue > 20 min -> simpler service", "Live demo fails -> recorded screenshots"]],
  ["Demo flow (20 min)", C.accent3, ["Problem and architecture (5)", "Upload a messy file to S3 (live)", "Run ETL, show audit + rejects", "Dashboard updates, alert appears", "Scale, security, Q&A"]],
];
cols.forEach(([label, color, items], i) => {
  const x = 0.6 + i * 4.1;
  card(s, x, 1.45, 3.8, 4.4);
  pill(s, x + 0.3, 1.75, 2.5, label, color);
  txt(s, bullets(items, 16), { x: x + 0.3, y: 2.45, w: 3.3, h: 3.2 });
});
s.addNotes("16 automated tests already pass. Every risk has a named fallback so we never block for long.");

// ================================================================ 14. Close
pres.addSection({ title: "Close" });
s = pres.addSlide({ masterName: "FM Title", sectionTitle: "Close" });
s.addText("We are asking for sign-off on the MVP", { placeholder: "title" });
s.addText("S3 -> Pandas ETL on EC2 -> RDS MySQL -> dashboard with anomaly alerts\nQuestions and feedback welcome", { placeholder: "body" });
s.addNotes("Close with the one-line architecture and an explicit ask: confirm the MUST-HAVE scope so we can start Sprint 1.");

(async () => {
  const out = "/home/claude/freshmart/docs/FreshMart_Sprint0_Design.pptx";
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
})();
