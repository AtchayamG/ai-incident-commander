// Deterministic offline check harness for the checkout-api fixture repository.
//
// This is the fixture's repository toolchain (blueprint 19.3): the incident
// commander's verification manifest maps the plan's baseline commands
// ("npm test", "npm run lint", ...) to this zero-dependency harness so the
// checks are real subprocess executions with deterministic output — no
// package installs, no network, no timestamps. The patched code genuinely
// runs: a session without a discount really calls applyDiscount, so the
// unguarded `session.discount.code` really throws and fails the run.
//
// Modes:
//   test / targeted-test  execute src/checkout.test.ts against src/checkout.ts
//   lint                  deterministic static rules over the source files
//   typecheck             strip-types module load check (offline; not full tsc)
//
// Usage: node --experimental-strip-types --no-warnings harness.mjs <mode> <workspaceRoot>
// Exit code 0 = check passed; 1 = check failed; 2 = harness misuse.

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const SOURCE_FILE = "src/checkout.ts";
const TEST_FILE = "src/checkout.test.ts";

function fail(code, message) {
  console.error(message);
  process.exit(code);
}

const [mode, workspaceRoot] = process.argv.slice(2);
if (!mode || !workspaceRoot) fail(2, "usage: harness.mjs <mode> <workspaceRoot>");
const root = path.resolve(workspaceRoot);
if (!fs.existsSync(path.join(root, SOURCE_FILE))) {
  fail(2, `workspace has no ${SOURCE_FILE}: ${root}`);
}

function read(rel) {
  return fs.readFileSync(path.join(root, rel), "utf8");
}

// Materialize import-resolvable copies inside the ephemeral workspace: the
// fixture test imports "./checkout" extensionless (jest style); node ESM
// needs the explicit .ts extension for strip-types loading.
function scratchModules() {
  const scratch = path.join(root, ".vscratch");
  fs.mkdirSync(scratch, { recursive: true });
  fs.writeFileSync(path.join(scratch, "checkout.ts"), read(SOURCE_FILE));
  fs.writeFileSync(
    path.join(scratch, "checkout.test.ts"),
    read(TEST_FILE).replace(/from "\.\/checkout"/g, 'from "./checkout.ts"'),
  );
  return scratch;
}

async function runTests() {
  const results = [];
  globalThis.describe = (name, fn) => fn();
  globalThis.it = (name, fn) => {
    try {
      fn();
      results.push({ name, error: null });
    } catch (error) {
      results.push({ name, error: String(error) });
    }
  };
  globalThis.expect = (actual) => ({
    toBe(expected) {
      if (!Object.is(actual, expected)) {
        throw new Error(`expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
      }
    },
  });
  const scratch = scratchModules();
  await import(pathToFileURL(path.join(scratch, "checkout.test.ts")).href);
  let failed = 0;
  for (const result of results) {
    if (result.error === null) {
      console.log(`PASS ${result.name}`);
    } else {
      failed += 1;
      console.log(`FAIL ${result.name}: ${result.error}`);
    }
  }
  console.log(`tests: ${results.length - failed} passed, ${failed} failed`);
  process.exit(failed === 0 && results.length > 0 ? 0 : 1);
}

function runLint() {
  // Deterministic minimal ruleset (documented in checks/README.md): the
  // fixture repo's lint contract, not a full eslint.
  const rules = [
    ["no-var", /(^|\s)var\s+[A-Za-z_$]/],
    ["no-console", /\bconsole\.(log|debug|info)\(/],
    ["eqeqeq-allow-null", /[^=!<>]==[^=]|[^=!]!=[^=]/],
  ];
  const findings = [];
  for (const rel of [SOURCE_FILE, TEST_FILE]) {
    const lines = read(rel).split("\n");
    lines.forEach((line, index) => {
      for (const [rule, pattern] of rules) {
        if (rule === "eqeqeq-allow-null" && /[=!]=\s*null/.test(line)) continue;
        if (pattern.test(line)) findings.push(`${rel}:${index + 1} ${rule}`);
      }
    });
  }
  for (const finding of findings) console.log(finding);
  console.log(`lint: ${findings.length} finding(s)`);
  process.exit(findings.length === 0 ? 0 : 1);
}

async function runTypecheck() {
  // Offline approximation: strip types and load the module graph. Catches
  // syntax errors and unresolvable imports; NOT a full tsc type analysis.
  const scratch = scratchModules();
  try {
    const module = await import(pathToFileURL(path.join(scratch, "checkout.ts")).href);
    for (const name of ["applyDiscount", "processCheckout"]) {
      if (typeof module[name] !== "function") {
        throw new Error(`expected exported function ${name}`);
      }
    }
  } catch (error) {
    console.log(`typecheck: FAIL ${String(error)}`);
    process.exit(1);
  }
  console.log("typecheck: module loads with types stripped (offline check, not full tsc)");
  process.exit(0);
}

if (mode === "test" || mode === "targeted-test") await runTests();
else if (mode === "lint") runLint();
else if (mode === "typecheck") await runTypecheck();
else fail(2, `unknown mode: ${mode}`);
