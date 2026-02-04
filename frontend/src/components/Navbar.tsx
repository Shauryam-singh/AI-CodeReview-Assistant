import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const location = useLocation();

  // Helper to determine if a link is active
  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 h-16 flex justify-between items-center">
        
        {/* Logo - Minimalist & Bold */}
        <Link 
          to="/" 
          className="flex items-center gap-2 group transition-opacity hover:opacity-90"
        >
          <div className="w-8 h-8 bg-slate-900 rounded flex items-center justify-center text-white font-bold text-lg">
            A
          </div>
          <span className="text-xl font-bold tracking-tighter text-slate-900">
            AUDIT<span className="text-slate-400">.IO</span>
          </span>
        </Link>
        
        {/* Navigation Links */}
        <div className="flex items-center gap-1">
          <Link 
            to="/" 
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive("/") 
                ? "text-slate-900 bg-slate-100" 
                : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            Home
          </Link>

          <Link 
            to="/analyze" 
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              isActive("/analyze") 
                ? "text-slate-900 bg-slate-100" 
                : "text-slate-500 hover:text-slate-900 hover:bg-slate-50"
            }`}
          >
            Analyze Repo
          </Link>

          {/* Separator */}
          <div className="w-px h-4 bg-slate-200 mx-2" />

          <Link 
            to="/analyze-pr" 
            className="ml-2 px-5 py-2 bg-slate-900 text-white rounded-full text-sm font-semibold hover:bg-slate-800 transition-all shadow-sm active:scale-95"
          >
            Analyze PR
          </Link>
        </div>
      </div>
    </nav>
  );
}