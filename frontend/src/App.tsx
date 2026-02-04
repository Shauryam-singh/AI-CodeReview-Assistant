import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage"; 
import PRInputForm from "./components/PRInputForm";
import FullRepoInputForm from "./components/FullRepoInputForm";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";

function App() {
  return (
    <Router>
      <div className="flex-col min-h-screen">
        
        <Navbar />

        {/* Routes Container */}
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/analyze" element={<FullRepoInputForm />} />
            <Route path="/analyze-pr" element={<PRInputForm />} />
          </Routes>
        </div>

        <Footer />

      </div>

    </Router>
  );
}

export default App;
