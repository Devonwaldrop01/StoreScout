"use client";

import { Component, type ReactNode, type ErrorInfo } from "react";
import { RefreshCw, AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message || "Something went wrong." };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  reset = () => this.setState({ hasError: false, message: "" });

  render() {
    if (!this.state.hasError) return this.props.children;

    if (this.props.fallback) return this.props.fallback;

    return (
      <div
        className="flex flex-col items-center justify-center min-h-[40vh] rounded-2xl p-10 text-center"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <AlertTriangle className="w-8 h-8 mb-3" style={{ color: "#F2555A" }} />
        <p className="font-semibold mb-1" style={{ color: "var(--text)" }}>
          Something went wrong
        </p>
        <p className="text-sm mb-5 max-w-xs" style={{ color: "var(--muted)" }}>
          {this.state.message}
        </p>
        <button
          onClick={this.reset}
          className="flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-xl transition-all hover:brightness-110"
          style={{ background: "var(--bg3)", color: "var(--text)" }}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Try again
        </button>
      </div>
    );
  }
}
