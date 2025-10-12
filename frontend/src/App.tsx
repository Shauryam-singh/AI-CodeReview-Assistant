import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import LandingPage from "./pages/LandingPage"; 
import PRInputForm from "./components/PRInputForm";
import FullRepoInputForm from "./components/FullRepoInputForm";

function App() {
  return (
    <Router>
      <div className="flex flex-col min-h-screen bg-gray-950">
        
        {/* Navbar */}
        <nav className="bg-gray-950 border-b border-purple-700/50 text-white shadow-2xl shadow-purple-900/10 sticky top-0 z-50">
          <div className="max-w-8xl mx-auto px-8 py-3 flex justify-between items-center">
            {/* Logo */}
            <Link to="/" className="text-3xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-600 transition duration-300 hover:opacity-80">
              //AI:CodeAudit
            </Link>
            
            {/* Navigation Links */}
            <div className="space-x-8 font-semibold text-lg">
              <Link 
                to="/" 
                className="text-gray-300 transition duration-200 relative group"
              >
                Home
                <span className="absolute left-0 bottom-[-5px] w-0 h-0.5 bg-cyan-400 group-hover:w-full transition-all duration-300" />
              </Link>
              
              <Link 
                to="/analyze" 
                className="text-gray-300 transition duration-200 relative group"
              >
                Analyze Repo
                <span className="absolute left-0 bottom-[-5px] w-0 h-0.5 bg-cyan-400 group-hover:w-full transition-all duration-300" />
              </Link>

              <Link 
                to="/analyze-pr" 
                className="text-gray-300 transition duration-200 relative group"
              >
                Analyze PR
                <span className="absolute left-0 bottom-[-5px] w-0 h-0.5 bg-cyan-400 group-hover:w-full transition-all duration-300" />
              </Link>
            </div>
          </div>
        </nav>

        {/* Routes Container */}
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/analyze" element={<FullRepoInputForm />} />
            <Route path="/analyze-pr" element={<PRInputForm />} />
          </Routes>
        </div>

        {/* Footer */}
        <footer className="bg-gray-950 border-t border-blue-700/50 text-gray-500 py-6 text-center mt-auto text-sm tracking-widest">
          <p>
            MADE BY: SHAURYAM | © {new Date().getFullYear()} AI Code Review Assistant.
          </p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
