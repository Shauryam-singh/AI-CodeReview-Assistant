import { Link, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";

export default function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { name: "Home", path: "/" },
    { name: "Analyze Repo", path: "/analyze" },
    { name: "Analyze PR", path: "/analyze-pr" },
  ];

  return (
    <nav 
      className={`sticky top-0 z-[100] transition-all duration-500 ${
        isScrolled 
          ? "bg-white/70 backdrop-blur-md py-3 border-b border-slate-200/60 shadow-sm" 
          : "bg-white/0 py-6 border-b border-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 flex justify-between items-center">
        
        {/* Logo Area */}
        <Link 
          to="/" 
          className="group flex items-center space-x-1.5 text-xl font-bold tracking-tight"
        >
          <span className="text-slate-900 group-hover:text-indigo-600 transition-colors duration-300">
            AI.
          </span>
          <span className="text-indigo-600 font-extrabold">
            CodeAudit
          </span>
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden md:flex items-center bg-slate-100/50 p-1 rounded-xl border border-slate-200/50">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className={`relative px-5 py-2 text-sm font-medium transition-all duration-200 rounded-lg ${
                  isActive 
                    ? "bg-white text-indigo-600 shadow-sm ring-1 ring-slate-200" 
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                {link.name}
              </Link>
            );
          })}
        </div>

        {/* Action Button */}
        <div className="flex items-center space-x-4">
          <Link
            to="/analyze"
            className="hidden sm:inline-flex items-center justify-center px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-full hover:bg-indigo-600 hover:shadow-lg hover:shadow-indigo-200 transition-all duration-300 active:scale-95"
          >
            Launch Scan
          </Link>
          
          {/* Mobile Menu Toggle */}
          <button className="md:hidden text-slate-600 p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

      </div>
    </nav>
  );
}