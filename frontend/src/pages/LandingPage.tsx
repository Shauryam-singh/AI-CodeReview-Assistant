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
      </section>
      
      <CTA />
    </div>
  );
}