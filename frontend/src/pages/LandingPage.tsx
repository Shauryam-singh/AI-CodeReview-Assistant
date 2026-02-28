<<<<<<< HEAD
import Features from "../components/landing/Features";
import Steps from "../components/landing/Steps";
import CTA from "../components/landing/CTA";
import Hero from "../components/landing/Hero";

export default function LandingPage() {
  return (
    <div className="bg-white min-h-screen">
      <Hero />
      
      <section className="bg-slate-50/50 py-20 border-y border-slate-100">
        <Features />
      </section>
      
      <section className="bg-white py-20">
        <Steps />
=======
import { Link } from "react-router-dom";
import { ArrowRight, ShieldCheck, Zap, BarChart3 } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-slate-900 selection:bg-blue-100">

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-8">
        <div className="max-w-5xl mx-auto text-center">
          <span className="inline-block py-1 px-3 mb-6 text-xs font-semibold tracking-widest uppercase bg-blue-50 text-blue-600 rounded-full">
            v2.0 Now Live
          </span>
          <h1 className="text-6xl md:text-7xl font-semibold tracking-tight text-slate-950 mb-8">
            Code review, <br /> 
            <span className="text-slate-400">reimagined for scale.</span>
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto mb-12 leading-relaxed">
            Automated intelligence that surfaces security vulnerabilities and performance bottlenecks before they hit production.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/analyze"
              className="px-8 py-4 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-all shadow-lg shadow-blue-200 flex items-center gap-2"
            >
              Analyze Repository <ArrowRight size={18} />
            </Link>
            <button className="px-8 py-4 bg-white text-slate-600 font-medium border border-slate-200 rounded-xl hover:bg-slate-50 transition">
              View Documentation
            </button>
          </div>
        </div>
      </section>

      {/* Social Proof / Trusted By */}
      <div className="max-w-7xl mx-auto px-8 py-10 border-y border-slate-100 flex flex-wrap justify-center gap-12 grayscale opacity-50">
         {/* Replace with actual SVGs or text logos */}
         <span className="font-bold text-xl">GITHUB</span>
         <span className="font-bold text-xl">VERCEL</span>
         <span className="font-bold text-xl">STRIPE</span>
         <span className="font-bold text-xl">LINEAR</span>
      </div>

      {/* Features Section */}
      <section id="features" className="py-32 px-8 bg-slate-50/50">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-3 gap-12">
            <div className="space-y-4">
              <div className="w-12 h-12 bg-white shadow-sm border border-slate-100 rounded-lg flex items-center justify-center text-blue-600">
                <ShieldCheck size={24} />
              </div>
              <h3 className="text-lg font-bold">Predictive Security</h3>
              <p className="text-slate-500 leading-relaxed">Our engine identifies OWASP top-ten threats in real-time, preventing leaks before deployment.</p>
            </div>
            
            <div className="space-y-4">
              <div className="w-12 h-12 bg-white shadow-sm border border-slate-100 rounded-lg flex items-center justify-center text-blue-600">
                <BarChart3 size={24} />
              </div>
              <h3 className="text-lg font-bold">Health Metrics</h3>
              <p className="text-slate-500 leading-relaxed">Visualize technical debt through streamlined data points and file-level health scores.</p>
            </div>

            <div className="space-y-4">
              <div className="w-12 h-12 bg-white shadow-sm border border-slate-100 rounded-lg flex items-center justify-center text-blue-600">
                <Zap size={24} />
              </div>
              <h3 className="text-lg font-bold">Instant Isolation</h3>
              <p className="text-slate-500 leading-relaxed">Filter issues by severity or scope. Zero noise, just actionable improvements for your team.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Workflow Section */}
      <section id="workflow" className="py-32 px-8 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row gap-20 items-center">
          <div className="flex-1">
            <h2 className="text-4xl font-semibold tracking-tight mb-6">Built for modern <br/> engineering workflows.</h2>
            <div className="space-y-8 mt-12">
              {[
                { n: "01", t: "Connect Repository", d: "Integration via secure OAuth in seconds." },
                { n: "02", t: "Neural Scan", d: "Deep analysis across every branch and file." },
                { n: "03", t: "Actionable Insights", d: "Get a clear PDF or dashboard report." }
              ].map((step) => (
                <div key={step.n} className="flex gap-6">
                  <span className="text-blue-600 font-mono font-bold">{step.n}</span>
                  <div>
                    <h4 className="font-bold text-slate-900">{step.t}</h4>
                    <p className="text-slate-500">{step.d}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex-1 w-full bg-slate-950 aspect-video rounded-2xl shadow-2xl overflow-hidden border border-slate-800 p-4">
              {/* This represents a code preview or dashboard screenshot */}
              <div className="w-full h-full bg-slate-900 rounded-lg opacity-50 flex items-center justify-center">
                <code className="text-blue-400 text-sm">Waiting for repository link...</code>
              </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 px-8">
        <div className="max-w-4xl mx-auto bg-slate-950 rounded-3xl p-12 md:p-20 text-center text-white relative overflow-hidden">
          <div className="relative z-10">
            <h2 className="text-4xl font-bold mb-6">Ready to secure your code?</h2>
            <p className="text-slate-400 mb-10 text-lg">Join 500+ teams automating their quality assurance.</p>
            <Link to="/analyze" className="px-10 py-4 bg-white text-slate-950 font-bold rounded-full hover:bg-slate-100 transition inline-block">
              Start Free Scan
            </Link>
          </div>
          {/* Subtle background flair */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/20 blur-[100px] rounded-full" />
        </div>
>>>>>>> 0df6e60c82e66018563f77148062f66864321997
      </section>
      
      <CTA />
    </div>
  );
}