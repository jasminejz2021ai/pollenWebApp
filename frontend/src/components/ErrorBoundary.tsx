import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallbackLabel?: string;
}

interface State {
  hasError: boolean;
  message: string;
}

// Catches render/runtime errors in its subtree so a single component crash
// (e.g. a Leaflet popup hiccup) shows a recoverable message instead of a
// blank white page.
export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error?.message || 'Something went wrong.' };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, message: '' });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="absolute inset-0 z-[2000] flex items-center justify-center bg-slate-50/95">
          <div className="bg-white rounded-xl shadow-lg p-6 max-w-sm text-center border border-slate-200">
            <div className="text-3xl mb-2">⚠</div>
            <h2 className="text-lg font-bold text-slate-800 mb-1">
              {this.props.fallbackLabel || 'Display error'}
            </h2>
            <p className="text-slate-600 text-sm mb-4">{this.state.message}</p>
            <button
              onClick={this.handleReset}
              className="bg-emerald-600 text-white px-5 py-2 rounded-lg hover:bg-emerald-700 transition text-sm font-semibold"
            >
              Dismiss and continue
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
