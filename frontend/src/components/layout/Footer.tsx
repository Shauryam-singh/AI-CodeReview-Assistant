import { Link } from "react-router-dom";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-slate-100 border-t border-slate-200 pt-16 pb-12">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
          
          {/* Brand Column */}
          <div className="col-span-1 md:col-span-1 space-y-5">
            <Link to="/" className="text-xl font-bold tracking-tight text-slate-900">
              AI<span className="text-indigo-600">.CodeAudit</span>
            </Link>
            <p className="text-slate-500 text-sm leading-relaxed max-w-xs">
              Elevating code quality through autonomous intelligence. Secure your future, one commit at a time.
            </p>
          </div>

          {/* Navigation */}
          <div>
            <h4 className="text-slate-900 font-bold mb-5 text-xs uppercase tracking-widest">Platform</h4>
            <ul className="space-y-3 text-sm text-slate-500">
              <li><Link to="/analyze" className="hover:text-indigo-600 transition-colors">Analyze Repo</Link></li>
              <li><Link to="/analyze-pr" className="hover:text-indigo-600 transition-colors">Analyze PR</Link></li>
              <li><Link to="/docs" className="hover:text-indigo-600 transition-colors">Documentation</Link></li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-slate-900 font-bold mb-5 text-xs uppercase tracking-widest">Legal</h4>
            <ul className="space-y-3 text-sm text-slate-500">
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Terms of Service</a></li>
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Security Protocol</a></li>
            </ul>
          </div>

          {/* Social Icons */}
          <div>
            <h4 className="text-slate-900 font-bold mb-5 text-xs uppercase tracking-widest">Connect</h4>
            <div className="flex space-x-3">
              <a href="#" className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-600 transition-all text-slate-400">
                 <span className="text-[10px] font-bold">GH</span>
              </a>
              <a href="#" className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-600 transition-all text-slate-400">
                 <span className="text-[10px] font-bold">TW</span>
              </a>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-slate-200 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center space-x-2">
            <span className="h-px w-8 bg-slate-300"></span>
            <p className="text-slate-400 text-[10px] tracking-[0.2em] uppercase">
              Designed by <span className="text-slate-900 font-bold">SHAURYAM</span>
            </p>
          </div>
          <p className="text-slate-400 text-xs font-medium">
            © {currentYear} AI Code Review. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}