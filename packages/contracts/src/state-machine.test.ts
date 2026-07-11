import { describe, expect, it } from "vitest";

import {
  RECOVERABLE_STATES,
  TERMINAL_STATES,
  TRANSITIONS,
  WORKFLOW_STATES,
  canTransition,
  isTerminalState,
  isWorkflowState,
} from "./index";

const GOLDEN_PATH = [
  "RECEIVED",
  "NORMALIZING",
  "COLLECTING_EVIDENCE",
  "EVIDENCE_READY",
  "INVESTIGATING",
  "HYPOTHESES_READY",
  "PLANNING_REMEDIATION",
  "PLAN_READY",
  "WAITING_PATCH_APPROVAL",
  "PATCHING",
  "VERIFYING",
  "REVIEW_READY",
  "RESOLUTION_DRAFTED",
  "CLOSED",
] as const;

describe("workflow state contract", () => {
  it("covers every state in the transition map", () => {
    expect(Object.keys(TRANSITIONS).sort()).toEqual([...WORKFLOW_STATES].sort());
  });

  it("keeps the golden path legal", () => {
    for (let i = 0; i < GOLDEN_PATH.length - 1; i++) {
      const from = GOLDEN_PATH[i]!;
      const to = GOLDEN_PATH[i + 1]!;
      expect(canTransition(from, to), `${from} -> ${to}`).toBe(true);
    }
  });

  it("terminal states have no outgoing transitions", () => {
    for (const state of TERMINAL_STATES) {
      expect(TRANSITIONS[state]).toEqual([]);
      expect(isTerminalState(state)).toBe(true);
    }
  });

  it("recoverable states can re-enter the workflow", () => {
    expect(canTransition("NEEDS_INPUT", "COLLECTING_EVIDENCE")).toBe(true);
    expect(canTransition("PATCH_FAILED", "PLAN_READY")).toBe(true);
    expect(canTransition("EXTERNAL_ACTION_FAILED", "WAITING_PR_APPROVAL")).toBe(true);
    for (const state of RECOVERABLE_STATES) {
      expect(isTerminalState(state)).toBe(false);
    }
  });

  it("rejects illegal transitions", () => {
    expect(canTransition("RECEIVED", "PATCHING")).toBe(false);
    expect(canTransition("CLOSED", "RECEIVED")).toBe(false);
  });

  it("narrows unknown strings with isWorkflowState", () => {
    expect(isWorkflowState("REVIEW_READY")).toBe(true);
    expect(isWorkflowState("NOT_A_STATE")).toBe(false);
  });
});
