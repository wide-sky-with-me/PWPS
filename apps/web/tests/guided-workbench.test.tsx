import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { GuidedWorkbench } from "../components/guided-workbench";

// Mock the API module
vi.mock("../lib/api", () => ({
  createRun: vi.fn(),
  fetchRun: vi.fn(),
  fetchCurrentDecision: vi.fn(),
  submitDecision: vi.fn(),
  fetchOutputs: vi.fn(),
}));

import { createRun, fetchRun, fetchCurrentDecision, submitDecision, fetchOutputs } from "../lib/api";

const mockCreateRun = vi.mocked(createRun);
const mockFetchRun = vi.mocked(fetchRun);
const mockFetchCurrentDecision = vi.mocked(fetchCurrentDecision);
const mockSubmitDecision = vi.mocked(submitDecision);
const mockFetchOutputs = vi.mocked(fetchOutputs);

function renderWithQueryClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

describe("GuidedWorkbench", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the create view initially", () => {
    renderWithQueryClient(<GuidedWorkbench />);

    expect(screen.getByText("创建可审查的 pWPS 草案")).toBeInTheDocument();
    expect(screen.getByText("创建草案")).toBeInTheDocument();
    expect(screen.getByLabelText("工艺需求")).toBeInTheDocument();
  });

  it("shows mode selector with guided and auto options", () => {
    renderWithQueryClient(<GuidedWorkbench />);

    expect(screen.getByText("Guided")).toBeInTheDocument();
    expect(screen.getByText("Auto")).toBeInTheDocument();
  });

  it("disables create button when input is empty", async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<GuidedWorkbench />);

    const textarea = screen.getByLabelText("工艺需求");
    await user.clear(textarea);

    const createButton = screen.getByText("创建草案");
    expect(createButton).toBeDisabled();
  });

  it("creates a run and shows workbench", async () => {
    const user = userEvent.setup();

    mockCreateRun.mockResolvedValue({
      run_id: "test-run-001",
      status: "running",
    });
    mockFetchRun.mockResolvedValue({
      run_id: "test-run-001",
      status: "running",
      progress: { confirmed_groups: [], pending_groups: ["basic_condition_group"] },
      current_target: { group_name: "basic_condition_group", fields: ["base_material"] },
    });

    renderWithQueryClient(<GuidedWorkbench />);

    const createButton = screen.getByText("创建草案");
    await user.click(createButton);

    await waitFor(() => {
      expect(mockCreateRun).toHaveBeenCalled();
    });
  });

  it("shows error message when run creation fails", async () => {
    const user = userEvent.setup();

    mockCreateRun.mockRejectedValue(new Error("Network error"));

    renderWithQueryClient(<GuidedWorkbench />);

    const createButton = screen.getByText("创建草案");
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeInTheDocument();
    });
  });

  it("displays run ID after creation", async () => {
    const user = userEvent.setup();

    mockCreateRun.mockResolvedValue({
      run_id: "test-run-002",
      status: "running",
    });
    mockFetchRun.mockResolvedValue({
      run_id: "test-run-002",
      status: "running",
      progress: { confirmed_groups: [], pending_groups: ["basic_condition_group"] },
      current_target: { group_name: "basic_condition_group", fields: ["base_material"] },
    });

    renderWithQueryClient(<GuidedWorkbench />);

    const createButton = screen.getByText("创建草案");
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByText("test-run-002")).toBeInTheDocument();
    });
  });

  it("shows group progress list", async () => {
    const user = userEvent.setup();

    mockCreateRun.mockResolvedValue({
      run_id: "test-run-003",
      status: "running",
    });
    mockFetchRun.mockResolvedValue({
      run_id: "test-run-003",
      status: "running",
      progress: { confirmed_groups: [], pending_groups: ["basic_condition_group"] },
      current_target: { group_name: "basic_condition_group", fields: ["base_material"] },
    });

    renderWithQueryClient(<GuidedWorkbench />);

    const createButton = screen.getByText("创建草案");
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByText("基础条件")).toBeInTheDocument();
      expect(screen.getByText("焊材与保护")).toBeInTheDocument();
      expect(screen.getByText("焊接参数")).toBeInTheDocument();
    });
  });

  it("allows resetting the workbench", async () => {
    const user = userEvent.setup();

    mockCreateRun.mockResolvedValue({
      run_id: "test-run-004",
      status: "running",
    });
    mockFetchRun.mockResolvedValue({
      run_id: "test-run-004",
      status: "running",
      progress: { confirmed_groups: [], pending_groups: ["basic_condition_group"] },
      current_target: { group_name: "basic_condition_group", fields: ["base_material"] },
    });

    renderWithQueryClient(<GuidedWorkbench />);

    // Create a run
    const createButton = screen.getByText("创建草案");
    await user.click(createButton);

    await waitFor(() => {
      expect(screen.getByText("test-run-004")).toBeInTheDocument();
    });

    // Click reset
    const resetButton = screen.getByText("新建任务");
    await user.click(resetButton);

    // Should be back to create view
    await waitFor(() => {
      expect(screen.getByText("创建可审查的 pWPS 草案")).toBeInTheDocument();
    });
  });
});
