/**
 * SignalForge v2.1 — Signal Edge Adjudicator demo console.
 *
 * P2-9 fix: SERVICE_URL falls back to "" (relative path via Vite proxy),
 *           never hardcoded localhost in production builds.
 * P2-2 fix: getMockVerdict leakage_check fields aligned with LeakageCheck
 *           schema (direction_flip_detected, lookahead_flag included).
 */

import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell,
} from "recharts";

// P2-9: env var > build-time define > relative path (Vite proxy)
const SERVICE_URL =
  import.meta.env.VITE_SERVICE_URL ||
  (typeof __SERVICE_URL__ !== "undefined" && __SERVICE_URL__) ||
  "";

// ── Preset scenarios ─────────────────────────────────────────────────
const PRESET_LEAKAGE = {
  label: "🔴 Submit leaky signal (LEAKAGE_DETECTED)",
  sub: "naive Sharpe +0.85 → IS-only −0.99 → LEAKAGE_DETECTED",
  asset: "ETH",
  candidate_signal: {
    name: "cmc_fg_extreme_reversal_v1",
    source: "cmc_fear_greed",
    definition: "fg < 20 -> long; fg > 80 -> short",
    holding_period_days: 5,
  },
  risk: "balanced",
};

const PRESET_HONEST = {
  label: "🟡 Submit honest weak signal (REJECT)",
  sub: "honest evaluation, REJECT verdict",
  asset: "BTC",
  candidate_signal: {
    name: "btc_dominance_trend",
    source: "cmc_global_metrics",
    definition: "dom_trend_30 > 0 -> btc_long",
    holding_period_days: 10,
  },
  risk: "conservative",
};

const VERDICT_COLORS = {
  STRONG_ACCEPT:    { bg: "bg-green-500",  text: "text-white", label: "✅ STRONG ACCEPT" },
  ACCEPT:           { bg: "bg-green-400",  text: "text-white", label: "✅ ACCEPT" },
  WEAK:             { bg: "bg-yellow-400", text: "text-black", label: "⚠️ WEAK" },
  REJECT:           { bg: "bg-red-500",    text: "text-white", label: "❌ REJECT" },
  LEAKAGE_DETECTED: { bg: "bg-red-700",    text: "text-white", label: "🚨 LEAKAGE DETECTED" },
};

// ── Edge Confidence gauge ────────────────────────────────────────────
function ConfidenceGauge({ score }) {
  const color = score >= 60 ? "#22c55e" : score >= 40 ? "#eab308" : "#ef4444";
  const angle = (score / 100) * 180 - 90;
  const r = 80, cx = 100, cy = 100;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const x = cx + r * Math.cos(toRad(angle));
  const y = cy + r * Math.sin(toRad(angle));

  return (
    <div className="flex flex-col items-center">
      <svg width="200" height="120" viewBox="0 0 200 120">
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#e5e7eb" strokeWidth="12" />
        <path d={`M 20 100 A 80 80 0 0 1 ${x} ${y}`} fill="none" stroke={color} strokeWidth="12" />
        <line x1={cx} y1={cy} x2={x} y2={y} stroke="#1f2937" strokeWidth="3" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="5" fill="#1f2937" />
        <text x="16" y="116" fontSize="10" fill="#9ca3af">0</text>
        <text x="94" y="22" fontSize="10" fill="#9ca3af">50</text>
        <text x="178" y="116" fontSize="10" fill="#9ca3af">100</text>
      </svg>
      <div className="text-4xl font-bold mt-1" style={{ color }}>{score}</div>
      <div className="text-sm text-gray-500">Edge Confidence / 100</div>
    </div>
  );
}

// ── Sharpe comparison bars (the demo highlight) ──────────────────────
function SharpComparison({ naive, honest }) {
  const data = [
    { name: "Naive (leaky)", sharpe: naive, fill: "#ef4444" },
    { name: "Honest (IS-only)", sharpe: honest, fill: "#22c55e" },
  ];
  const minY = Math.min(honest, -1.5);
  const maxY = Math.max(naive, 1.2);

  return (
    <div className="w-full">
      <div className="text-sm text-gray-500 mb-2 text-center">
        Leaky vs IS-only honest calibration — Sharpe
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis domain={[minY - 0.2, maxY + 0.2]} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v) => v.toFixed(2)} />
          <ReferenceLine y={0} stroke="#374151" strokeWidth={2} />
          <Bar dataKey="sharpe" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (<Cell key={i} fill={entry.fill} />))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="text-center text-xs text-gray-400 mt-1">
        ⚠️ Leakage inflated Sharpe to{" "}
        <span className="text-red-500 font-bold">{naive > 0 ? "+" : ""}{naive.toFixed(2)}</span>;
        honest calibration reveals{" "}
        <span className="text-green-600 font-bold">{honest.toFixed(2)}</span>
      </div>
    </div>
  );
}

// ── Three-stack evidence panel ───────────────────────────────────────
function EvidencePanel({ verdict }) {
  if (!verdict) return null;
  const prov = verdict.cmc_data_provenance || {};
  const billing = verdict.billing || {};
  return (
    <div className="mt-6 p-4 bg-gray-50 rounded-xl border border-gray-200">
      <h3 className="font-semibold text-gray-700 mb-3">📊 Sponsor-Stack Evidence</h3>
      <div className="grid grid-cols-1 gap-3 text-sm">
        <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
          <div className="font-medium text-blue-700 mb-1">① CMC Agent Hub</div>
          <div className="text-blue-600 text-xs">
            Source: {prov.fear_greed_source || "CMC Proprietary F&G"}<br/>
            This call: {(prov.access_channels_used || ["rest"]).join(" + ").toUpperCase()}<br/>
            Project channels: {(prov.historical_channels_documented || []).join(" + ").toUpperCase()}<br/>
            {billing.payment_tx && (
              <span>x402 tx: <code>{String(billing.payment_tx).slice(0, 20)}...</code></span>
            )}
          </div>
        </div>
        <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-100">
          <div className="font-medium text-yellow-700 mb-1">② BNB AI Agent SDK</div>
          <div className="text-yellow-600 text-xs">
            ERC-8004 registration: outputs/onchain/registration.json<br/>
            APEX job lifecycle: outputs/onchain/job_lifecycle.json<br/>
            BSC Testnet (Chain 97), gas-free registration
          </div>
        </div>
        <div className="p-3 bg-purple-50 rounded-lg border border-purple-100">
          <div className="font-medium text-purple-700 mb-1">③ CMC Skills Marketplace</div>
          <div className="text-purple-600 text-xs">
            find_skill: signal validation / deflated sharpe / CMC<br/>
            skill-card: GET /.well-known/skill-card.json<br/>
            x402 · $0.50 USDC per adjudication
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main app ─────────────────────────────────────────────────────────
export default function App() {
  const [loading, setLoading] = useState(false);
  const [verdict, setVerdict] = useState(null);
  const [error, setError] = useState(null);
  const [customSignal, setCustomSignal] = useState("");

  const sendAdjudicateRequest = async (payload) => {
    setLoading(true);
    setVerdict(null);
    setError(null);
    try {
      let res = await fetch(`${SERVICE_URL}/adjudicate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.status === 402) {
        // demo-mode x402 auth header
        const demoAuth = btoa(JSON.stringify({
          x402Version: 1, network: "base",
          payload: { signature: "0xdemo", authorization: {} },
        }));
        res = await fetch(`${SERVICE_URL}/adjudicate`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-PAYMENT": demoAuth },
          body: JSON.stringify(payload),
        });
      }

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setVerdict(await res.json());
    } catch (e) {
      setVerdict(getMockVerdict(payload));
      setError("(Demo mode: service not reachable — showing mock data)");
    } finally {
      setLoading(false);
    }
  };

  const handlePreset = (preset) => {
    sendAdjudicateRequest({
      asset: preset.asset,
      candidate_signal: preset.candidate_signal,
      risk: preset.risk,
    });
  };

  const handleCustom = () => {
    const sig = customSignal.trim()
      ? { name: "custom", source: "cmc_fear_greed", definition: customSignal, holding_period_days: 5 }
      : PRESET_LEAKAGE.candidate_signal;
    sendAdjudicateRequest({ asset: "ETH", candidate_signal: sig, risk: "balanced" });
  };

  const vc = verdict ? (VERDICT_COLORS[verdict.verdict] || VERDICT_COLORS.REJECT) : null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-4">
      <div className="max-w-2xl mx-auto">

        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">⚖️ SignalForge</h1>
          <p className="text-gray-300 text-sm">
            Signal Edge Adjudicator — validates trading signals for real alpha vs leakage
          </p>
          <div className="flex justify-center gap-2 mt-3 flex-wrap">
            <span className="px-2 py-1 bg-blue-600 text-white text-xs rounded">CMC Agent Hub ✅</span>
            <span className="px-2 py-1 bg-yellow-600 text-white text-xs rounded">BNB AI Agent SDK ✅</span>
            <span className="px-2 py-1 bg-purple-600 text-white text-xs rounded">Skills Marketplace ✅</span>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 shadow-lg mb-5">
          <h2 className="font-semibold text-gray-800 mb-4">📤 Submit a candidate signal</h2>

          <div className="grid grid-cols-1 gap-3 mb-4">
            <button
              onClick={() => handlePreset(PRESET_LEAKAGE)}
              disabled={loading}
              className="w-full py-3 px-4 bg-red-100 hover:bg-red-200 border-2 border-red-300 rounded-xl text-left text-sm font-medium text-red-800 transition-colors disabled:opacity-50"
            >
              {PRESET_LEAKAGE.label}
              <div className="text-xs text-red-500 mt-1 font-normal">{PRESET_LEAKAGE.sub}</div>
            </button>
            <button
              onClick={() => handlePreset(PRESET_HONEST)}
              disabled={loading}
              className="w-full py-3 px-4 bg-yellow-50 hover:bg-yellow-100 border-2 border-yellow-300 rounded-xl text-left text-sm font-medium text-yellow-800 transition-colors disabled:opacity-50"
            >
              {PRESET_HONEST.label}
              <div className="text-xs text-yellow-600 mt-1 font-normal">{PRESET_HONEST.sub}</div>
            </button>
          </div>

          <div className="border-t pt-4">
            <div className="text-xs text-gray-500 mb-2">Or enter a custom signal definition:</div>
            <textarea
              className="w-full border rounded-lg p-2 text-sm h-16 text-gray-700 resize-none"
              placeholder="e.g. fg < 25 -> long; fg > 75 -> short"
              value={customSignal}
              onChange={(e) => setCustomSignal(e.target.value)}
            />
            <button
              onClick={handleCustom}
              disabled={loading}
              className="mt-2 w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {loading ? "Adjudicating..." : "Submit for adjudication"}
            </button>
          </div>
        </div>

        {loading && (
          <div className="bg-white rounded-2xl p-8 text-center shadow-lg mb-5">
            <div className="text-4xl mb-3 animate-spin">⚖️</div>
            <div className="text-gray-600">Running statistical checks...</div>
            <div className="text-xs text-gray-400 mt-2">
              DSR · BH-FDR · Walk-forward · Plateau · Leakage · Regime
            </div>
          </div>
        )}

        {error && !loading && (
          <div className="bg-orange-50 border border-orange-200 rounded-xl p-3 mb-4 text-xs text-orange-700">
            {error}
          </div>
        )}

        {verdict && !loading && (
          <>
            <div className={`rounded-2xl p-5 shadow-lg mb-5 ${vc.bg}`}>
              <div className={`text-2xl font-bold mb-1 ${vc.text}`}>{vc.label}</div>
              <div className={`text-sm ${vc.text} opacity-80`}>{verdict.verdict_summary}</div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-lg mb-5">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <ConfidenceGauge score={verdict.edge_confidence} />
                <SharpComparison
                  naive={verdict.leakage_check?.naive_sharpe_if_leaked ?? 0.85}
                  honest={verdict.leakage_check?.honest_sharpe ?? -0.99}
                />
              </div>
            </div>

            <div className="bg-white rounded-2xl p-5 shadow-lg mb-5">
              <h3 className="font-semibold text-gray-700 mb-3">📋 Check details</h3>
              <ul className="space-y-2">
                {(verdict.reasons || []).map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className={`mt-0.5 flex-shrink-0 ${/\(\+/.test(r) ? "text-green-500" : "text-red-500"}`}>
                      {/\(\+/.test(r) ? "✓" : "✗"}
                    </span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>

            {verdict.regime_conditional_finding && (
              <div className="bg-indigo-50 rounded-2xl p-5 shadow-lg mb-5 border border-indigo-100">
                <h3 className="font-semibold text-indigo-700 mb-2">🔬 Regime-conditional finding</h3>
                <div className="text-sm text-indigo-600">
                  <div>Regime: <strong>{verdict.regime_conditional_finding.bucket}</strong></div>
                  <div>
                    IC = {verdict.regime_conditional_finding.ic?.toFixed(3)},
                    t = {verdict.regime_conditional_finding.t_stat?.toFixed(2)},
                    p ≈ {verdict.regime_conditional_finding.p_value?.toExponential(1)}
                  </div>
                  <div className="text-xs mt-1 text-indigo-400">
                    {verdict.regime_conditional_finding.interpretation}
                  </div>
                </div>
              </div>
            )}

            <EvidencePanel verdict={verdict} />
          </>
        )}

        <div className="text-center text-xs text-gray-500 mt-8 pb-4">
          SignalForge v2.1 · BNB Hack Track 2 · CMC Agent Hub + BNB AI Agent SDK
          <br/>
          <a href="https://github.com/0xCaptain888/signalforge" className="underline">GitHub</a>
          {" · "}
          <a href={`${SERVICE_URL || ""}/docs`} className="underline">API Docs</a>
        </div>
      </div>
    </div>
  );
}

// ── Mock verdict (P2-2: fields aligned with LeakageCheck schema) ──────
function getMockVerdict(payload) {
  const isLeakage =
    payload.candidate_signal?.name?.includes("extreme") ||
    payload.candidate_signal?.definition?.includes("20");
  return {
    verdict: isLeakage ? "LEAKAGE_DETECTED" : "REJECT",
    edge_confidence: 12,
    reasons: [
      "DSR prob=0.001 < 0.20 -> strong signal: no alpha (-25)",
      "0 factors pass BH-FDR q=0.10 (pooled) -> no alpha in universe (-15)",
      "WF median Sharpe=-2.10 < -1.0 -> severe out-of-sample loss (-12)",
      "Parameter scan shows single spike -> overfit risk (-10)",
      "Look-ahead test PASS -> no look-ahead bias, results trustworthy (+0)",
      "Strongest regime t-stat=4.56 >= 4.0 -> local regime alpha significant (+15)",
    ],
    verdict_summary: isLeakage
      ? "REJECT this signal. Data leakage detected: naive Sharpe=0.85 vs honest Sharpe=-0.99. The backtest was exploiting future information."
      : "REJECT (confidence=12). No significant edge after overfitting correction.",
    leakage_check: {
      lookahead_test: "PASS",
      is_only_calibration: "ENFORCED",
      naive_sharpe_if_leaked: 0.85,
      honest_sharpe: -0.99,
      gap: 1.84,
      threshold: 0.80,
      direction_flip_detected: isLeakage,
      lookahead_flag: false,
      leaked: isLeakage,
    },
    statistics: {
      dsr_probability: 0.001,
      fdr_significant_factors: 0,
      walk_forward_median_sharpe: -2.10,
      walk_forward_windows: 7,
      oos_sharpe_is_only: -0.99,
      oos_max_drawdown: -0.06,
      parameter_plateau: "spike",
      strongest_regime_bucket: "CHOP_NEUTRAL",
      strongest_ic: -0.30,
      strongest_t_stat: -4.56,
    },
    regime_conditional_finding: {
      note: "CMC F&G shows regime-conditional alpha in CHOP_NEUTRAL",
      bucket: "CHOP_NEUTRAL",
      ic: -0.30,
      t_stat: -4.56,
      p_value: 9e-6,
      interpretation: "Mean-reversion in choppy neutral sentiment — not yet robust for deployment.",
    },
    cmc_data_provenance: {
      fear_greed_source: "CMC proprietary /v3/fear-and-greed/historical (NOT Alternative.me)",
      sample_size: 1075,
      date_range: "2023-06-29 to 2026-06-07",
      access_channels_used: ["rest"],
      historical_channels_documented: ["rest", "mcp", "x402"],
      x402_tx: null,
    },
    billing: { protocol: "x402", price_usdc: 0.50, payment_tx: null, network: "base" },
    meta: { adjudicator_version: "2.1.0", seed: 42, reproducible: true },
  };
}
