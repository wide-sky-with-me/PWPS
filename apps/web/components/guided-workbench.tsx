"use client";

import {
  AlertTriangle,
  Check,
  ChevronDown,
  ClipboardList,
  Database,
  FileJson,
  LoaderCircle,
  Play,
  RotateCcw,
  ShieldAlert,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";

import { ErrorBoundary } from "@/components/error-boundary";
import { ParticleBackground } from "@/components/particle-background";
import { ConfidenceBar, LoadingPanel, LoadingSkeleton } from "@/components/ui-components";
import {
  useCreateRun,
  useCurrentDecision,
  useOutputs,
  useRun,
  useSubmitDecision,
} from "@/lib/hooks";
import type { Mode, RunOutputs } from "@/lib/api";

const groups = [
  ["basic_condition_group", "基础条件"],
  ["consumable_group", "焊材与保护"],
  ["parameter_group", "焊接参数"],
  ["thermal_group", "热过程"],
  ["meta_group", "文档元信息"],
] as const;

const riskLabels: Record<string, { text: string; className: string }> = {
  high: { text: "高风险", className: "risk-tag danger" },
  medium: { text: "中风险", className: "risk-tag warn" },
  low: { text: "低风险", className: "risk-tag" },
  needs_confirmation: { text: "待人工确认", className: "risk-tag warn" },
  prohibited: { text: "禁止推断", className: "risk-tag danger" },
  insufficient_evidence: { text: "证据不足", className: "risk-tag warn" },
};

const sampleInput = "";

// M5: Stable key generation for candidate values
function candidateKey(value: unknown, index: number): string {
  if (value === null || value === undefined) return `candidate-${index}`;
  if (typeof value === "string") return `candidate-${value}`;
  if (typeof value === "number") return `candidate-${value}`;
  if (typeof value === "boolean") return `candidate-${value}`;
  // For objects, use a deterministic string representation
  try {
    return `candidate-${JSON.stringify(value, Object.keys(value as Record<string, unknown>).sort())}`;
  } catch {
    return `candidate-${index}`;
  }
}

function valuesEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === null || b === null) return false;
  if (typeof a !== typeof b) return false;
  if (typeof a === "object") {
    try {
      return JSON.stringify(a, Object.keys(a as Record<string, unknown>).sort()) ===
             JSON.stringify(b, Object.keys(b as Record<string, unknown>).sort());
    } catch {
      return false;
    }
  }
  return false;
}

export function GuidedWorkbench() {
  const [mode, setMode] = useState<Mode>("guided");
  const [input, setInput] = useState(sampleInput);
  const [runId, setRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedValues, setSelectedValues] = useState<Record<string, unknown>>({});

  // React Query hooks
  const createRunMutation = useCreateRun();
  const { data: run, isLoading: isRunLoading } = useRun(runId);
  const { data: decision, isLoading: isDecisionLoading } = useCurrentDecision(runId);
  const { data: outputs } = useOutputs(runId);
  const submitDecisionMutation = useSubmitDecision(runId ?? "");

  // L9: Focus management refs
  const decisionHeaderRef = useRef<HTMLDivElement>(null);
  const previousDecisionRef = useRef<string | null>(null);

  const activeGroup = decision?.target_group ?? run?.current_target?.group_name;
  const completed = useMemo(
    () => new Set(run?.progress.confirmed_groups ?? []),
    [run?.progress.confirmed_groups],
  );

  // Sync recommended values when decision changes
  useEffect(() => {
    if (decision?.recommended) {
      setSelectedValues(decision.recommended);
    }
  }, [decision?.recommended]);

  // L9: Focus on decision header when it changes
  useEffect(() => {
    if (decision?.session_id && decision.session_id !== previousDecisionRef.current) {
      previousDecisionRef.current = decision.session_id;
      // Small delay to ensure DOM is updated
      setTimeout(() => {
        decisionHeaderRef.current?.focus();
      }, 100);
    }
  }, [decision?.session_id]);

  const busy = createRunMutation.isPending || submitDecisionMutation.isPending;

  function selectCandidate(field: string, value: unknown) {
    setSelectedValues((prev) => ({ ...prev, [field]: value }));
  }

  async function startRun() {
    setError(null);
    try {
      const created = await createRunMutation.mutateAsync({ input, mode });
      setRunId(created.run_id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create run.");
    }
  }

  async function acceptRecommended() {
    if (!runId || !decision) return;
    setError(null);
    try {
      await submitDecisionMutation.mutateAsync({
        session_id: decision.session_id,
        decision_type: "accept_recommended",
        selected_values: selectedValues,
        comment: "Accepted from Guided workbench.",
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to submit decision.");
    }
  }

  async function acceptAlternative() {
    if (!runId || !decision) return;
    setError(null);
    try {
      await submitDecisionMutation.mutateAsync({
        session_id: decision.session_id,
        decision_type: "choose_alternative",
        selected_values: selectedValues,
        comment: "User selected alternative candidates.",
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to submit decision.");
    }
  }

  function reset() {
    setRunId(null);
    setError(null);
    setSelectedValues({});
  }

  return (
    <>
      <ParticleBackground />
      <ErrorBoundary>
      <main className="app-shell">
        <header className="topbar">
          <div className="brand-lockup">
            <span className="brand-mark">
              <Zap size={20} />
            </span>
            <div>
              <strong>pWPS Agent</strong>
              <span>焊接工艺草案确认工作台</span>
            </div>
          </div>
          <div className="system-state">
            <span className="live-dot" />
            Draft workflow
          </div>
        </header>

        {!run ? (
          <section className="create-view">
            <div className="create-intro">
              <p className="kicker">New draft</p>
              <h1>创建可审查的 pWPS 草案</h1>
              <p>
                输入当前已知条件。系统按字段组整理候选、证据和风险，由你逐步确认。
              </p>
            </div>
            <div className="create-form">
              <label htmlFor="draft-input">工艺需求</label>
              <textarea
                id="draft-input"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                rows={6}
                placeholder="输入焊接工艺需求，例如：Q345R，12mm，对接焊，平焊，GMAW..."
              />
              <div className="form-row">
                <div>
                  <span className="field-label">工作模式</span>
                  <div className="segmented" role="radiogroup" aria-label="工作模式">
                    {(["guided", "auto"] as const).map((item) => (
                      <button
                        className={mode === item ? "active" : ""}
                        key={item}
                        onClick={() => setMode(item)}
                        type="button"
                        role="radio"
                        aria-checked={mode === item}
                      >
                        {item === "guided" ? "Guided" : "Auto"}
                      </button>
                    ))}
                  </div>
                </div>
                <button className="primary-button" disabled={busy || !input.trim()} onClick={startRun}>
                  {busy ? <LoaderCircle className="spin" size={18} /> : <Play size={18} />}
                  创建草案
                </button>
              </div>
              {error ? <p className="error-text" role="alert">{error}</p> : null}
            </div>
          </section>
        ) : (
          <section className="workbench">
            <aside className="progress-rail" aria-busy={isRunLoading}>
              <div className="rail-heading">
                <p className="kicker">Run progress</p>
                <h2>字段组确认</h2>
                <code>{run.run_id}</code>
              </div>
              <ol className="group-list" aria-label="字段组进度">
                {groups.map(([name, label], index) => (
                  <li
                    className={[
                      completed.has(name) ? "complete" : "",
                      activeGroup === name ? "current" : "",
                    ].join(" ")}
                    key={name}
                  >
                    <span>{completed.has(name) ? <Check size={14} /> : index + 1}</span>
                    <div>
                      <strong>{label}</strong>
                      <small>{name}</small>
                    </div>
                  </li>
                ))}
              </ol>
              <button className="ghost-button" onClick={reset} type="button">
                <RotateCcw size={16} />
                新建任务
              </button>
            </aside>

            <section className="decision-column">
              {isDecisionLoading ? (
                <LoadingSkeleton />
              ) : decision ? (
                <>
                  <div
                    className="decision-header"
                    ref={decisionHeaderRef}
                    tabIndex={-1}
                    role="heading"
                    aria-level={1}
                  >
                    <div>
                      <p className="kicker">Current decision</p>
                      <h1>{labelForGroup(decision.target_group)}</h1>
                      <p>{decision.summary}</p>
                    </div>
                    <span className="status-chip">等待确认</span>
                  </div>
                  <div className="known-strip">
                    <ClipboardList size={17} />
                    <span>当前字段组</span>
                    <strong>{decision.target_fields.join(" / ")}</strong>
                  </div>
                  <div className="field-stack">
                    {decision.target_fields.map((field) => {
                      const candidates = decision.candidates[field] ?? [];
                      const topCandidate = candidates[0];
                      const hasRisks = topCandidate?.risks?.length > 0;
                      const confidence = topCandidate?.confidence ?? 0;
                      const riskLevel = hasRisks
                        ? confidence < 0.5
                          ? "high"
                          : "medium"
                        : selectedValues[field] == null
                          ? "needs_confirmation"
                          : "low";
                      const risk = riskLabels[riskLevel];
                      const selectedIdx = candidates.findIndex(
                        (c) => valuesEqual(c.value, selectedValues[field])
                      );

                      return (
                        <article className="field-card" key={field}>
                          <div className="field-card-heading">
                            <div>
                              <span className="field-label">{field}</span>
                              <h3>{formatValue(selectedValues[field])}</h3>
                            </div>
                            <span className={risk.className}>{risk.text}</span>
                          </div>
                          {candidates.map((candidate, idx) => (
                            <div
                              className={`candidate${idx === selectedIdx ? " candidate-selected" : ""}`}
                              key={candidateKey(candidate.value, idx)}
                              onClick={() => selectCandidate(field, candidate.value)}
                              role="button"
                              tabIndex={0}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                  selectCandidate(field, candidate.value);
                                } else if (e.key === "ArrowDown" || e.key === "ArrowRight") {
                                  e.preventDefault();
                                  const next = candidates[(idx + 1) % candidates.length];
                                  selectCandidate(field, next.value);
                                } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
                                  e.preventDefault();
                                  const prev = candidates[(idx - 1 + candidates.length) % candidates.length];
                                  selectCandidate(field, prev.value);
                                }
                              }}
                            >
                              <div className="candidate-check">
                                <Check size={16} />
                              </div>
                              <div>
                                <strong>{formatValue(candidate.value)}</strong>
                                <p>{candidate.reason}</p>
                                {candidate.risks?.length > 0 ? (
                                  <small className="candidate-risk">
                                    ⚠ {candidate.risks.join("; ")}
                                  </small>
                                ) : null}
                              </div>
                              <ConfidenceBar value={candidate.confidence} />
                            </div>
                          ))}
                        </article>
                      );
                    })}
                  </div>
                  <div className="sticky-actions">
                    <button className="secondary-button" type="button" onClick={acceptRecommended}>
                      {busy ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />}
                      接受推荐并继续
                    </button>
                    <button className="primary-button" disabled={busy} onClick={acceptAlternative}>
                      {busy ? <LoaderCircle className="spin" size={18} /> : <Check size={18} />}
                      接受选择并继续
                    </button>
                  </div>
                </>
              ) : outputs ? (
                <FinalPreview outputs={outputs} onReset={reset} />
              ) : (
                <div className="loading-panel">
                  <LoaderCircle className="spin" size={24} />
                  {run?.status === "finalizing" || run?.status === "auditing"
                    ? "正在生成草案输出..."
                    : "正在准备字段确认卡片"}
                </div>
              )}
              {error ? <p className="error-text" role="alert">{error}</p> : null}
            </section>

            <aside className="context-rail">
              <section>
                <div className="section-title">
                  <Database size={17} />
                  <h2>证据摘要</h2>
                </div>
                {decision?.evidence.length ? (
                  decision.evidence.map((evidence) => (
                    <details className="evidence-item" key={evidence.evidence_id}>
                      <summary>
                        <span>{evidence.source_title}</span>
                        <ChevronDown size={15} />
                      </summary>
                      {evidence.section_path.length ? (
                        <small>{evidence.section_path.join(" / ")}</small>
                      ) : null}
                      <p>{evidence.content}</p>
                      {evidence.source_ref ? <small>{evidence.source_ref}</small> : null}
                      {evidence.limitations ? <small>{evidence.limitations}</small> : null}
                    </details>
                  ))
                ) : (
                  <p className="empty-copy">当前字段组没有额外证据。</p>
                )}
              </section>
              <section>
                <div className="section-title">
                  <ShieldAlert size={17} />
                  <h2>风险提示</h2>
                </div>
                {decision?.risks?.length ? (
                  decision.risks.map((risk, i) => (
                    <div className="risk-note" key={i}>
                      <AlertTriangle size={17} />
                      <p>
                        {typeof risk === "string"
                          ? risk
                          : (risk as Record<string, unknown>).description
                            ? String((risk as Record<string, unknown>).description)
                            : JSON.stringify(risk)}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="risk-note">
                    <AlertTriangle size={17} />
                    <p>模型常识仅作为低置信辅助，高风险字段仍需工程师复核。</p>
                  </div>
                )}
                {outputs?.risk_report?.issues?.length ? (
                  outputs.risk_report.issues.map((issue, i) => (
                    <div className="risk-note" key={i}>
                      <AlertTriangle size={17} />
                      <p>
                        <strong>[{issue.severity}]</strong> {issue.description}
                        <br />
                        <small>建议：{issue.recommended_action}</small>
                      </p>
                    </div>
                  ))
                ) : null}
              </section>
            </aside>
          </section>
        )}
      </main>
      </ErrorBoundary>
    </>
  );
}

function FinalPreview({ outputs, onReset }: { outputs: RunOutputs; onReset: () => void }) {
  return (
    <section className="final-preview">
      <div className="decision-header">
        <div>
          <p className="kicker">Draft output</p>
          <h1>草案已生成</h1>
          <p>输出仍需焊接工程师审查，不可直接作为正式 WPS 签发。</p>
        </div>
        <span className="status-chip warn">{outputs.publishability ?? "待确认"}</span>
      </div>
      <div className="json-preview">
        <div>
          <FileJson size={18} />
          <strong>pwps.json</strong>
        </div>
        <pre>{JSON.stringify(outputs.pwps, null, 2)}</pre>
      </div>
      <button className="primary-button" onClick={onReset} type="button">
        <RotateCcw size={17} />
        新建草案
      </button>
    </section>
  );
}

function labelForGroup(group: string) {
  return groups.find(([name]) => name === group)?.[1] ?? group;
}

function formatValue(value: unknown) {
  if (value == null) return "待补充";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
