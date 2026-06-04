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
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  useCreateRun,
  useCurrentDecision,
  useOutputs,
  useRun,
  useSubmitDecision,
} from "../lib/hooks";
import type { Mode, RunOutputs } from "../lib/api";

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

const sampleInput = "Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案";

function ConfidenceBar({ value }: { value: number }) {
  const percent = Math.round(value * 100);
  const level = percent < 40 ? "low" : percent < 70 ? "medium" : "";

  return (
    <div className="candidate-confidence">
      <div className="confidence-bar">
        <div
          className={`confidence-fill ${level}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className="confidence-text">{percent}%</span>
    </div>
  );
}

function ParticleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationId: number;
    let particles: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      size: number;
      opacity: number;
      color: string;
    }> = [];

    const colors = [
      "rgba(6, 182, 212, ",
      "rgba(139, 92, 246, ",
      "rgba(16, 185, 129, ",
    ];

    function resize() {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }

    function createParticles() {
      if (!canvas) return;
      particles = Array.from({ length: 50 }, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 1,
        opacity: Math.random() * 0.5 + 0.1,
        color: colors[Math.floor(Math.random() * colors.length)],
      }));
    }

    function animate() {
      if (!canvas || !ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `${p.color}${p.opacity})`;
        ctx.fill();
      });

      // Draw connections
      particles.forEach((p1, i) => {
        particles.slice(i + 1).forEach((p2) => {
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 150) {
            ctx.beginPath();
            ctx.strokeStyle = `rgba(6, 182, 212, ${0.1 * (1 - dist / 150)})`;
            ctx.lineWidth = 0.5;
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        });
      });

      animationId = requestAnimationFrame(animate);
    }

    resize();
    createParticles();
    animate();

    window.addEventListener("resize", () => {
      resize();
      createParticles();
    });

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 0,
        opacity: 0.6,
      }}
    />
  );
}

function LoadingSkeleton() {
  return (
    <div style={{ display: "grid", gap: "16px" }}>
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          style={{
            background: "rgba(0, 0, 0, 0.2)",
            borderRadius: "12px",
            padding: "20px",
            animation: `fadeIn 0.5s ease ${i * 0.1}s backwards`,
          }}
        >
          <div
            style={{
              height: "16px",
              width: "30%",
              background: "linear-gradient(90deg, rgba(148, 163, 184, 0.1), rgba(148, 163, 184, 0.2), rgba(148, 163, 184, 0.1))",
              backgroundSize: "200% 100%",
              animation: "shimmer 1.5s infinite",
              borderRadius: "4px",
              marginBottom: "12px",
            }}
          />
          <div
            style={{
              height: "12px",
              width: "60%",
              background: "linear-gradient(90deg, rgba(148, 163, 184, 0.1), rgba(148, 163, 184, 0.2), rgba(148, 163, 184, 0.1))",
              backgroundSize: "200% 100%",
              animation: "shimmer 1.5s infinite 0.2s",
              borderRadius: "4px",
            }}
          />
        </div>
      ))}
    </div>
  );
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

  const activeGroup = decision?.target_group ?? run?.current_target?.group_name;
  const completed = useMemo(
    () => new Set(run?.progress.confirmed_groups ?? []),
    [run?.progress.confirmed_groups],
  );

  // Sync recommended values when decision changes
  useMemo(() => {
    if (decision?.recommended) {
      setSelectedValues(decision.recommended);
    }
  }, [decision?.recommended]);

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
                  <div className="segmented">
                    {(["guided", "auto"] as const).map((item) => (
                      <button
                        className={mode === item ? "active" : ""}
                        key={item}
                        onClick={() => setMode(item)}
                        type="button"
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
              {error ? <p className="error-text">{error}</p> : null}
            </div>
          </section>
        ) : (
          <section className="workbench">
            <aside className="progress-rail">
              <div className="rail-heading">
                <p className="kicker">Run progress</p>
                <h2>字段组确认</h2>
                <code>{run.run_id}</code>
              </div>
              <ol className="group-list">
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
                  <div className="decision-header">
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
                        (c) => JSON.stringify(c.value) === JSON.stringify(selectedValues[field])
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
                              key={JSON.stringify(candidate.value)}
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
                  正在准备字段确认卡片
                </div>
              )}
              {error ? <p className="error-text">{error}</p> : null}
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
                      <p>{JSON.stringify(risk)}</p>
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
