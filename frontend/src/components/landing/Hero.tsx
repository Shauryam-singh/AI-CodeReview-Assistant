import { Link } from "react-router-dom";

export default function Hero() {
  return (
    <section className="relative min-h-[90vh] flex items-center justify-center pt-20 overflow-hidden bg-white">
      {/* Soft Background Orbs - Much subtler for light mode */}
      <div className="absolute top-[10%] -left-[5%] w-[400px] h-[400px] bg-indigo-100/50 rounded-full blur-[100px]" />
      <div className="absolute bottom-[10%] -right-[5%] w-[500px] h-[500px] bg-blue-50/80 rounded-full blur-[120px]" />

      <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-2 gap-16 items-center relative z-10">
        <div className="space-y-8 text-center md:text-left">
          
          {/* Badge - Replaced Cyan with Indigo/Slate */}
          <div className="inline-flex items-center space-x-3 px-3 py-1.5 rounded-full border border-slate-200 bg-slate-50 text-slate-600 text-[11px] font-bold tracking-wider uppercase shadow-sm">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-600"></span>
            </span>
            <span>AI-Powered Security Engine v1.1</span>
          </div>

          <h1 className="text-6xl md:text-7xl font-extrabold leading-[1.1] tracking-tight text-slate-900">
            Audit Your <br />
            <span className="bg-gradient-to-r from-indigo-600 via-blue-600 to-indigo-500 bg-clip-text text-transparent">
              Code Intelligence.
            </span>
          </h1>

          <p className="text-slate-500 text-lg md:text-xl max-w-xl leading-relaxed font-normal">
            Instantly detect security flaws, performance debt, and architectural 
            vulnerabilities with our autonomous AI auditor. Built for modern engineering teams.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center md:justify-start">
            <Link
              to="/analyze"
              className="px-8 py-4 bg-slate-900 text-white font-semibold rounded-2xl hover:bg-indigo-600 hover:shadow-xl hover:shadow-indigo-200 transition-all duration-300 transform hover:-translate-y-1 text-center text-sm"
            >
              Start Analysis Free
            </Link>
            <Link
              to="/docs"
              className="px-8 py-4 border border-slate-200 bg-white rounded-2xl hover:bg-slate-50 transition-all text-slate-600 font-semibold text-sm shadow-sm"
            >
              View Documentation
            </Link>
          </div>
          
          {/* Trust Marker */}
          <p className="text-slate-400 text-xs font-medium pt-2 italic">
            Trusted by 500+ developers worldwide
          </p>
        </div>

        {/* Hero Visual Component - "The Glass Terminal" */}
        <div className="relative hidden md:block group">
          <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500/10 to-blue-500/10 rounded-[40px] blur-2xl group-hover:blur-3xl transition-all duration-700" />
          
          <div className="relative bg-white border border-slate-200 rounded-[32px] p-3 shadow-[0_20px_50px_rgba(0,0,0,0.05)] overflow-hidden">
            {/* Terminal Mockup Header - macOS Style */}
            <div className="flex items-center space-x-2 px-4 py-3 bg-slate-50/50 border-b border-slate-100 rounded-t-[20px]">
              <div className="w-2.5 h-2.5 rounded-full bg-slate-300" />
              <div className="w-2.5 h-2.5 rounded-full bg-slate-300" />
              <div className="w-2.5 h-2.5 rounded-full bg-slate-300" />
              <div className="flex-1 text-center">
                <span className="text-[10px] font-mono text-slate-400 tracking-widest uppercase">main.py — Analysis</span>
              </div>
            </div>
            
            {/* The "Code" Content */}
            <div className="relative group-hover:scale-[1.02] transition-transform duration-700">
              <img 
                src="https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&q=80&w=1000" 
                alt="Code Interface" 
                className="rounded-xl mt-2 opacity-90 saturate-[0.8]"
              />
              {/* Floating Overlay Card */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white/90 backdrop-blur-md p-6 rounded-2xl shadow-2xl border border-indigo-100 w-64">
                <div className="flex items-center space-x-3 mb-3">
                    <div className="h-8 w-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold">AI</div>
                    <div className="text-xs font-bold text-slate-800">Review Complete</div>
                </div>
                <div className="space-y-2">
                    <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full w-4/5 bg-indigo-500" />
                    </div>
                    <div className="flex justify-between text-[10px] font-bold text-slate-500">
                        <span>Security Score</span>
                        <span className="text-indigo-600">92%</span>
                    </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}