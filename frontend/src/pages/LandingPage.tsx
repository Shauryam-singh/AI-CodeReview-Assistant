import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-50 overflow-x-hidden">
      
      {/* Hero Section */}
      <section className="relative h-screen flex items-center justify-center border-b border-gray-800/50">
        <div 
          className="absolute inset-0 bg-cover bg-center opacity-10" 
          style={{ backgroundImage: 'url("/assets/abstract-lines-bg.svg")' }} 
        /> 
        <div className="max-w-8xl mx-auto px-8 z-10 flex flex-col md:flex-row items-center gap-20">
          <div className="flex-1 space-y-10 text-center md:text-left">
            <h1 className="text-6xl md:text-8xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-cyan-300 to-purple-500 leading-tight animate-pulse-slow">
              AI Code Review Assistant
            </h1>
            <p className="text-xl md:text-3xl text-gray-400 font-light max-w-2xl mx-auto md:mx-0">
              Instantly analyze your GitHub repositories for **security flaws, performance issues**, and architectural debt with luminous, AI-powered insights.
            </p>
            <Link
              to="/analyze"
              className="inline-block px-12 py-5 text-xl font-extrabold rounded-full shadow-2xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 transition duration-500 transform hover:scale-105 hover:shadow-cyan-500/50 uppercase tracking-widest"
            >
              Access The Matrix
            </Link>
          </div>
          <div className="flex-1 hidden md:block">
            <img
              src="/assets/code-review-illustration.svg"
              alt="Futuristic code analysis illustration"
              className="w-full max-w-lg mx-auto drop-shadow-[0_0_20px_rgba(59,130,246,0.6)] hover:drop-shadow-[0_0_30px_rgba(168,85,247,0.8)] transition duration-500"
            />
          </div>
        </div>
      </section>

      {/* Features Section - Glassmorphism Simulation */}
      <section className="py-40 bg-gray-950">
        <div className="max-w-7xl mx-auto px-8 text-center space-y-20">
          <h2 className="text-5xl font-extrabold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-gray-50 to-gray-400">Core Intelligence Features</h2>
          <div className="grid md:grid-cols-3 gap-16">
            
            {/* Feature 1 */}
            <div 
              className="p-10 rounded-2xl shadow-2xl bg-gray-900/40 border border-blue-600/30 hover:border-blue-400 transition duration-500 transform hover:translate-y-[-10px] space-y-4"
              style={{ boxShadow: '0 0 30px rgba(59, 130, 246, 0.2)' }}
            >
              <div className="text-6xl mb-4 font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">
                //
              </div>
              <h3 className="font-bold text-3xl mb-3 text-white tracking-wider">Smart Issue Detection</h3>
              <p className="text-gray-400">Detect errors, warnings, and hidden security vulnerabilities automatically with predictive AI algorithms.</p>
            </div>

            {/* Feature 2 */}
            <div 
              className="p-10 rounded-2xl shadow-2xl bg-gray-900/40 border border-purple-600/30 hover:border-purple-400 transition duration-500 transform hover:translate-y-[-10px] space-y-4"
              style={{ boxShadow: '0 0 30px rgba(168, 85, 247, 0.2)' }}
            >
              <div className="text-6xl mb-4 font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-500">
                &#x2211;
              </div>
              <h3 className="font-bold text-3xl mb-3 text-white tracking-wider">Interactive Data Streams</h3>
              <p className="text-gray-400">Visualize complex data using real-time pie charts, file-wise bar charts, and a dynamic repo health matrix.</p>
            </div>

            {/* Feature 3 */}
            <div 
              className="p-10 rounded-2xl shadow-2xl bg-gray-900/40 border border-cyan-600/30 hover:border-cyan-400 transition duration-500 transform hover:translate-y-[-10px] space-y-4"
              style={{ boxShadow: '0 0 30px rgba(6, 182, 212, 0.2)' }}
            >
              <div className="text-6xl mb-4 font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-cyan-500">
                {">"}
              </div>
              <h3 className="font-bold text-3xl mb-3 text-white tracking-wider">Deep Search & Isolation</h3>
              <p className="text-gray-400">Isolate critical issues by filtering on severity, language, or file path to prioritize your fixing workflow.</p>
            </div>
          </div>
        </div>
      </section>
      
      {/* Divider / Spacer */}
      <div className="max-w-6xl mx-auto border-t border-blue-800/50 my-20" />

      {/* How It Works Section */}
      <section className="py-40 bg-gray-950">
        <div className="max-w-7xl mx-auto px-8 text-center space-y-20">
          <h2 className="text-5xl font-extrabold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-gray-50 to-gray-400">Execution Protocol</h2>
          <div className="grid md:grid-cols-3 gap-16">
            
            {/* Step 1 */}
            <div className="space-y-6 p-8 rounded-lg transition duration-500 transform hover:scale-[1.05]">
              <div className="text-8xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-cyan-500 leading-none">
                01
              </div>
              <h3 className="font-semibold text-2xl text-white tracking-wide">Secure Link Input</h3>
              <p className="text-gray-500 max-w-xs mx-auto">Input your GitHub repository URL for secure, encrypted processing.</p>
            </div>

            {/* Step 2 */}
            <div className="space-y-6 p-8 rounded-lg transition duration-500 transform hover:scale-[1.05]">
              <div className="text-8xl font-black text-transparent bg-clip-text bg-gradient-to-r from-cyan-500 to-green-500 leading-none">
                02
              </div>
              <h3 className="font-semibold text-2xl text-white tracking-wide">AI Threat Analysis</h3>
              <p className="text-gray-500 max-w-xs mx-auto">The AI engine performs a deep, cross-layer scan to identify all potential issues.</p>
            </div>

            {/* Step 3 */}
            <div className="space-y-6 p-8 rounded-lg transition duration-500 transform hover:scale-[1.05]">
              <div className="text-8xl font-black text-transparent bg-clip-text bg-gradient-to-r from-green-500 to-purple-500 leading-none">
                03
              </div>
              <h3 className="font-semibold text-2xl text-white tracking-wide">Deliverable Report</h3>
              <p className="text-gray-500 max-w-xs mx-auto">Receive a comprehensive, interactive dashboard with prioritized action items.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action Section - Elevated Card */}
      <section className="py-40 bg-gray-950">
        <div className="max-w-5xl mx-auto px-8">
          <div 
            className="p-16 rounded-3xl text-center shadow-2xl border border-purple-600/50 bg-gray-900/60 transition duration-700 hover:shadow-purple-500/30"
            style={{ boxShadow: '0 0 40px rgba(168, 85, 247, 0.4)' }}
          >
            <h2 className="text-4xl md:text-5xl font-black mb-6 tracking-tight text-white">Engage The Code Matrix</h2>
            <p className="text-xl text-gray-400 mb-10 max-w-3xl mx-auto">Stop guessing and start optimizing. Leverage **AI-powered intelligence** to secure and perfect your codebase instantly.</p>
            <Link
              to="/analyze"
              className="inline-block px-14 py-5 text-xl font-extrabold rounded-full shadow-2xl bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700 transition duration-500 transform hover:scale-105 hover:shadow-pink-500/50 uppercase tracking-widest"
            >
              Start Scan
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}