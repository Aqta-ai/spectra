"use client";

import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error("[Spectra] Unhandled render error:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-[#0a0a0f] text-white px-6 text-center">
          <div className="w-20 h-20 spectra-orb flex items-center justify-center text-3xl font-bold">S</div>
          <div className="space-y-2">
            <h1 className="text-xl font-semibold">Something went wrong</h1>
            <p className="text-white/50 text-sm">Press <kbd className="px-2 py-0.5 bg-white/10 rounded border border-white/20 font-mono text-xs">Q</kbd> after refreshing to reconnect</p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2.5 bg-spectra-primary hover:bg-spectra-primary/85 rounded-xl text-sm font-semibold transition-colors"
          >
            Refresh
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
