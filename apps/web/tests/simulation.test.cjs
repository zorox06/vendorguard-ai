const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

function load(relativePath) {
  const source = fs.readFileSync(path.join(__dirname, "..", relativePath), "utf8");
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const context = { exports: {}, process: { env: {} } };
  vm.runInNewContext(code, context);
  return context.exports;
}

const { simulateMaterial } = load("src/lib/simulation.ts");

const resin = {
  material_id: "mat-001",
  material_name: "Polyethylene Resin HD-500",
  criticality: "tier_1",
  unit: "kg",
  on_hand_stock: 800,
  reserved_stock: 0,
  available_stock: 800,
  daily_consumption: 100,
  coverage_days: 8.0,
  scenario_arrival_days: 12.0,
  scenario_gap_days: 4.0,
  day_to_stockout: 9,
  primary_supplier: "Apex Polymers Ltd",
  has_alternate_supplier: true,
  alternate_suppliers: [],
  trajectory_base: Array.from({ length: 30 }, (_, i) => {
    const day = i + 1;
    const bal = 800 + (day >= 8 ? 1000 : 0) - day * 100;
    return { day, date_str: `2026-10-${String(day + 9).padStart(2, "0")}`, balance: bal, is_stockout: bal < 0 };
  }),
  trajectory_stress: Array.from({ length: 30 }, (_, i) => {
    const day = i + 1;
    const bal = 800 + (day >= 12 ? 1000 : 0) - day * 100;
    return { day, date_str: `2026-10-${String(day + 9).padStart(2, "0")}`, balance: bal, is_stockout: bal < 0 };
  }),
};

const film = {
  material_id: "mat-002",
  material_name: "High Barrier PVDC Film 25um",
  criticality: "tier_1",
  unit: "rolls",
  on_hand_stock: 120,
  reserved_stock: 20,
  available_stock: 100,
  daily_consumption: 10,
  coverage_days: 10.0,
  scenario_arrival_days: 14.0,
  scenario_gap_days: 4.0,
  day_to_stockout: 11,
  primary_supplier: "FlexiFilm Global",
  has_alternate_supplier: false,
  alternate_suppliers: [],
  trajectory_base: Array.from({ length: 30 }, (_, i) => ({
    day: i + 1,
    date_str: `2026-10-${String(i + 10).padStart(2, "0")}`,
    balance: Math.max(0, 100 - (i + 1) * 10 + (i >= 9 ? 150 : 0)),
    is_stockout: 100 - (i + 1) * 10 < 0,
  })),
  trajectory_stress: Array.from({ length: 30 }, (_, i) => ({
    day: i + 1,
    date_str: `2026-10-${String(i + 10).padStart(2, "0")}`,
    balance: 100 - (i + 1) * 10 + (i >= 15 ? 150 : 0),
    is_stockout: 100 - (i + 1) * 10 < 0,
  })),
};

const onTime = simulateMaterial(resin, 0);
const delayed = simulateMaterial(resin, 4);

assert.equal(onTime.firstReceipt, 8);
assert.equal(onTime.gap, 0);
assert.equal(delayed.arrival, 12);
assert.equal(delayed.gap, 4);
assert.equal(delayed.stockout, 9);
assert.equal(delayed.stress.find(p => p.day === 9).balance, -100);
assert.equal(delayed.stress.find(p => p.day === 12).balance, 600);
assert.equal(onTime.base.find(p => p.day === 8).balance, 1000);
assert.equal(delayed.base.find(p => p.day === 8).balance, 1000);
assert.notEqual(delayed.stress.find(p => p.day === 8).balance, onTime.stress.find(p => p.day === 8).balance);

// A clamped zero balance must not manufacture daily replenishment.
const filmSim = simulateMaterial(film, 4);
assert.equal(filmSim.firstReceipt, 10);
assert.equal(filmSim.arrival, 14);
assert.equal(filmSim.stockout, 11);
assert.equal(filmSim.stress.find(p => p.day === 30).balance, -50);

// At the maximum delay, the scheduled receipt moves to day 22.
const worst = simulateMaterial(resin, 14);
assert.equal(worst.arrival, 22);
assert.equal(worst.gap, 14);
assert.equal(worst.stockout, 9);

// With no supplied receipt, there is no invented arrival or supply-gap value.
const noReceipt = simulateMaterial({ ...resin, trajectory_base: [] }, 4);
assert.equal(noReceipt.arrival, null);
assert.equal(noReceipt.gap, null);
assert.equal(noReceipt.stockout, 9);
console.log("Inventory scenarios passed: arrival shifts, stockout, recovery, clamped balances, and missing receipts.");
