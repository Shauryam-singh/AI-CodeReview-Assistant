const steps = [
  {
    id: "01",
    title: "Secure Link Input",
    desc: "Input your GitHub repository or PR URL. Our system uses end-to-end encryption to process your code architecture.",
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    border: "border-indigo-100",
  },
  {
    id: "02",
    title: "AI Threat Analysis",
    desc: "Our neural engine performs a deep, cross-layer scan, cross-referencing thousands of known vulnerabilities.",
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    border: "border-indigo-100",
  },
  {
    id: "03",
    title: "Deliverable Report",
    desc: "Receive a comprehensive dashboard within minutes. Review prioritized action items with direct code links.",
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    border: "border-indigo-100",
  },
];

export default function Steps() {
  return (
    <section className="py-32 bg-white relative overflow-hidden">
      {/* Structural Connecting Line (Desktop) */}
      <div className="hidden md:block absolute top-[62%] left-1/2 -translate-x-1/2 w-1/2 h-[2px] bg-slate-100" />

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="text-center mb-24 space-y-4">
          <h2 className="text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight">
            How it <span className="text-indigo-600">Works</span>
          </h2>
          <p className="text-slate-500 max-w-xl mx-auto font-medium leading-relaxed">
            Our automated audit pipeline is designed for speed, security, and surgical precision.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-12">
          {steps.map((step, index) => (
            <div key={index} className="relative group">
              {/* Large Muted Number Background */}
              <div className="absolute -top-16 -left-6 text-[10rem] font-black text-slate-50 select-none pointer-events-none transition-colors duration-500 group-hover:text-indigo-50/50">
                {step.id}
              </div>

              <div className="relative space-y-6 p-10 rounded-[32px] border border-slate-100 bg-white shadow-sm group-hover:shadow-xl group-hover:shadow-slate-200/50 transition-all duration-500 group-hover:-translate-y-2">
                
                {/* Step Icon/ID Indicator */}
                <div className={`w-14 h-14 rounded-2xl ${step.bg} ${step.color} flex items-center justify-center text-xl font-bold border ${step.border} shadow-sm transition-transform duration-500 group-hover:rotate-12`}>
                  {step.id}
                </div>

                <div className="space-y-3">
                  <h3 className="text-2xl font-bold text-slate-900 tracking-tight">
                    {step.title}
                  </h3>
                  <p className="text-slate-500 leading-relaxed text-sm font-medium">
                    {step.desc}
                  </p>
                </div>

                {/* Micro-interaction: Animated underline */}
                <div className="h-1 w-16 bg-slate-100 rounded-full overflow-hidden">
                  <div className={`h-full w-0 group-hover:w-full transition-all duration-700 ${step.bg.replace('bg-', 'bg-').replace('50', '600')}`} />
                </div>
              </div>

              {/* Connector Arrow - Clean Slate version */}
              {index !== steps.length - 1 && (
                <div className="hidden md:flex absolute top-[60%] -right-10 items-center justify-center z-20">
                  <div className="w-8 h-8 rounded-full bg-white border border-slate-100 flex items-center justify-center shadow-sm text-slate-300 group-hover:text-indigo-500 group-hover:border-indigo-100 transition-all">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}