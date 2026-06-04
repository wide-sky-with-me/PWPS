"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          style={{
            alignItems: "center",
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.2)",
            borderRadius: "12px",
            color: "#ef4444",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
            justifyContent: "center",
            margin: "20px",
            minHeight: "200px",
            padding: "32px",
            textAlign: "center",
          }}
        >
          <AlertTriangle size={48} />
          <div>
            <h3 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "8px" }}>
              渲染出错
            </h3>
            <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
              {this.state.error?.message ?? "发生了一个意外错误"}
            </p>
          </div>
          <button
            onClick={this.handleReset}
            style={{
              alignItems: "center",
              background: "var(--gradient-primary)",
              border: "none",
              borderRadius: "8px",
              color: "white",
              cursor: "pointer",
              display: "flex",
              fontSize: "14px",
              gap: "8px",
              padding: "10px 20px",
            }}
          >
            <RotateCcw size={16} />
            重试
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
