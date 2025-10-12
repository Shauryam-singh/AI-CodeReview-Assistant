import { useState } from "react";
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid
} from "recharts";

// Futuristic, luminous color palette
const COLORS = ["#00BFFF", "#00FFFF", "#A020F0", "#00FF7F", "#FF69B4", "#FFA500"];
const BAR_FILL_COLOR = "#00BFFF";

// --- START MOCK API SERVICE (Required for self-contained example) ---
const analyzePR = async (prUrl: string) => {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    if (prUrl.includes("error")) {
        return { status: "error", message: "PR analysis failed. Could not access the requested Pull Request data." };
    }
    
    // Mock successful PR analysis data (only changes relevant to the PR)
    return {
        status: "success",
        results: {
            JavaScript: [
                { file: "src/new_auth.js", issues: [
                    { tool: "ESLint", line: 15, column: 10, type: "error", message: "New dependency 'lodash' imported but not used." }, 
                    { tool: "Security", line: 42, column: 1, type: "security", message: "PR introduces direct use of `document.cookie`." },
                    { tool: "Performance", line: 88, column: 5, type: "warning", message: "Inefficient array mapping in loop, consider `reduce`." }
                ]},
                { file: "src/utils/data.js", issues: [
                    { tool: "JSHint", line: 5, column: 1, type: "warning", message: "Variable 'temp' declared globally." }, 
                ]},
            ],
            Python: [
                { file: "api/routes.py", issues: [
                    { tool: "Flake8", line: 20, column: 5, type: "error", message: "E302: Expected 2 blank lines, found 1." },
                    { tool: "Bandit", line: 35, column: 1, type: "security", message: "B104: Hardcoded sensitive credentials in source." }
                ]},
            ],
            Markdown: [
                { file: "docs/PR_REVIEW.md", issues: [] },
            ]
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

// Helper function for table row color based on issue type
const getIssueRowColor = (type: string) => {
    switch (type.toLowerCase()) {
        case "error": return "bg-red-900/40 text-red-300 border-red-800";
        case "warning": return "bg-yellow-900/40 text-yellow-300 border-yellow-800";
        case "security": return "bg-purple-900/40 text-purple-300 border-purple-800";
        default: return "bg-gray-800/40 text-gray-300 border-gray-700";
    }
};


export default function PRInputForm() {
  const [prUrl, setPrUrl] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prUrl) return;
    setLoading(true);
    setResult(null);
    try {
      // NOTE: Using the mock analyzePR function defined above
      const data = await analyzePR(prUrl);
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  const getChartData = (issues: Issue[]) => {
    const countMap: { [key: string]: number } = {};
    issues.forEach(i => {
      // Ensure type is treated as lowercase for consistent keys
      const key = i.type?.toLowerCase() || "unknown"; 
      countMap[key] = (countMap[key] || 0) + 1;
    });
    // Filter out types with 0 count
    return Object.entries(countMap).map(([name, value]) => ({ name, value })).filter(item => item.value > 0);
  };

  const getFileBarData = (files: any[]) => 
    files.map(f => ({ name: f.file, issues: f.issues.length })).filter(data => data.issues > 0);

  // Calculate total number of issues found in the PR
  const totalIssues = result?.status === "success" ? 
    Object.values(result.results).flat().flatMap((f: any) => f.issues).length : 0;


  return (
    <div className="min-h-screen bg-gray-950 text-gray-50 p-6 sm:p-10 font-mono">
      <h1 className="text-4xl font-extrabold mb-8 tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-300 to-purple-500">
        // PR Analysis Matrix
      </h1>

      {/* PR Input Form */}
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 mb-10 p-5 rounded-xl bg-gray-900/60 shadow-2xl border border-gray-800">
        <input
          type="text"
          value={prUrl}
          onChange={(e) => setPrUrl(e.target.value)}
          placeholder="Enter GitHub Pull Request URL"
          className="flex-1 bg-gray-800/70 text-gray-200 placeholder-gray-500 p-4 rounded-lg border border-cyan-500/30 focus:outline-none focus:ring-2 focus:ring-cyan-500 transition duration-300"
        />
        <button
          type="submit"
          disabled={loading || !prUrl}
          className={`px-8 py-3 rounded-lg shadow-lg font-bold transition duration-300 transform uppercase ${
            loading || !prUrl 
              ? "bg-gray-700 text-gray-500 cursor-not-allowed" 
              : "bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 hover:scale-[1.02] shadow-blue-500/50"
          }`}
        >
          {loading ? "PARSING DELTA..." : "ANALYZE PR"}
        </button>
      </form>

      {/* Status Messages */}
      {loading && (
        <div className="text-center py-20 text-xl text-cyan-400 animate-pulse">
          Reviewing code diff... Analyzing patch integrity.
        </div>
      )}

      {result && result.status === "error" && (
        <div className="bg-red-900/40 border border-red-600 text-red-300 p-6 rounded-lg font-bold">
          <span className="text-2xl mr-2">&#9888;</span> CRITICAL FAILURE: {result.message}
        </div>
      )}

      {/* Analysis Results Dashboard */}
      {result && result.status === "success" && (
        <div className="space-y-12">
            
          {/* Global Summary Card */}
          <div className="p-6 rounded-xl bg-gray-900/60 border border-cyan-700/50 shadow-xl">
            <h2 className="text-2xl font-bold mb-4 text-cyan-400 border-b border-gray-800 pb-3">PR Summary Report</h2>
            <p className="text-xl">
              Total Issues Found: <span className={`font-extrabold text-2xl ml-2 ${totalIssues > 5 ? 'text-red-400' : totalIssues > 0 ? 'text-yellow-400' : 'text-green-400'}`}>{totalIssues}</span>
            </p>
            {totalIssues > 0 && (
                <div className="w-full h-80 mt-6">
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={getChartData(Object.values(result.results).flat().flatMap((f: any) => f.issues))}
                                dataKey="value"
                                nameKey="name"
                                cx="50%"
                                cy="50%"
                                outerRadius={100}
                                labelLine={false}
                                label={({ name, percent }: any) => `${String(name).toUpperCase()}: ${((Number(percent) || 0) * 100).toFixed(0)}%`}
                            >
                                {getChartData(Object.values(result.results).flat().flatMap((f: any) => f.issues)).map((_, i) => (
                                    <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip content={<ChartTooltip />} />
                            <Legend layout="horizontal" align="center" verticalAlign="bottom" wrapperStyle={{ color: '#E5E7EB' }} />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            )}
          </div>
            
          {/* Language-Specific Analysis Panels */}
          {Object.entries(result.results).map(([lang, files]: [string, any], idx: number) => {
            const fileList: any[] = Array.isArray(files) ? files : [];
            const allIssues: Issue[] = fileList.flatMap(f => f.issues);

            if (fileList.length === 0 && allIssues.length === 0) return null;

            return (
              <div key={idx} className="p-6 rounded-xl bg-gray-900/60 border border-blue-700/50 shadow-xl space-y-8">
                <h2 className="text-3xl font-bold tracking-tight text-blue-400">{`// Language: ${lang} Delta`}</h2>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    
                    {/* Bar Chart: Issues per file */}
                    {getFileBarData(fileList).length > 0 && (
                        <div className="p-4 bg-gray-800/70 rounded-lg border border-gray-700/50 shadow-inner col-span-2">
                            <h3 className="text-xl font-semibold mb-2 text-purple-400">Changed File Contamination</h3>
                            <div className="w-full h-80">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart 
                                        data={getFileBarData(fileList)} 
                                        margin={{ top: 5, right: 10, left: 10, bottom: 5 }}
                                    >
                                        <CartesianGrid stroke="#374151" strokeDasharray="3 3" />
                                        <XAxis dataKey="name" angle={-25} textAnchor="end" height={100} stroke="#9CA3AF" interval={0} style={{ fontSize: '12px' }}/>
                                        <YAxis stroke="#9CA3AF" />
                                        <Tooltip content={<ChartTooltip />} />
                                        <Bar dataKey="issues" fill={BAR_FILL_COLOR} radius={[5, 5, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}
                </div>

                {/* File-wise Issues Table */}
                <div className="space-y-4">
                  <h3 className="text-2xl font-bold text-cyan-400 pt-4 border-t border-gray-800">Patch Audit Details</h3>
                  {fileList.map((file, fIdx) => (
                    <div key={fIdx} className="bg-gray-900 p-4 rounded-lg border border-gray-700 shadow-lg">
                      <h4 className="font-bold text-lg mb-3 text-cyan-300 border-b border-gray-700/50 pb-2">{file.file}</h4>
                      
                      {file.issues.length === 0 ? (
                        <p className="text-green-400">File change approved. No issues found. ✅</p>
                      ) : (
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
                              {file.issues.map((issue: Issue, iIdx: number) => (
                                <tr key={iIdx} className={`transition duration-150 ${getIssueRowColor(issue.type)} border-b border-gray-800`}>
                                  <td className="px-3 py-2 text-sm">{issue.tool}</td>
                                  <td className="px-3 py-2 text-sm font-semibold">{issue.type.toUpperCase()}</td>
                                  <td className="px-3 py-2 text-sm">{issue.line ?? "-"}</td>
                                  <td className="px-3 py-2 text-sm">{issue.message}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
      
        {/* No Issues Found Message */}
        {result && result.status === "success" && totalIssues === 0 && (
            <div className="text-center py-10">
                <p className="text-2xl text-green-400 drop-shadow-[0_0_5px_rgba(74,222,128,0.5)]">
                    PULL REQUEST APPROVED. Zero critical issues detected. ✅
                </p>
            </div>
        )}
    </div>
  );
}
