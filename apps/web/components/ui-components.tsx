"use client";

import { LoaderCircle } from "lucide-react";

export function ConfidenceBar({ value }: { value: number }) {
  const percent = Math.round(value * 100);
  const level = percent < 40 ? "low" : percent < 70 ? "medium" : "";

  return (
    <div
      className="candidate-confidence"
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`置信度 ${percent}%`}
    >
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

export function LoadingSkeleton() {
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

export function LoadingPanel({ message }: { message: string }) {
  return (
    <div className="loading-panel">
      <LoaderCircle className="spin" size={24} />
      {message}
    </div>
  );
}
