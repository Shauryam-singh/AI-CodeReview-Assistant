import { Link } from "react-router-dom";

export default function CTA() {
  return (
    <section className="py-24 relative overflow-hidden bg-white">
      {/* Soft Background Accent */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-indigo-50 rounded-full blur-[120px] pointer-events-none opacity-60" />
      
      <div className="max-w-6xl mx-auto px-6 relative">
        <div className="relative group p-12 md:p-20 rounded-[48px] bg-slate-900 overflow-hidden shadow-2xl shadow-indigo-200">
          
          {/* Subtle Abstract Background Pattern */}
          <div className="absolute inset-0 opacity-10 pointer-events-none bg-[matrix-grid-pattern] mask-image-linear-gradient" />
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/20 blur-[80px] rounded-full -mr-20 -mt-20" />
          
          <div className="relative z-10 space-y-10 text-center">
            <div className="space-y-4">
              <h2 className="text-4xl md:text-6xl font-extrabold text-white tracking-tight">
                Ready to ship <br />
                <span className="bg-gradient-to-r from-indigo-300 to-blue-200 bg-clip-text text-transparent">
                  bulletproof code?
                </span>
              </h2>
              
              <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto font-medium leading-relaxed">
                Stop guessing and start optimizing. Join thousands of developers using 
                <span className="text-white"> AI.CodeAudit </span> 
                to automate security and performance reviews.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-6 pt-4">
              <Link
                to="/analyze"
                className="group relative px-10 py-5 bg-indigo-600 text-white font-bold rounded-2xl hover:bg-indigo-500 transition-all duration-300 transform hover:-translate-y-1 hover:shadow-lg hover:shadow-indigo-500/25 text-sm uppercase tracking-wider"
              >
                Start Free Analysis
              </Link>
              
              <Link
                to="/docs"
                className="px-10 py-5 bg-white/10 text-white font-bold rounded-2xl hover:bg-white/20 backdrop-blur-sm transition-all text-sm uppercase tracking-wider border border-white/10 flex items-center gap-2"
              >
                Read Docs 
                <svg className="w-4 h-4 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </Link>
            </div>
          </div>

          {/* Clean Modern Accents instead of Brackets */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent" />
        </div>
      </div>
    </section>
  );
}