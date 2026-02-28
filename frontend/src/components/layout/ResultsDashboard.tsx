/* eslint-disable @typescript-eslint/no-explicit-any */
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import {
  ShieldAlert, FileCode, Search, Activity,
  CheckCircle2, ChevronDown, Terminal, AlertCircle, Info,
  Code2, ExternalLink
} from 'lucide-react';
import { useState } from 'react';

interface Issue {
  file: string;
  line?: number;
  language?: string;
  severity: string;
  message: string;
  risk?: string;
  suggestion?: string;
  tool: string;
  snippet?: string;
}

interface AnalysisResult {
  status: string;
  total_files_found: number;
  total_files_scanned: number;
  issues: Issue[];
}

export default function ResultsDashboard({ data }: { data: AnalysisResult }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const issues = data.issues || [];

  // Data Normalization for Charts
  const severityCounts = issues.reduce((acc: any, issue) => {
    const sev = issue.severity.toUpperCase();
    acc[sev] = (acc[sev] || 0) + 1;
    return acc;
  }, {});

  const severityData = [
    { name: 'High', value: (severityCounts['HIGH'] || 0) + (severityCounts['CRITICAL'] || 0), color: '#f43f5e' },
    { name: 'Medium', value: (severityCounts['MEDIUM'] || 0) + (severityCounts['WARNING'] || 0), color: '#fbbf24' },
    { name: 'Low', value: (severityCounts['LOW'] || 0) + (severityCounts['INFO'] || 0), color: '#38bdf8' },
  ].filter(d => d.value > 0);

  const toolCounts = issues.reduce((acc: any, issue) => {
    acc[issue.tool] = (acc[issue.tool] || 0) + 1;
    return acc;
  }, {});

  const toolData = Object.keys(toolCounts).map(tool => ({
    name: tool.split('-')[0].toUpperCase(), // Clean tool name for UI
    count: toolCounts[tool]
  }));

  const healthScore = issues.length === 0 ? 100 : Math.max(0, 100 - issues.length * 3);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-1000">
      
      {/* --- TOP ROW: KPI STAT CARDS --- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Files Found" 
          value={data.total_files_found} 
          icon={<FileCode size={20} className="text-slate-500" />} 
          color="bg-slate-50" 
        />
        <StatCard 
          title="Files Scanned" 
          value={data.total_files_scanned} 
          icon={<Search size={20} className="text-indigo-500" />} 
          color="bg-indigo-50" 
        />
        <StatCard 
          title="Total Issues" 
          value={issues.length} 
          icon={<ShieldAlert size={20} className="text-rose-500" />} 
          color="bg-rose-50" 
        />
        <HealthStatCard value={healthScore} />
      </div>

      {/* --- MIDDLE ROW: DATA VISUALIZATIONS --- */}
      {issues.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Pie Chart: Risk Level */}
          <ChartCard title="Security Risk Profile" className="lg:col-span-1">
            <div className="h-[250px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie 
                    data={severityData} 
                    dataKey="value" 
                    innerRadius={65} 
                    outerRadius={90} 
                    paddingAngle={8}
                    stroke="none"
                  >
                    {severityData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)' }} 
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex flex-wrap justify-center gap-4 mt-2">
              {severityData.map((s) => (
                <div key={s.name} className="flex items-center gap-1.5 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color }} /> {s.name}
                </div>
              ))}
            </div>
          </ChartCard>

          {/* Bar Chart: Tool Effectiveness */}
          <ChartCard title="Detections by Engine" className="lg:col-span-2">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={toolData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 600 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip 
                  cursor={{ fill: '#f8fafc' }} 
                  contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)' }} 
                />
                <Bar dataKey="count" fill="url(#barGradient)" radius={[8, 8, 0, 0]} barSize={45} />
                <defs>
                  <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" />
                    <stop offset="100%" stopColor="#a855f7" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      )}

      {/* --- BOTTOM SECTION: DETAILED ISSUE FEED --- */}
      {issues.length > 0 ? (
        <div className="bg-white/70 backdrop-blur-xl rounded-[2.5rem] border border-slate-200 shadow-2xl overflow-hidden shadow-slate-200/50">
          <div className="px-10 py-8 bg-gradient-to-r from-slate-50 to-white border-b border-slate-200 flex justify-between items-center">
            <div>
              <h3 className="text-xl font-black text-slate-900 tracking-tight">Security Audit Log</h3>
              <p className="text-sm text-slate-500 font-medium mt-1">Found {issues.length} potential vulnerabilities</p>
            </div>
            <div className="flex gap-2">
               <button className="px-4 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50 transition-colors flex items-center gap-2">
                  <ExternalLink size={14} /> Export Report
               </button>
            </div>
          </div>

          <div className="divide-y divide-slate-100">
            {issues.map((issue, idx) => (
              <IssueAccordion 
                key={idx} 
                issue={issue} 
                isOpen={openIndex === idx} 
                onClick={() => setOpenIndex(openIndex === idx ? null : idx)} 
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-gradient-to-br from-emerald-50 to-teal-50 border border-emerald-100 rounded-[3rem] p-20 text-center">
          <div className="w-24 h-24 bg-white rounded-[2rem] shadow-xl shadow-emerald-200/50 flex items-center justify-center mx-auto mb-8 border border-emerald-50">
            <CheckCircle2 size={48} className="text-emerald-500" />
          </div>
          <h3 className="text-3xl font-black text-slate-900 tracking-tight">System Secure</h3>
          <p className="text-slate-500 mt-3 text-lg max-w-md mx-auto leading-relaxed">
            Our automated scanners have verified your codebase. No high-risk patterns detected.
          </p>
        </div>
      )}
    </div>
  );
}

// --- REUSABLE UI COMPONENTS ---

function StatCard({ title, value, icon, color }: any) {
  return (
    <div className="bg-white p-7 rounded-[2rem] border border-slate-100 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all group duration-300">
      <div className="flex items-center gap-5">
        <div className={`p-4 ${color} rounded-2xl transition-all duration-500 group-hover:rotate-6`}>
          {icon}
        </div>
        <div>
          <div className="text-3xl font-black text-slate-900 tracking-tighter leading-none">{value}</div>
          <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.15em] mt-2">{title}</div>
        </div>
      </div>
    </div>
  );
}

function HealthStatCard({ value }: { value: number }) {
  const color = value > 80 ? 'text-emerald-500' : value > 50 ? 'text-amber-500' : 'text-rose-500';
  return (
    <div className="bg-slate-900 p-7 rounded-[2rem] shadow-2xl hover:-translate-y-1 transition-all relative overflow-hidden group border border-slate-800">
       <div className="absolute -top-4 -right-4 p-8 opacity-10 group-hover:scale-125 group-hover:rotate-12 transition-transform duration-700">
          <Activity size={100} className="text-white" />
       </div>
       <div className="relative z-10">
          <div className={`text-3xl font-black ${color} tracking-tighter leading-none`}>{value}%</div>
          <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.15em] mt-2">Health Grade</div>
       </div>
    </div>
  );
}

function ChartCard({ title, children, className = "" }: any) {
  return (
    <div className={`bg-white p-8 rounded-[2.5rem] border border-slate-100 shadow-sm hover:shadow-lg transition-shadow duration-500 ${className}`}>
      <h3 className="text-xs font-black text-slate-400 uppercase tracking-[0.2em] mb-8">{title}</h3>
      {children}
    </div>
  );
}

function IssueAccordion({ issue, isOpen, onClick }: any) {
  const sev = issue.severity.toUpperCase();
  const severityConfig: any = {
    HIGH: { bg: "bg-rose-50", text: "text-rose-600", ring: "ring-rose-200", icon: <AlertCircle size={18} /> },
    CRITICAL: { bg: "bg-rose-50", text: "text-rose-600", ring: "ring-rose-200", icon: <AlertCircle size={18} /> },
    MEDIUM: { bg: "bg-amber-50", text: "text-amber-600", ring: "ring-amber-200", icon: <AlertCircle size={18} /> },
    LOW: { bg: "bg-sky-50", text: "text-sky-600", ring: "ring-sky-200", icon: <Info size={18} /> }
  };
  const config = severityConfig[sev] || severityConfig.LOW;

  return (
    <div className={`transition-all duration-300 ${isOpen ? 'bg-slate-50/80 shadow-inner' : 'hover:bg-slate-50/50'}`}>
      <div className="p-7 cursor-pointer flex justify-between items-center gap-6" onClick={onClick}>
        <div className="flex items-start gap-5 flex-1 min-w-0">
          <div className={`mt-1 p-2.5 rounded-xl border bg-white shadow-sm ${config.text}`}>
            {config.icon}
          </div>
          <div className="min-w-0">
            <h4 className="font-bold text-slate-900 leading-tight text-lg group-hover:text-indigo-600 transition-colors">
              {issue.message}
            </h4>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mt-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
               <span className="flex items-center gap-1.5 bg-slate-100 px-2 py-1 rounded-md text-slate-500 lowercase">
                  <FileCode size={13}/> {issue.file.split('/').pop()}
               </span>
               {issue.line && <span className="flex items-center gap-1"><Terminal size={12}/> Line {issue.line}</span>}
               <span className={`px-2.5 py-1 rounded-full ring-1 ring-inset ${config.bg} ${config.text} ${config.ring}`}>
                {issue.severity}
               </span>
               <span className="text-slate-300">|</span>
               <span className="text-indigo-400">{issue.tool}</span>
            </div>
          </div>
        </div>
        <div className={`p-2 rounded-full transition-all duration-500 ${isOpen ? 'bg-indigo-100 text-indigo-600 rotate-180' : 'bg-slate-100 text-slate-400'}`}>
          <ChevronDown size={20} />
        </div>
      </div>

      {isOpen && (
        <div className="px-8 pb-10 ml-16 space-y-8 animate-in slide-in-from-top-4 duration-500">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-rose-500 font-black text-[10px] uppercase tracking-[0.2em]">
                <ShieldAlert size={14} /> Risk Analysis
              </div>
              <p className="text-sm text-slate-600 leading-relaxed font-medium">
                {issue.risk || "Automated analysis suggests this pattern could lead to unauthorized access or execution in production environments."}
              </p>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-emerald-500 font-black text-[10px] uppercase tracking-[0.2em]">
                <CheckCircle2 size={14} /> Suggested Remediation
              </div>
              <p className="text-sm text-slate-600 leading-relaxed font-medium italic border-l-2 border-emerald-200 pl-4">
                {issue.suggestion || "Encapsulate this logic within a validated security boundary or use a modern, non-vulnerable alternative library."}
              </p>
            </div>
          </div>

          {issue.snippet && (
            <div className="space-y-3">
               <div className="flex items-center justify-between px-5 py-3 bg-slate-800 rounded-t-2xl border-b border-slate-700">
                 <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-rose-500/40" />
                    <div className="w-3 h-3 rounded-full bg-amber-500/40" />
                    <div className="w-3 h-3 rounded-full bg-emerald-500/40" />
                 </div>
                 <span className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
                    <Code2 size={14} className="text-indigo-400" /> Source Context
                 </span>
              </div>
              <pre className="bg-slate-900 p-6 rounded-b-2xl overflow-x-auto shadow-2xl border-x border-b border-slate-800 text-[13px] font-mono leading-relaxed text-indigo-100/90 custom-scrollbar">
                <code>{issue.snippet}</code>
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}