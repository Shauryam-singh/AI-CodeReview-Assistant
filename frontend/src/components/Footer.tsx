import { Link } from "react-router-dom";
import { Github, Twitter, Linkedin, Mail } from "lucide-react";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-slate-200 pt-20 pb-12">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-12 gap-12 mb-16">
          
          {/* Brand Column */}
          <div className="col-span-2 md:col-span-4 space-y-6">
            <div className="flex items-center gap-2 font-bold text-lg tracking-tight text-slate-900">
              <div className="w-8 h-8 bg-slate-900 rounded flex items-center justify-center text-white text-sm">
                A
              </div>
              <span>AUDIT<span className="text-slate-400">.IO</span></span>
            </div>
            <p className="text-slate-500 text-sm leading-relaxed max-w-xs">
              Next-generation code analysis powered by adaptive AI. Built for teams that prioritize security and performance.
            </p>
            <div className="flex gap-4 text-slate-400">
              <a href="#" className="hover:text-slate-900 transition-colors"><Github size={20} /></a>
              <a href="#" className="hover:text-slate-900 transition-colors"><Twitter size={20} /></a>
              <a href="#" className="hover:text-slate-900 transition-colors"><Linkedin size={20} /></a>
              <a href="#" className="hover:text-slate-900 transition-colors"><Mail size={20} /></a>
            </div>
          </div>

          {/* Links Columns */}
          <div className="col-span-1 md:col-span-2 md:col-start-7 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-widest text-slate-900">Product</h4>
            <ul className="space-y-3 text-sm text-slate-500">
              <li><Link to="/analyze" className="hover:text-indigo-600 transition-colors">Analyze Repo</Link></li>
              <li><Link to="/analyze-pr" className="hover:text-indigo-600 transition-colors">PR Review</Link></li>
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Integrations</a></li>
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Pricing</a></li>
            </ul>
          </div>

          <div className="col-span-1 md:col-span-2 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-widest text-slate-900">Resources</h4>
            <ul className="space-y-3 text-sm text-slate-500">
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Documentation</a></li>
              <li><a href="#" className="hover:text-indigo-600 transition-colors">API Reference</a></li>
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Changelog</a></li>
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Security</a></li>
            </ul>
          </div>

          <div className="col-span-1 md:col-span-2 space-y-4">
            <h4 className="text-xs font-bold uppercase tracking-widest text-slate-900">Legal</h4>
            <ul className="space-y-3 text-sm text-slate-500">
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Terms of Service</a></li>
              <li><a href="#" className="hover:text-indigo-600 transition-colors">Cookie Policy</a></li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-slate-100 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-xs text-slate-400">
            © {currentYear} AUDIT.IO Inc. All rights reserved.
          </p>
          <div className="flex items-center gap-6 text-xs font-medium text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              All Systems Operational
            </span>
            <span className="text-slate-200">|</span>
            <span>Based in India</span>
          </div>
        </div>
      </div>
    </footer>
  );
}