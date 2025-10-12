import { useState, useMemo } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

// Futuristic, luminous color palette
const COLORS = ["#00BFFF", "#00FFFF", "#A020F0", "#00FF7F", "#FF69B4", "#FFA500"];

// --- START MOCK API SERVICE (Required for self-contained example) ---
const analyzeRepo = async (repo: string) => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    if (repo.includes("error")) {
        return { status: "error", message: "Repository not found or access denied. Check URL and permissions." };
    }
    
    // Mock successful data structure
    return {
        status: "success",
        results: {
            TypeScript: [
                { file: "src/user.ts", issues: [{ tool: "ESLint", line: 10, column: 5, type: "error", message: "Interface naming convention violation." }, { tool: "Security", line: 55, column: 1, type: "security", message: "Unsanitized user input in API call." }] },
                { file: "src/utils.ts", issues: [{ tool: "TS Lint", line: 22, column: 1, type: "warning", message: "Function 'fetchData' declared but never used." }, { tool: "TS Lint", line: 25, column: 1, type: "error", message: "Avoid 'any' type." }] },
            ],
            Go: [
                { file: "pkg/handler.go", issues: [{ tool: "GoVet", line: 15, column: 1, type: "warning", message: "Inconsistent error handling on I/O operation." }, { tool: "GoSec", line: 30, column: 1, type: "security", message: "Hardcoded secret key detected." }] },
                { file: "cmd/main.go", issues: [{ tool: "GoFmt", line: 5, column: 1, type: "warning", message: "Missing trailing comma in struct definition." }] },
                { file: "README.md", issues: [] },
            ],
        },
    };
};
// --- END MOCK API SERVICE ---

interface Issue {
  tool: string;
  line: number | null;
  column: number | null;
  type: string;
  message: string;
  symbol?: string;
  severity?: string;
}

// Custom Tooltip for dark theme (Recharts)
const ChartTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-800/95 border border-gray-600 p-3 rounded shadow-lg text-sm text-gray-200">
          <p className="font-semibold text-cyan-400">{label}</p>
          <p>Issues: <span className="text-purple-400">{payload[0].value}</span></p>
        </div>
      );
    }
    return null;
};

export default function PRInputForm() {
  const [repo, setRepo] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repo) return;
    setLoading(true);
    setResult(null); 
    try {
      // NOTE: Using the mock analyzeRepo function defined above
      const data = await analyzeRepo(repo); 
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  // Aggregate issues per language
  const getRepoSummaryData = (results: any) => {
    const summary: { [lang: string]: number } = {};
    Object.entries(results).forEach(([lang, files]: [string, any]) => {
      summary[lang] = files
        .flatMap((f: any) => f.issues)
        .filter((i: Issue) => filter === "all" || i.type === filter).length;
    });
    // Filter out languages with 0 issues after filtering/searching
    return Object.entries(summary)
        .map(([name, value]) => ({ name, value }))
        .filter(item => item.value > 0);
  };

  // Aggregate issues per type/severity
  const getChartData = (issues: Issue[]) => {
    const countMap: { [key: string]: number } = {};
    issues
      .filter((i) => filter === "all" || i.type === filter)
      .filter((i) => i.message.toLowerCase().includes(search.toLowerCase()))
      .forEach((i) => {
        const key = i.type || i.severity || "unknown";
        countMap[key] = (countMap[key] || 0) + 1;
      });
    return Object.entries(countMap).map(([name, value]) => ({ name, value }));
  };

  const getFileBarData = (files: any[]) =>
    files.map((f) => ({
      name: f.file,
      issues: f.issues.filter(
        (i: Issue) =>
          (filter === "all" || i.type === filter) &&
          i.message.toLowerCase().includes(search.toLowerCase())
      ).length,
    })).filter(data => data.issues > 0);

  // Calculate repo health score: enhanced weighted metric
  const repoHealthScore = useMemo(() => {
    if (!result || result.status !== "success") return 100;
    let weightedScore = 100;
    
    Object.values(result.results).forEach((files: any) => {
      files.forEach((f: any) => {
        f.issues.forEach((i: Issue) => {
          // Increased weighting for futuristic feel:
          if (i.type === "security") weightedScore -= 10; 
          else if (i.type === "error") weightedScore -= 4;
          else if (i.type === "warning") weightedScore -= 1;
        });
      });
    });
    return Math.max(Math.round(weightedScore), 0);
  }, [result]);

  const getHealthColor = (score: number) => {
    if (score >= 85) return "text-green-400 drop-shadow-[0_0_5px_rgba(74,222,128,0.5)]";
    if (score >= 60) return "text-yellow-400 drop-shadow-[0_0_5px_rgba(251,191,36,0.5)]";
    return "text-red-400 drop-shadow-[0_0_5px_rgba(248,113,113,0.5)]";
  };
  
  const getFilterColor = (f: string) => {
      switch (f) {
          case "error": return "border-red-500 text-red-400 hover:border-red-400";
          case "warning": return "border-yellow-500 text-yellow-400 hover:border-yellow-400";
          case "security": return "border-purple-500 text-purple-400 hover:border-purple-400";
          default: return "border-cyan-500 text-cyan-400 hover:border-cyan-400";
      }
  };
  
  const getIssueRowColor = (type: string) => {
      switch (type) {
          case "error": return "bg-red-900/40 text-red-300 border-red-800";
          case "warning": return "bg-yellow-900/40 text-yellow-300 border-yellow-800";
          case "security": return "bg-purple-900/40 text-purple-300 border-purple-800";
          default: return "bg-gray-800/40 text-gray-300 border-gray-700";
      }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-50 p-6 sm:p-10 font-mono">
      <h1 className="text-4xl font-extrabold mb-8 tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-cyan-300 to-purple-500">
        // AI Code Analysis Console
      </h1>

      {/* Repo Input */}
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 mb-10 p-5 rounded-xl bg-gray-900/60 shadow-2xl border border-gray-800">
        <input
          type="text"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="Enter GitHub repo URL (e.g., https://github.com/user/repo)"
          className="flex-1 bg-gray-800/70 text-gray-200 placeholder-gray-500 p-4 rounded-lg border border-cyan-500/30 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition duration-300"
        />
        <button
          type="submit"
          disabled={loading || !repo}
          className={`px-8 py-3 rounded-lg shadow-lg font-bold transition duration-300 transform uppercase ${
            loading || !repo 
              ? "bg-gray-700 text-gray-500 cursor-not-allowed" 
              : "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 hover:scale-[1.02] shadow-blue-500/50"
          }`}
        >
          {loading ? "SCANNING..." : "INITIATE ANALYSIS"}
        </button>
      </form>

      {/* Loading/Error Messages */}
      {loading && (
        <div className="text-center py-20 text-xl text-cyan-400 animate-pulse">
          Processing code matrix... Stand by.
        </div>
      )}

      {result && result.status === "error" && (
        <div className="bg-red-900/40 border border-red-600 text-red-300 p-6 rounded-lg font-bold">
          <span className="text-2xl mr-2">&#9888;</span> EXECUTION FAILURE: {result.message}
        </div>
      )}

      {/* Filters and Health Score */}
      {result && result.status === "success" && (
        <div className="flex flex-col md:flex-row justify-between items-center mb-8 p-4 rounded-xl bg-gray-900/60 border border-gray-700/50 shadow-lg">
          <div className="flex flex-wrap gap-2 mb-4 md:mb-0">
            {["all", "error", "warning", "security"].map((f) => (
              <button
                key={f}
                className={`px-4 py-2 rounded-full text-sm font-semibold transition duration-300 border ${
                  filter === f 
                    ? `bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg shadow-cyan-500/30 border-none` 
                    : `bg-gray-800/50 ${getFilterColor(f)} text-gray-300`
                }`}
                onClick={() => setFilter(f)}
              >
                {f === "all" ? "ALL ISSUES" : f.toUpperCase()}
              </button>
            ))}
          </div>
          
          <input
            type="text"
            placeholder="Search issues (keyword filtering)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border p-2 rounded-lg bg-gray-800/70 text-gray-200 placeholder-gray-500 flex-1 min-w-[200px] max-w-sm focus:border-purple-500 transition duration-300"
          />
          
          <div className="ml-0 md:ml-auto font-extrabold text-lg mt-4 md:mt-0">
            REPO HEALTH INDEX:{" "}
            <span className={`${getHealthColor(repoHealthScore)} text-2xl`}>
              {repoHealthScore}%
            </span>
          </div>
        </div>
      )}

      {/* Repo Summary Chart */}
      {result && result.status === "success" && getRepoSummaryData(result.results).length > 0 && (
        <div className="mb-8 p-6 rounded-xl bg-gray-900/60 border border-purple-700/50 shadow-xl">
          <h2 className="text-2xl font-bold mb-4 text-cyan-400">Total Issue Distribution by Language</h2>
          <div className="w-full h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={getRepoSummaryData(result.results)}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  labelLine={false}
                  label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? "Unknown"}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                >
                  {getRepoSummaryData(result.results).map((_, i) => (
                    <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip />} />
                <Legend layout="horizontal" align="center" verticalAlign="bottom" wrapperStyle={{ color: '#E5E7EB' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Language-specific Charts & Tables */}
      {result &&
        result.status === "success" &&
        Object.entries(result.results).map(([lang, files]: [string, any], idx: number) => {
          const fileList: any[] = Array.isArray(files) ? files : [];
          const allIssues: Issue[] = fileList.flatMap((f) => f.issues);

          const filteredAllIssues = allIssues.filter(
            (i) => (filter === "all" || i.type === filter) && i.message.toLowerCase().includes(search.toLowerCase())
          );
            
          // Only render analysis panel if there are issues or files to show
          if (filteredAllIssues.length === 0 && getFileBarData(fileList).length === 0) return null;

          return (
            <div key={idx} className="mb-10 p-6 rounded-xl bg-gray-900/60 border border-blue-700/50 shadow-xl space-y-8">
              <h2 className="text-3xl font-bold tracking-tight text-blue-400">{`// ${lang} System Log`}</h2>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                 {/* Pie Chart: Issue Type Distribution per language */}
                 {filteredAllIssues.length > 0 && (
                    <div className="p-4 bg-gray-800/70 rounded-lg border border-gray-700/50 shadow-inner">
                        <h3 className="text-xl font-semibold mb-2 text-purple-400">Issue Type Breakdown</h3>
                        <div className="w-full h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={getChartData(filteredAllIssues)}
                                        dataKey="value"
                                        nameKey="name"
                                        cx="50%"
                                        cy="50%"
                                        outerRadius={80}
                                        label
                                    >
                                        {getChartData(filteredAllIssues).map((_, i) => (
                                            <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip content={<ChartTooltip />} />
                                    <Legend />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                 )}
                
                {/* Bar Chart: Issues per file */}
                {getFileBarData(fileList).length > 0 && (
                    <div className="p-4 bg-gray-800/70 rounded-lg border border-gray-700/50 shadow-inner">
                        <h3 className="text-xl font-semibold mb-2 text-purple-400">File Hotspots (Issues per File)</h3>
                        <div className="w-full h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                    data={getFileBarData(fileList)}
                                    margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
                                >
                                    {/* Dark theme grid, axes, and text */}
                                    <CartesianGrid stroke="#374151" strokeDasharray="3 3" /> 
                                    <XAxis dataKey="name" angle={-25} textAnchor="end" height={100} stroke="#9CA3AF" interval={0} style={{ fontSize: '12px' }}/>
                                    <YAxis stroke="#9CA3AF" />
                                    <Tooltip content={<ChartTooltip />} />
                                    <Bar dataKey="issues" fill="#00BFFF" radius={[5, 5, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}
              </div>

              {/* File-wise Issues Table */}
              <div className="space-y-4">
                <h3 className="text-2xl font-bold text-cyan-400 pt-4 border-t border-gray-800">Detailed Code Audit</h3>
                {fileList.map((file, fIdx) => {
                  const filteredIssues = file.issues.filter(
                    (i: Issue) =>
                      (filter === "all" || i.type === filter) &&
                      i.message.toLowerCase().includes(search.toLowerCase())
                  );
                  
                  if (filteredIssues.length === 0) return null;

                  return (
                    <div key={fIdx} className="bg-gray-900 p-4 rounded-lg border border-gray-700 shadow-lg">
                      <h4 className="font-bold text-lg mb-3 text-cyan-300 border-b border-gray-700/50 pb-2">{file.file}</h4>
                      
                      <div className="overflow-x-auto">
                        <table className="min-w-full">
                          <thead className="bg-gray-800 text-gray-400 uppercase text-xs tracking-wider">
                            <tr>
                              <th className="px-3 py-2 text-left border-b border-gray-700">Tool</th>
                              <th className="px-3 py-2 text-left border-b border-gray-700">Type</th>
                              <th className="px-3 py-2 text-left border-b border-gray-700">Line</th>
                              <th className="px-3 py-2 text-left border-b border-gray-700">Message</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredIssues.map((issue: Issue, iIdx: number) => (
                              <tr key={iIdx} className={`hover:bg-gray-700 transition duration-150 ${getIssueRowColor(issue.type)} border-b border-gray-800`}>
                                <td className="px-3 py-2 text-sm">{issue.tool}</td>
                                <td className={`px-3 py-2 text-sm font-semibold`}>
                                    {issue.type.toUpperCase()}
                                </td>
                                <td className="px-3 py-2 text-sm">{issue.line ?? "-"}</td>
                                <td className="px-3 py-2 text-sm">{issue.message}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
        
        {/* No Issues Found Message */}
        {result && result.status === "success" && (
            <div className="text-center py-10">
                {Object.values(result.results).flat().flatMap((f: any) => f.issues).length === 0 && (
                    <p className="text-2xl text-green-400 drop-shadow-[0_0_5px_rgba(74,222,128,0.5)]">
                        CODEBASE CLEAN. No issues detected in the primary analysis run. ✅
                    </p>
                )}
            </div>
        )}
    </div>
  );
}
