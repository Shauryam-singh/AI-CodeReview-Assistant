/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from "react";
import ResultsDashboard from "./ResultsDashboard";
import { 
  GitPullRequest, 
  GitBranch, 
  ShieldCheck, 
  Clock, 
  ArrowRight,
  Loader2,
  AlertCircle,
  Code,
  Zap
} from "lucide-react";

export default function PRInputForm() {
  const [prUrl, setPrUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [statusText, setStatusText] = useState("");

  const loadingStates = [
    "Fetching Pull Request metadata...",
    "Extracting diff changes...",
    "Identifying modified files...",
    "Scanning hunk changes...",
    "Comparing branch security posture..."
  ];

  useEffect(() => {
    let i = 0;
    if (loading) {
      const interval = setInterval(() => {
        setStatusText(loadingStates[i % loadingStates.length]);
        i++;
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [loading]);

  const handleAnalyzePR = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`http://localhost:8000/analyze-pr?pr_url=${encodeURIComponent(prUrl)}`);
      if (!response.ok) throw new Error("Could not access Pull Request. Ensure it is a public repository.");
      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-20">
      {!result ? (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-16 items-center">
          
          {/* LEFT: INFO PANEL */}
          <div className="lg:col-span-2 space-y-10">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-black uppercase tracking-[0.2em]">
                <GitBranch size={14} /> Incremental Audit
              </div>
              <h1 className="text-5xl font-black text-slate-900 tracking-tight leading-[1.1]">
                Scan Your <span className="text-indigo-600">In-Flight</span> Changes
              </h1>
              <p className="text-slate-500 text-lg leading-relaxed font-medium">
                Prevent vulnerabilities from merging. Our PR engine scans only the modified files for immediate feedback.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6">
              <FeatureItem 
                icon={<GitBranch className="text-indigo-500" />} 
                title="Differential Scan" 
                desc="Only analyzes new or modified lines of code." 
              />
              <FeatureItem 
                icon={<ShieldCheck className="text-emerald-500" />} 
                title="Merge Blocker Checks" 
                desc="Identifies critical risks before they hit production." 
              />
              <FeatureItem 
                icon={<Clock className="text-amber-500" />} 
                title="Fast Execution" 
                desc="Optimized for CI/CD workflows and developer speed." 
              />
            </div>
          </div>

          {/* RIGHT: INPUT CARD */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-[3rem] border border-slate-100 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.1)] p-10 md:p-16 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-10 opacity-[0.03] pointer-events-none group-hover:scale-110 transition-transform duration-1000">
                <GitPullRequest size={280} />
              </div>

              <form onSubmit={handleAnalyzePR} className="relative z-10 space-y-8">
                <div className="space-y-4 text-center lg:text-left">
                   <h3 className="text-2xl font-black text-slate-900">PR Analysis</h3>
                   <p className="text-slate-400 text-sm font-medium">Paste a GitHub PR URL to begin the differential scan.</p>
                </div>

                <div className="relative group">
                   <div className="absolute inset-y-0 left-0 pl-7 flex items-center pointer-events-none">
                    <Code className="text-slate-300 group-focus-within:text-indigo-500 transition-all" size={22} />
                  </div>
                  <input
                    type="url"
                    required
                    placeholder="https://github.com/owner/repo/pull/123"
                    value={prUrl}
                    onChange={(e) => setPrUrl(e.target.value)}
                    className="w-full pl-16 pr-8 py-6 bg-slate-50/50 border border-slate-200 rounded-[2.5rem] focus:ring-8 focus:ring-indigo-500/5 focus:border-indigo-500 outline-none text-lg transition-all placeholder:text-slate-300 font-medium"
                  />
                </div>

                <button
                  disabled={loading}
                  className="w-full py-7 bg-indigo-600 text-white font-black rounded-[2.5rem] hover:bg-indigo-500 transition-all shadow-2xl shadow-indigo-200 disabled:bg-slate-300 transform active:scale-[0.98] flex items-center justify-center gap-4 text-lg"
                >
                  {loading ? (
                    <>
                      <Loader2 className="animate-spin" size={24} />
                      <span className="animate-pulse">{statusText}</span>
                    </>
                  ) : (
                    <>
                      <span>Run PR Security Scan</span>
                      <ArrowRight size={22} />
                    </>
                  )}
                </button>
              </form>

              {error && (
                <div className="mt-10 p-6 bg-rose-50 text-rose-600 rounded-[2rem] border border-rose-100 flex items-center gap-4 animate-in slide-in-from-top-4">
                  <AlertCircle size={20} className="shrink-0" />
                  <span className="text-sm font-bold leading-tight">{error}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-12 animate-in fade-in duration-1000">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 bg-slate-900 p-10 rounded-[3rem] text-white">
            <div className="flex items-center gap-6">
              <div className="w-16 h-16 bg-indigo-500/20 rounded-[1.5rem] flex items-center justify-center text-indigo-400">
                <GitPullRequest size={32} />
              </div>
              <div>
                <div className="flex items-center gap-3 mb-2">
                   <span className="px-3 py-1 bg-emerald-500 text-white text-[10px] font-black uppercase tracking-widest rounded-md">Differential Audit Clear</span>
                </div>
                <h2 className="text-4xl font-black tracking-tight italic">PR #{prUrl.split('/').pop()}</h2>
              </div>
            </div>
            <button 
              onClick={() => setResult(null)} 
              className="px-8 py-4 bg-white/10 hover:bg-white/20 text-white text-sm font-bold rounded-2xl transition-all border border-white/10 backdrop-blur-md flex items-center gap-2"
            >
              <Zap size={18} /> New PR Scan
            </button>
          </div>
          <ResultsDashboard data={result} />
        </div>
      )}
    </div>
  );
}

function FeatureItem({ icon, title, desc }: any) {
  return (
    <div className="flex gap-5 group">
      <div className="w-12 h-12 shrink-0 bg-white shadow-lg shadow-slate-100 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110 duration-500">
        {icon}
      </div>
      <div className="space-y-1">
        <h4 className="font-black text-slate-900 text-sm tracking-tight">{title}</h4>
        <p className="text-slate-400 text-xs font-medium leading-relaxed max-w-[240px]">{desc}</p>
      </div>
    </div>
  );
}