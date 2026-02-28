/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState } from "react";
import { 
  BarChart, Bar, XAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell 
} from "recharts";
import { 
  Search, ShieldAlert, AlertTriangle, CheckCircle2, 
  FileCode, ArrowRight, Loader2, Info 
} from "lucide-react";

// Professional Palette
const THEME = {
  error: "#ef4444",    // Red 500
  warning: "#f59e0b",  // Amber 500
  security: "#6366f1", // Indigo 500
  neutral: "#94a3b8",  // Slate 400
  bar: "#1e293b"       // Slate 800
};

// --- MOCK API (Kept for functionality) ---
const analyzePR = async (url: string) => {
  await new Promise(res => setTimeout(res, 1500));
  if (url.includes("error")) return { status: "error", message: "Repository access denied or PR not found." };
  return {
    status: "success",
    results: {
      "TypeScript": [
        { file: "src/auth/session.ts", issues: [
          { tool: "ESLint", line: 15, type: "error", message: "Unused dependency 'lodash' detected." },
          { tool: "Security", line: 42, type: "security", message: "Direct cookie manipulation found." }
        ]},
        { file: "src/utils/logger.ts", issues: [
          { tool: "Sonar", line: 5, type: "warning", message: "Cognitive complexity is too high." }
        ]}
      ],
      "Python": [
        { file: "api/main.py", issues: [
          { tool: "Bandit", line: 35, type: "security", message: "Hardcoded credentials in environment setup." }
        ]}
      ]
    }
  };
};

export default function PRAnalysisDashboard() {
  const [prUrl, setPrUrl] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    const data = await analyzePR(prUrl);
    setResult(data);
    setLoading(false);
  };

  const allIssues = result?.status === "success" 
    ? Object.values(result.results).flat().flatMap((f: any) => f.issues) 
    : [];

  const getBarData = () => {
    const counts: any = {};
    allIssues.forEach((i: any) => counts[i.type] = (counts[i.type] || 0) + 1);
    return Object.entries(counts).map(([name, value]) => ({ name, value }));
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">

      <main className="max-w-7xl mx-auto px-6 py-10">
        
        {/* Hero Section */}
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 mb-4">
            Pull Request <span className="text-indigo-600">Deep Scan</span>
          </h1>
          <p className="text-slate-500 max-w-xl mx-auto">
            Input a public GitHub Pull Request URL to analyze code changes for security vulnerabilities, performance issues, and code quality concerns.
          </p>
        </div>

        {/* Search Bar */}
        <div className="max-w-3xl mx-auto mb-12">
          <form onSubmit={handleSubmit} className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-500 transition-colors" size={20} />
            <input
              type="text"
              placeholder="Paste GitHub Pull Request URL (e.g., github.com/user/repo/pull/1)"
              className="w-full pl-12 pr-32 py-4 bg-white border border-slate-200 rounded-2xl shadow-sm focus:ring-4 focus:ring-indigo-50 focus:border-indigo-500 transition-all outline-none"
              value={prUrl}
              onChange={(e) => setPrUrl(e.target.value)}
            />
            <button
              disabled={loading || !prUrl}
              className="absolute right-2 top-2 bottom-2 px-6 bg-slate-900 text-white rounded-xl font-semibold text-sm hover:bg-slate-800 disabled:opacity-50 transition-all flex items-center gap-2"
            >
              {loading ? <Loader2 className="animate-spin" size={16} /> : "Run Scan"}
            </button>
          </form>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex flex-col items-center py-20 animate-in fade-in slide-in-from-bottom-4">
            <Loader2 className="animate-spin text-indigo-600 mb-4" size={40} />
            <p className="text-slate-500 font-medium text-lg">Deconstructing pull request diffs...</p>
          </div>
        )}

        {/* Error State */}
        {result?.status === "error" && (
          <div className="bg-red-50 border border-red-100 p-4 rounded-xl flex items-center gap-3 text-red-700">
            <AlertTriangle size={20} />
            <p className="font-medium">{result.message}</p>
          </div>
        )}

        {/* Results View */}
        {result?.status === "success" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-in fade-in duration-500">
            
            {/* Left Col: Summary Metrics */}
            <div className="lg:col-span-4 space-y-6">
              <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
                <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-6">Overview</h3>
                <div className="grid grid-cols-2 gap-4 mb-8">
                  <div className="p-4 bg-slate-50 rounded-xl">
                    <p className="text-xs font-semibold text-slate-500 mb-1">Total Issues</p>
                    <p className="text-3xl font-bold">{allIssues.length}</p>
                  </div>
                  <div className="p-4 bg-indigo-50 rounded-xl">
                    <p className="text-xs font-semibold text-indigo-600 mb-1">Security</p>
                    <p className="text-3xl font-bold text-indigo-700">
                      {allIssues.filter((i:any) => i.type === 'security').length}
                    </p>
                  </div>
                </div>

                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getBarData()}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 12, fill: '#64748b'}} />
                      <Tooltip cursor={{fill: '#f8fafc'}} />
                      <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={32}>
                        {getBarData().map((entry: any) => (
                          <Cell key={entry.name} fill={(THEME as any)[entry.name] || THEME.bar} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Right Col: Feed */}
            <div className="lg:col-span-8 space-y-8">
              {Object.entries(result.results).map(([lang, files]: [string, any]) => (
                <div key={lang} className="space-y-4">
                  <div className="flex items-center gap-2 text-slate-400">
                    <FileCode size={18} />
                    <h2 className="text-sm font-bold uppercase tracking-widest">{lang} Environment</h2>
                  </div>
                  
                  {files.map((file: any, fIdx: number) => (
                    <div key={fIdx} className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                      <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
                        <code className="text-sm font-bold text-slate-700">{file.file}</code>
                        {file.issues.length === 0 ? (
                          <span className="text-xs font-bold text-green-600 flex items-center gap-1 bg-green-50 px-2 py-1 rounded">
                            <CheckCircle2 size={12} /> CLEAR
                          </span>
                        ) : (
                          <span className="text-xs font-bold text-slate-400 bg-white border border-slate-200 px-2 py-1 rounded">
                            {file.issues.length} ISSUES
                          </span>
                        )}
                      </div>
                      
                      <div className="divide-y divide-slate-100">
                        {file.issues.map((issue: any, iIdx: number) => (
                          <div key={iIdx} className="px-6 py-4 flex items-start gap-4 hover:bg-slate-50/50 transition-colors">
                            <div className="mt-1">
                              {issue.type === 'security' && <ShieldAlert className="text-indigo-500" size={18} />}
                              {issue.type === 'error' && <AlertTriangle className="text-red-500" size={18} />}
                              {issue.type === 'warning' && <Info className="text-amber-500" size={18} />}
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-1">
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase ${
                                  issue.type === 'security' ? 'bg-indigo-50 border-indigo-100 text-indigo-600' :
                                  issue.type === 'error' ? 'bg-red-50 border-red-100 text-red-600' : 
                                  'bg-amber-50 border-amber-100 text-amber-600'
                                }`}>
                                  {issue.type}
                                </span>
                                <span className="text-xs font-mono text-slate-400">Line {issue.line} • {issue.tool}</span>
                              </div>
                              <p className="text-slate-700 text-sm leading-relaxed">{issue.message}</p>
                            </div>
                            <ArrowRight className="text-slate-300 self-center" size={16} />
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {result?.status === "success" && allIssues.length === 0 && (
          <div className="text-center py-20 bg-white border border-dashed border-slate-300 rounded-3xl">
            <CheckCircle2 className="mx-auto text-green-500 mb-4" size={48} />
            <h3 className="text-xl font-bold mb-1">No issues detected</h3>
            <p className="text-slate-500">This pull request meets all quality and security standards.</p>
          </div>
        )}
      </main>
    </div>
  );
}