import { useState } from "react";
import { Link } from "react-router-dom";

const sections = [
  { id: "introduction", title: "Introduction" },
  { id: "getting-started", title: "Getting Started" },
  { id: "audit-types", title: "Audit Modules" },
  { id: "security", title: "Security & Privacy" },
  { id: "faq", title: "FAQ" },
];

export default function Docs() {
  const [activeSection, setActiveSection] = useState("introduction");

  return (
    <div className="min-h-screen bg-white">
      {/* Sub-header for Docs navigation */}
      <div className="border-b border-slate-100 bg-slate-50/50 sticky top-[72px] z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-3">
          <div className="flex items-center text-sm text-slate-500">
            <Link to="/" className="hover:text-indigo-600 transition-colors">Home</Link>
            <span className="mx-2">/</span>
            <span className="text-slate-900 font-medium">Documentation</span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="flex flex-col md:flex-row gap-12">
          
          {/* Sidebar Navigation */}
          <aside className="md:w-64 shrink-0">
            <div className="sticky top-32 space-y-1">
              <h5 className="px-3 mb-4 text-xs font-bold uppercase tracking-widest text-slate-400">
                Documentation
              </h5>
              {sections.map((section) => (
                <a
                  key={section.id}
                  href={`#${section.id}`}
                  onClick={() => setActiveSection(section.id)}
                  className={`block px-3 py-2 text-sm font-medium rounded-lg transition-all ${
                    activeSection === section.id
                      ? "bg-indigo-50 text-indigo-700 shadow-sm shadow-indigo-100"
                      : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  {section.title}
                </a>
              ))}
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1 max-w-3xl">
            <div className="space-y-16">
              
              {/* Introduction */}
              <section id="introduction" className="scroll-mt-40 space-y-6">
                <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">
                  Introduction
                </h1>
                <p className="text-lg text-slate-600 leading-relaxed">
                  Welcome to the AI:CodeAudit documentation. Our platform leverages autonomous neural engines to identify security flaws, architectural debt, and performance bottlenecks in your codebase.
                </p>
                <div className="p-6 bg-indigo-50 border border-indigo-100 rounded-2xl">
                  <p className="text-indigo-900 text-sm font-medium leading-relaxed">
                    <strong>Note:</strong> We currently support public and private repositories for GitHub, GitLab, and Bitbucket.
                  </p>
                </div>
              </section>

              {/* Getting Started */}
              <section id="getting-started" className="scroll-mt-40 space-y-6">
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Getting Started</h2>
                <p className="text-slate-600">Follow these steps to initiate your first automated audit:</p>
                <div className="space-y-4">
                  {[
                    "Select your analysis target (Full Repo or PR).",
                    "Paste your repository URL into the secure input field.",
                    "Review the real-time telemetry as our AI pulls your AST.",
                    "Download your comprehensive PDF report or view the interactive dashboard."
                  ].map((step, i) => (
                    <div key={i} className="flex items-start gap-4">
                      <span className="flex-none w-6 h-6 rounded-full bg-slate-900 text-white text-[10px] flex items-center justify-center font-bold">
                        {i + 1}
                      </span>
                      <span className="text-slate-600 text-sm leading-relaxed">{step}</span>
                    </div>
                  ))}
                </div>
              </section>

              {/* Audit Modules */}
              <section id="audit-types" className="scroll-mt-40 space-y-6">
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Audit Modules</h2>
                
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="p-5 border border-slate-100 rounded-2xl bg-white shadow-sm">
                    <h4 className="font-bold text-slate-900 mb-2">Security Sentinel</h4>
                    <p className="text-xs text-slate-500 leading-relaxed">Scans for OWASP Top 10, SQL injection, and leaked secrets.</p>
                  </div>
                  <div className="p-5 border border-slate-100 rounded-2xl bg-white shadow-sm">
                    <h4 className="font-bold text-slate-900 mb-2">Logic Engine</h4>
                    <p className="text-xs text-slate-500 leading-relaxed">Detects race conditions, memory leaks, and redundant loops.</p>
                  </div>
                </div>
              </section>

              {/* Security */}
              <section id="security" className="scroll-mt-40 space-y-6">
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Security & Privacy</h2>
                <p className="text-slate-600 text-sm leading-relaxed">
                  We take code privacy seriously. Our architecture uses ephemeral containers that exist only for the duration of the scan.
                </p>
                <ul className="list-disc pl-5 text-sm text-slate-600 space-y-2">
                  <li>Zero persistent storage of source code.</li>
                  <li>End-to-end encrypted API requests.</li>
                  <li>SOC2 Type II compliant processing environment.</li>
                </ul>
              </section>

              {/* FAQ */}
              <section id="faq" className="scroll-mt-40 space-y-6 pb-20">
                <h2 className="text-3xl font-bold text-slate-900 tracking-tight">FAQ</h2>
                <div className="divide-y divide-slate-100">
                  <div className="py-4">
                    <h4 className="font-bold text-slate-900 text-sm">Is my code stored on your servers?</h4>
                    <p className="text-slate-500 text-xs mt-2">No. Once the audit report is generated, the code is purged from our temporary memory.</p>
                  </div>
                  <div className="py-4">
                    <h4 className="font-bold text-slate-900 text-sm">What languages are supported?</h4>
                    <p className="text-slate-500 text-xs mt-2">Currently: TypeScript, Python, Rust, Go, and Java.</p>
                  </div>
                </div>
              </section>

            </div>
          </main>
        </div>
      </div>
    </div>
  );
}