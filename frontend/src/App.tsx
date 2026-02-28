import { BrowserRouter as Router, Routes, Route, useLocation } from "react-router-dom";
import { useEffect } from "react";

import Navbar from "./components/layout/Navbar";
import Footer from "./components/layout/Footer";
import LandingPage from "./pages/LandingPage";
import PRInputForm from "./components/layout/PRInputForm";
import FullRepoInputForm from "./components/layout/FullRepoInputForm";
import Docs from "./pages/Docs";

function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: "instant",
    });
  }, [pathname]);

  return null;
}

function App() {
  return (
    <Router>
      <ScrollToTop />

      <div className="flex flex-col min-h-screen bg-slate-50 text-slate-900 selection:bg-indigo-100 selection:text-indigo-700 transition-colors duration-500 font-sans">
        
        <Navbar />

        <main className="flex-1">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/analyze" element={<FullRepoInputForm />} />
            <Route path="/analyze-pr" element={<PRInputForm />} />
            <Route path="/docs/*" element={<Docs />} />
            
            {/* 404 Route */}
            <Route 
              path="*" 
              element={
                <div className="flex flex-col items-center justify-center h-[70vh] space-y-6 text-center px-4">
                  <h1 className="text-8xl font-black text-slate-200 tracking-tighter select-none">404</h1>
                  <div className="space-y-2">
                    <p className="text-slate-900 text-xl font-bold tracking-tight">Page not found</p>
                    <p className="text-slate-500 max-w-xs mx-auto">The requested resource could not be located in our system.</p>
                  </div>
                  <a 
                    href="/" 
                    className="px-6 py-2 bg-white border border-slate-200 text-slate-600 rounded-full hover:bg-slate-50 transition-all shadow-sm font-medium"
                  >
                    Return Home
                  </a>
                </div>
              } 
            />
          </Routes>
        </main>

        <Footer />
      </div>
    </Router>
  );
}

export default App;