import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mock setup
const api = await import("../lib/api");

describe("API Client", () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  describe("createRun", () => {
    it("sends POST request with correct payload", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ run_id: "run-123", status: "waiting_for_user" }),
      });

      const result = await api.createRun("Q345R GMAW", "guided");

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/runs"),
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            input: "Q345R GMAW",
            mode: "guided",
            attachments: [],
          }),
        })
      );
      expect(result.run_id).toBe("run-123");
      expect(result.status).toBe("waiting_for_user");
    });

    it("throws error on failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ message: "Internal error" }),
      });

      await expect(api.createRun("test", "auto")).rejects.toThrow("Internal error");
    });
  });

  describe("fetchRun", () => {
    it("fetches run state by ID", async () => {
      const runState = {
        run_id: "run-123",
        status: "waiting_for_user",
        mode: "guided",
        current_target: null,
        progress: { confirmed_groups: [], remaining_groups: [] },
        publishability: null,
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => runState,
      });

      const result = await api.fetchRun("run-123");

      expect(result.run_id).toBe("run-123");
      expect(result.status).toBe("waiting_for_user");
    });
  });

  describe("fetchCurrentDecision", () => {
    it("fetches current decision card", async () => {
      const decision = {
        run_id: "run-123",
        session_id: "session-abc",
        target_group: "basic_condition_group",
        target_fields: ["base_material", "thickness"],
        summary: "Confirm fields",
        candidates: {},
        evidence: [],
        risks: [],
        recommended: {},
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => decision,
      });

      const result = await api.fetchCurrentDecision("run-123");

      expect(result.target_group).toBe("basic_condition_group");
      expect(result.session_id).toBe("session-abc");
    });
  });

  describe("submitDecision", () => {
    it("submits decision with correct payload", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          run_id: "run-123",
          status: "finished",
          accepted: true,
        }),
      });

      const result = await api.submitDecision("run-123", {
        session_id: "session-abc",
        decision_type: "accept_recommended",
        selected_values: { base_material: "Q345R" },
        comment: "Accept",
      });

      expect(result.accepted).toBe(true);
      expect(result.status).toBe("finished");
    });
  });

  describe("fetchOutputs", () => {
    it("fetches run outputs", async () => {
      const outputs = {
        pwps: { fields: {} },
        field_report: {},
        evidence_report: {},
        risk_report: { publishability: "needs_confirmation" },
        discussion_trace: {},
        publishability: "needs_confirmation",
      };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => outputs,
      });

      const result = await api.fetchOutputs("run-123");

      expect(result.publishability).toBe("needs_confirmation");
    });
  });
});
