/* eslint-disable react-hooks/exhaustive-deps */
/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect } from "react";
import ResultsDashboard from "./ResultsDashboard";
import { 
  Lock, 
  Cpu, 
  Globe, 
  Zap, 
  AlertTriangle,
  Loader2,
  Database,
  ArrowRight,
  Fingerprint
} from "lucide-react";

export default function FullRepoInputForm() {
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [scanStep, setScanStep] = useState(0);

  const steps = [
    "Cloning remote repository...",
    "Running Semgrep static analysis...",
    "Building Abstract Syntax Tree (AST)...",
    "Scanning for exposed secrets & API keys...",
    "Finalizing security report..."
  ];

  useEffect(() => {
    let interval: any;
    if (loading && scanStep < steps.length - 1) {
      interval = setInterval(() => {
        setScanStep(prev => prev + 1);
      }, 3000); 
    }
    return () => clearInterval(interval);
  }, [loading, scanStep]);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setScanStep(0);
    setError("");
    setResult(null);

    try {
      const response = await fetch("http://localhost:8000/analyze/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl }),
      });
      if (!response.ok) throw new Error("Analysis engine failed to process this repository.");
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
          
          {/* LEFT: AUDIT CAPABILITIES PANEL */}
          <div className="lg:col-span-2 space-y-10">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[10px] font-black uppercase tracking-[0.2em]">
                <Database size={14} /> Full System Audit
              </div>
              <h1 className="text-5xl font-black text-slate-900 tracking-tight leading-[1.1]">
                Scan Your <span className="text-indigo-600">Entire</span> Codebase
              </h1>
              <p className="text-slate-500 text-lg leading-relaxed font-medium">
                Our deep-scan engine performs a recursive security audit across every file and dependency in your repository.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-6">
              <FeatureItem 
                icon={<Lock className="text-rose-500" />}
                title="Deep Secret Scanning"
                desc="Detects AWS keys, Stripe tokens, and private .env files."
              />
              <FeatureItem 
                icon={<Cpu className="text-indigo-500" />}
                title="Logic Flaw Analysis"
                desc="Identifies broken access control and insecure logic."
              />
              <FeatureItem 
                icon={<Fingerprint className="text-emerald-500" />}
                title="Vulnerability Mapping"
                desc="Cross-references findings with CVE and OWASP databases."
              />
            </div>
          </div>

          {/* RIGHT: INPUT ACTION CARD */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-[3rem] border border-slate-100 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.1)] p-10 md:p-16 relative overflow-hidden group">
              <div className="absolute -top-24 -right-24 w-64 h-64 bg-indigo-100/40 rounded-full blur-3xl transition-all group-hover:bg-indigo-200/40 duration-700" />
              
              <form onSubmit={handleAnalyze} className="relative z-10 space-y-8">
                <div className="space-y-4 text-center lg:text-left">
                   <h3 className="text-2xl font-black text-slate-900">Initialize Scan</h3>
                   <p className="text-slate-400 text-sm font-medium">Enter a public repository URL to begin.</p>
                </div>

                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-7 flex items-center pointer-events-none">
                    <Globe className="text-slate-300 group-focus-within:text-indigo-500 transition-all" size={22} />
                  </div>
                  <input
                    type="url"
                    required
                    placeholder="https://github.com/organization/repo"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
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
                      <span className="animate-pulse">{steps[scanStep]}</span>
                    </>
                  ) : (
                    <>
                      <span>Launch Global Audit</span>
                      <ArrowRight size={22} />
                    </>
                  )}
                </button>
              </form>

              {error && (
                <div className="mt-10 p-6 bg-rose-50 border border-rose-100 rounded-[2rem] flex items-center gap-4 text-rose-600 animate-in slide-in-from-top-4">
                  <AlertTriangle className="shrink-0" size={20} />
                  <p className="text-sm font-bold leading-tight">{error}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-12 animate-in fade-in duration-1000">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 bg-white p-10 rounded-[3rem] border border-slate-100 shadow-xl shadow-slate-200/50">
            <div>
              <div className="flex items-center gap-3 mb-4">
                 <span className="px-4 py-1.5 bg-indigo-600 text-white text-[10px] font-black uppercase tracking-[0.2em] rounded-full">Global Report</span>
                 <span className="text-slate-400 text-xs font-bold tracking-widest uppercase">ID: {Math.random().toString(36).substr(2, 9).toUpperCase()}</span>
              </div>
              <h2 className="text-5xl font-black text-slate-900 tracking-tighter italic">
                {repoUrl.split('/').pop()}
              </h2>
            </div>
            <button 
              onClick={() => setResult(null)} 
              className="px-8 py-4 bg-white/10 hover:bg-white/20 text-white text-sm font-bold rounded-2xl transition-all border border-white/10 backdrop-blur-md flex items-center gap-2"
            >
              <Zap size={20} className="group-hover:text-indigo-600 transition-colors" /> New Audit
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