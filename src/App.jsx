import React from "react";
import MatchPredictor from "./components/MatchPredictor";

export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-4xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700 rounded-xl p-6 neon">
        <header className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-semibold">CricIQ — Match Predictor</h1>
          <div className="text-sm text-slate-400">Dark analytics dashboard</div>
        </header>

        <MatchPredictor />
      </div>
    </div>
  );
}
