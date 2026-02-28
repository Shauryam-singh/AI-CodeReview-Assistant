/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useMemo } from "react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer
} from "recharts";
import { 
  Search, ShieldAlert, AlertTriangle, CheckCircle2, 
  FileCode, Loader2, Info, Activity, LayoutDashboard
} from "lucide-react";

const CHART_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316"];

// --- MOCK API SERVICE ---
const analyzeRepo = async (repo: string) => {
  await new Promise(resolve => setTimeout(resolve, 1500));
  if (repo.includes("error")) {
    return { status: "error", message: "Repository access denied. Ensure the repository is public or your token is valid." };
  }
  return {
    status: "success",
    results: {
      TypeScript: [
        { file: "src/user.ts", issues: [{ tool: "ESLint", line: 10, type: "error", message: "Interface naming convention violation." }, { tool: "Security", line: 55, type: "security", message: "Unsanitized user input in API call." }] },
        { file: "src/utils.ts", issues: [{ tool: "TS Lint", line: 25, type: "error", message: "Avoid 'any' type." }] },
      ],
      Go: [
        { file: "pkg/handler.go", issues: [{ tool: "GoSec", line: 30, type: "security", message: "Hardcoded secret key detected." }] },
        { file: "cmd/main.go", issues: [{ tool: "GoFmt", line: 5, type: "warning", message: "Missing trailing comma." }] },
      ],
    },
  };
};

export default function RepoAnalysis() {
  const [repo, setRepo] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<string>("all");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repo) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await analyzeRepo(repo);
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  const healthScore = useMemo(() => {
    if (!result || result.status !== "success") return 100;
    let score = 100;
    Object.values(result.results).flat().flatMap((f: any) => f.issues).forEach((i: any) => {
      if (i.type === "security") score -= 10;
      else if (i.type === "error") score -= 4;
      else score -= 1;
    });
    return Math.max(score, 0);
  }, [result]);

  const allIssues = useMemo(() => {
    if (!result || result.status !== "success") return [];
    return Object.values(result.results).flat().flatMap((f: any) => f.issues);
  }, [result]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased">
      <main className="max-w-7xl mx-auto px-6 py-10">
        
        {/* Hero Section */}
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 mb-4">
            Repository <span className="text-indigo-600">Deep Scan</span>
          </h1>
          <p className="text-slate-500 max-w-xl mx-auto">
            Input a public GitHub repository URL to generate a comprehensive quality and security audit.
          </p>
        </div>

        {/* Search Bar */}
        <div className="max-w-3xl mx-auto mb-16">
          <form onSubmit={handleSubmit} className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-indigo-500 transition-colors" size={20} />
            <input
              type="text"
              placeholder="https://github.com/organization/project"
              className="w-full pl-12 pr-32 py-4 bg-white border border-slate-200 rounded-2xl shadow-sm focus:ring-4 focus:ring-indigo-50 focus:border-indigo-500 transition-all outline-none"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
            />
            <button
              disabled={loading || !repo}
              className="absolute right-2 top-2 bottom-2 px-6 bg-slate-900 text-white rounded-xl font-semibold text-sm hover:bg-slate-800 disabled:opacity-50 transition-all flex items-center gap-2"
            >
              {loading ? <Loader2 className="animate-spin" size={16} /> : "Run Analysis"}
            </button>
          </form>
        </div>

        {loading && (
          <div className="flex flex-col items-center py-20">
            <Loader2 className="animate-spin text-indigo-600 mb-4" size={48} />
            <p className="text-slate-500 font-medium">Indexing files and running security heuristics...</p>
          </div>
        )}

        {result?.status === "error" && (
          <div className="max-w-2xl mx-auto bg-red-50 border border-red-100 p-4 rounded-xl flex items-center gap-3 text-red-700">
            <AlertTriangle size={20} />
            <p className="font-medium text-sm">{result.message}</p>
          </div>
        )}

        {result?.status === "success" && (
          <div className="space-y-8 animate-in fade-in duration-700">
            
            {/* Top Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-5">
                <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center">
                  <Activity size={24} />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Health Index</p>
                  <p className={`text-3xl font-bold ${healthScore > 80 ? 'text-green-600' : 'text-amber-500'}`}>{healthScore}%</p>
                </div>
              </div>
              
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-5">
                <div className="w-12 h-12 bg-red-50 text-red-600 rounded-xl flex items-center justify-center">
                  <ShieldAlert size={24} />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Security Risks</p>
                  <p className="text-3xl font-bold text-slate-900">
                    {allIssues.filter((i:any) => i.type === 'security').length}
                  </p>
                </div>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-5">
                <div className="w-12 h-12 bg-slate-100 text-slate-600 rounded-xl flex items-center justify-center">
                  <LayoutDashboard size={24} />
                </div>
                <div>
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Total Findings</p>
                  <p className="text-3xl font-bold text-slate-900">{allIssues.length}</p>
                </div>
              </div>
            </div>

            {/* Analysis Detail Section */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              
              {/* Controls & Mini Chart */}
              <div className="lg:col-span-4 space-y-6">
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                  <h3 className="text-sm font-bold text-slate-900 mb-6 uppercase tracking-wider">Filters</h3>
                  <div className="flex flex-col gap-2 mb-8">
                    {["all", "error", "warning", "security"].map((f) => (
                      <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all text-left flex items-center justify-between ${
                          filter === f ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200' : 'text-slate-500 hover:bg-slate-50'
                        }`}
                      >
                        <span className="capitalize">{f}</span>
                        {filter === f && <CheckCircle2 size={14} />}
                      </button>
                    ))}
                  </div>

                  <h3 className="text-sm font-bold text-slate-900 mb-4 uppercase tracking-wider">Language Volume</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={Object.entries(result.results).map(([name, files]: any) => ({
                            name,
                            value: files.flatMap((f: any) => f.issues).length
                          }))}
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {Object.keys(result.results).map((_, index) => (
                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Main Issue Feed */}
              <div className="lg:col-span-8 space-y-6">
                {Object.entries(result.results).map(([lang, files]: [string, any]) => (
                  <div key={lang} className="space-y-4">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                      <FileCode size={18} />
                      <h2 className="text-xs font-bold uppercase tracking-[0.2em]">{lang} Source Audit</h2>
                    </div>

                    {files.map((file: any, fIdx: number) => {
                      const filteredIssues = file.issues.filter((i: any) => filter === "all" || i.type === filter);
                      if (filteredIssues.length === 0) return null;

                      return (
                        <div key={fIdx} className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                          <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
                            <code className="text-xs font-bold text-slate-600">{file.file}</code>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{filteredIssues.length} findings</span>
                          </div>
                          <div className="divide-y divide-slate-100">
                            {filteredIssues.map((issue: any, iIdx: number) => (
                              <div key={iIdx} className="px-6 py-4 flex items-start gap-4 hover:bg-slate-50 transition-colors">
                                <div className="mt-1">
                                  {issue.type === 'security' && <ShieldAlert className="text-indigo-500" size={18} />}
                                  {issue.type === 'error' && <AlertTriangle className="text-red-500" size={18} />}
                                  {issue.type === 'warning' && <Info className="text-amber-500" size={18} />}
                                </div>
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase ${
                                      issue.type === 'security' ? 'bg-indigo-50 border-indigo-100 text-indigo-600' :
                                      issue.type === 'error' ? 'bg-red-50 border-red-100 text-red-600' : 
                                      'bg-amber-50 border-amber-100 text-amber-600'
                                    }`}>
                                      {issue.type}
                                    </span>
                                    <span className="text-xs font-mono text-slate-400">Line {issue.line} • {issue.tool}</span>
                                  </div>
                                  <p className="text-slate-700 text-sm">{issue.message}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>

            </div>
          </div>
        )}
      </main>
    </div>
  );
}