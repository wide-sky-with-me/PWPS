"use client";

import {
  ArrowLeft,
  Calendar,
  CheckCircle,
  Clock,
  FileText,
  LoaderCircle,
  Play,
  XCircle,
  Zap,
} from "lucide-react";
import { useState } from "react";

import { useRuns } from "@/lib/hooks";
import type { RunListItem, RunStatus } from "@/lib/api";

const statusConfig: Record<RunStatus, { label: string; icon: typeof CheckCircle; className: string }> = {
  initialized: { label: "初始化", icon: Clock, className: "status-pending" },
  understanding: { label: "理解中", icon: LoaderCircle, className: "status-processing" },
  field_confirming: { label: "确认中", icon: LoaderCircle, className: "status-processing" },
  waiting_for_user: { label: "等待用户", icon: Clock, className: "status-waiting" },
  auditing: { label: "审计中", icon: LoaderCircle, className: "status-processing" },
  finalizing: { label: "生成中", icon: LoaderCircle, className: "status-processing" },
  finished: { label: "已完成", icon: CheckCircle, className: "status-success" },
  blocked: { label: "已阻塞", icon: XCircle, className: "status-error" },
};

function formatDate(dateStr: string): string {
  if (!dateStr) return "-";
  const date = new Date(dateStr);
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function truncateInput(input: string, maxLen = 60): string {
  if (input.length <= maxLen) return input;
  return input.slice(0, maxLen) + "...";
}

export function HistoryPage({ onBack, onViewRun }: {
  onBack: () => void;
  onViewRun: (runId: string) => void;
}) {
  const [page, setPage] = useState(0);
  const limit = 20;
  const { data, isLoading, error } = useRuns(limit, page * limit);

  const runs = data?.runs ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">
            <Zap size={20} />
          </span>
          <div>
            <strong>pWPS Agent</strong>
            <span>历史任务</span>
          </div>
        </div>
        <button className="ghost-button" onClick={onBack} style={{ width: "auto" }}>
          <ArrowLeft size={16} />
          返回
        </button>
      </header>

      <section className="history-container">
        <div className="history-header">
          <h1>历史任务</h1>
          <p>共 {total} 个任务</p>
        </div>

        {isLoading ? (
          <div className="loading-panel">
            <LoaderCircle className="spin" size={24} />
            加载中...
          </div>
        ) : error ? (
          <div className="error-text" role="alert">
            加载失败: {error.message}
          </div>
        ) : runs.length === 0 ? (
          <div className="history-empty">
            <FileText size={48} />
            <h3>暂无任务</h3>
            <p>创建第一个 pWPS 草案任务</p>
            <button className="primary-button" onClick={onBack}>
              <Play size={18} />
              创建任务
            </button>
          </div>
        ) : (
          <>
            <div className="history-list">
              {runs.map((run) => (
                <HistoryCard key={run.run_id} run={run} onView={() => onViewRun(run.run_id)} />
              ))}
            </div>

            {totalPages > 1 && (
              <div className="history-pagination">
                <button
                  className="ghost-button"
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                  style={{ width: "auto" }}
                >
                  上一页
                </button>
                <span>
                  {page + 1} / {totalPages}
                </span>
                <button
                  className="ghost-button"
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => p + 1)}
                  style={{ width: "auto" }}
                >
                  下一页
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}

function HistoryCard({ run, onView }: { run: RunListItem; onView: () => void }) {
  const config = statusConfig[run.status] ?? statusConfig.initialized;
  const Icon = config.icon;

  return (
    <article className="history-card" onClick={onView} role="button" tabIndex={0}>
      <div className="history-card-header">
        <div className="history-card-status">
          <Icon size={16} className={config.className} />
          <span className={config.className}>{config.label}</span>
        </div>
        <code>{run.run_id}</code>
      </div>

      <p className="history-card-input">{truncateInput(run.raw_input)}</p>

      <div className="history-card-meta">
        <span>
          <Calendar size={14} />
          {formatDate(run.created_at)}
        </span>
        {run.mode && (
          <span className="history-card-mode">
            {run.mode === "guided" ? "Guided" : "Auto"}
          </span>
        )}
        {run.publishability && (
          <span className={`history-card-publish ${run.publishability === "draft_publishable" ? "success" : "warn"}`}>
            {run.publishability === "draft_publishable" ? "可发布" : "需审查"}
          </span>
        )}
      </div>
    </article>
  );
}
