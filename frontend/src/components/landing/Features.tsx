interface FeatureProps {
  icon: string;
  title: string;
  desc: string;
  color: string;
  lightBg: string;
}

const FeatureCard = ({ icon, title, desc, color, lightBg }: FeatureProps) => (
  <div className="relative group p-8 rounded-3xl bg-white border border-slate-100 shadow-sm hover:shadow-xl hover:shadow-indigo-500/5 transition-all duration-500 hover:-translate-y-2">
    {/* Subtle Icon Container */}
    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl mb-6 transition-transform duration-500 group-hover:scale-110 ${lightBg} ${color}`}>
      {icon}
    </div>
    
    <div className="space-y-3">
      <h3 className="text-xl font-bold text-slate-900 tracking-tight group-hover:text-indigo-600 transition-colors">
        {title}
      </h3>
      <p className="text-slate-500 leading-relaxed text-sm">
        {desc}
      </p>
    </div>

    {/* Bottom Accent Line */}
    <div className={`absolute bottom-0 left-8 right-8 h-1 rounded-t-full transition-all duration-500 scale-x-0 group-hover:scale-x-100 bg-gradient-to-r from-transparent via-current to-transparent opacity-20 ${color}`} />
  </div>
);

export default function Features() {
  const features = [
    {
      icon: "⚡",
      title: "Smart Detection",
      desc: "Identify security vulnerabilities and logic flaws in real-time using our proprietary AI scanning engine.",
      color: "text-indigo-600",
      lightBg: "bg-indigo-50"
    },
    {
      icon: "📊",
      title: "Interactive Analytics",
      desc: "Visualize codebase health with dynamic heatmaps, dependency trees, and performance metrics.",
      color: "text-blue-600",
      lightBg: "bg-blue-50"
    },
    {
      icon: "🛡️",
      title: "Deep Isolation",
      desc: "Isolate critical issues by severity. Prioritize your workflow with AI-generated fix suggestions.",
      color: "text-slate-900",
      lightBg: "bg-slate-100"
    }
  ];

  return (
    <section className="py-24 relative overflow-hidden">
      {/* Decorative Background Element */}
      <div className="absolute top-0 right-0 -translate-y-1/2 translate-x-1/4 w-[600px] h-[600px] bg-slate-50 rounded-full blur-3xl opacity-50 pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 relative z-10">
        <div className="text-center mb-20 space-y-4">
          <span className="px-4 py-1.5 rounded-full bg-indigo-50 text-indigo-600 text-xs font-bold tracking-widest uppercase shadow-sm border border-indigo-100/50">
            Core Intelligence
          </span>
          <h2 className="text-4xl my-4 md:text-5xl font-extrabold text-slate-900 tracking-tight">
            Advanced Audit Protocols
          </h2>
          <p className="text-slate-500 max-w-2xl mx-auto font-medium">
            Everything you need to ship secure, optimized, and production-ready code without the manual overhead.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {features.map((f, i) => (
            <FeatureCard key={i} {...f} />
          ))}
        </div>
      </div>
    </section>
  );
}