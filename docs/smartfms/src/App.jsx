import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BatteryCharging,
  Bell,
  LayoutDashboard,
  Map,
  Search,
  Settings,
  ShieldCheck,
  Wrench
} from "lucide-react";

const navItems = [
  { label: "Overview", icon: LayoutDashboard, active: true },
  { label: "Live Map", icon: Map },
  { label: "Maintenance", icon: Wrench },
  { label: "Energy", icon: BatteryCharging },
  { label: "Utilization", icon: Activity },
  { label: "Compliance", icon: ShieldCheck },
  { label: "Settings", icon: Settings }
];

const metrics = [
  {
    label: "Fleet Health",
    value: "92%",
    delta: "+3.2% vs 7d",
    trend: "up",
    tone: "text-fms-accent-2"
  },
  {
    label: "Active Assets",
    value: "1,248",
    delta: "+18 deployed",
    trend: "up",
    tone: "text-fms-info"
  },
  {
    label: "Maintenance SLA",
    value: "96.4%",
    delta: "-0.8% backlog",
    trend: "down",
    tone: "text-fms-warn"
  },
  {
    label: "Energy Utilization",
    value: "74%",
    delta: "+4.1% efficiency",
    trend: "up",
    tone: "text-fms-accent-2"
  }
];

const alerts = [
  { tone: "bg-rose-500", title: "Critical battery", detail: "Unit T-98 • 6% SoC" },
  { tone: "bg-fms-warn", title: "Maintenance due", detail: "Lift A-12 • 3 days" },
  { tone: "bg-fms-info", title: "Geo-fence warning", detail: "Zone 4 • 2 units" }
];

const maintenanceRows = [
  { asset: "Lift A-12", issue: "Hydraulic leak", priority: "High", eta: "3 days" },
  { asset: "Fork B-07", issue: "Sensor calibration", priority: "Medium", eta: "7 days" },
  { asset: "Tow T-03", issue: "Battery swap", priority: "Low", eta: "10 days" }
];

const utilization = [
  { label: "Shift A", value: 82 },
  { label: "Shift B", value: 68 },
  { label: "Shift C", value: 74 }
];

const complianceChecks = [
  { label: "Daily inspections", status: "98%" },
  { label: "Safety training", status: "93%" },
  { label: "Regulatory audit", status: "On track" }
];

export default function App() {
  return (
    <div className="relative min-h-screen bg-fms-bg text-slate-100">
      <div className="pointer-events-none absolute inset-0 glow-orb" />
      <div className="pointer-events-none absolute inset-0 grid-overlay opacity-60" />

      <div className="relative mx-auto flex min-h-screen max-w-[1600px] flex-col lg:flex-row">
        <aside className="hidden w-[270px] flex-col gap-6 border-r border-fms-border bg-fms-panel-2 px-5 py-6 lg:flex">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-fms-accent-2" />
            <div>
              <p className="font-display text-base font-semibold">NEXUS FMS</p>
              <p className="text-xs text-slate-400">Smart fleet ops</p>
            </div>
          </div>

          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-700/40 bg-emerald-950/60 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-200">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Connected
          </div>

          <div className="text-xs font-semibold tracking-[0.2em] text-slate-500">
            Operations
          </div>

          <nav className="flex flex-col gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.label}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2 text-left text-sm transition ${
                    item.active
                      ? "border border-slate-700 bg-slate-800/70 text-slate-100"
                      : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="mt-auto rounded-2xl border border-fms-border bg-slate-900/50 p-4">
            <p className="text-xs text-slate-400">Fleet sync</p>
            <p className="mt-2 font-display text-2xl font-semibold text-slate-100">14.2 TB</p>
            <p className="text-xs text-slate-500">Telemetry streamed today</p>
          </div>
        </aside>

        <main className="flex-1 px-6 py-6 lg:px-10 lg:py-8">
          <header className="flex flex-col gap-4 border-b border-fms-border pb-6 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="font-display text-2xl font-semibold text-slate-100 md:text-3xl">
                Smart FMS Control Tower
              </h1>
              <p className="text-sm text-slate-400">
                Fleet telemetry, uptime, and compliance in real time
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-xs text-slate-400">
                <Search className="h-4 w-4" />
                Search assets
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-xs text-slate-200">
                Mar 7, 2026 • Live
              </div>
              <button className="flex items-center gap-2 rounded-xl bg-slate-800/80 px-3 py-2 text-xs">
                <Bell className="h-4 w-4" />
                <span className="rounded-full bg-fms-warn px-2 py-0.5 text-[10px] font-semibold text-slate-900">
                  5
                </span>
              </button>
            </div>
          </header>

          <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => (
              <div
                key={metric.label}
                className="rounded-2xl border border-fms-border bg-fms-panel px-4 py-4"
              >
                <p className="text-xs text-slate-400">{metric.label}</p>
                <p className="mt-2 font-display text-2xl font-semibold text-slate-100">
                  {metric.value}
                </p>
                <div className={`mt-3 flex items-center gap-2 text-xs ${metric.tone}`}>
                  {metric.trend === "up" ? (
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  ) : (
                    <ArrowDownRight className="h-3.5 w-3.5" />
                  )}
                  <span>{metric.delta}</span>
                </div>
              </div>
            ))}
          </section>

          <section className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="rounded-2xl border border-fms-border bg-fms-panel p-4">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold">Live Map</h2>
                <span className="rounded-full bg-emerald-950/60 px-3 py-1 text-xs text-emerald-300">
                  Realtime
                </span>
              </div>
              <div className="relative mt-4 h-[240px] overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
                <div className="absolute inset-0 opacity-70" style={{
                  backgroundImage:
                    "linear-gradient(rgba(40,60,80,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(40,60,80,0.35) 1px, transparent 1px)",
                  backgroundSize: "48px 48px"
                }} />
                <div className="absolute left-12 top-10 h-3 w-3 rounded-full bg-emerald-400 shadow-[0_0_16px_rgba(46,230,166,0.8)]" />
                <div className="absolute left-44 top-24 h-2.5 w-2.5 rounded-full bg-sky-400 shadow-[0_0_12px_rgba(77,184,255,0.7)]" />
                <div className="absolute left-72 top-16 h-2 w-2 rounded-full bg-amber-300 shadow-[0_0_10px_rgba(242,184,75,0.7)]" />
                <div className="absolute bottom-6 right-6 rounded-xl bg-slate-900/90 px-3 py-2 text-xs text-slate-300">
                  64 assets online
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-fms-border bg-fms-panel p-4">
              <h2 className="font-display text-lg font-semibold">Alerts</h2>
              <div className="mt-4 space-y-3">
                {alerts.map((alert) => (
                  <div
                    key={alert.title}
                    className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-3"
                  >
                    <span className={`h-2.5 w-2.5 rounded-full ${alert.tone}`} />
                    <div>
                      <p className="text-sm font-semibold text-slate-100">{alert.title}</p>
                      <p className="text-xs text-slate-400">{alert.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div className="rounded-2xl border border-fms-border bg-fms-panel p-4">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold">Maintenance Queue</h2>
                <button className="text-xs text-fms-accent">View all</button>
              </div>
              <div className="mt-4 space-y-3">
                <div className="grid grid-cols-[140px_minmax(0,1fr)_90px_90px] text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                  <span>Asset</span>
                  <span>Issue</span>
                  <span>Priority</span>
                  <span>ETA</span>
                </div>
                {maintenanceRows.map((row) => (
                  <div
                    key={row.asset}
                    className="grid grid-cols-[140px_minmax(0,1fr)_90px_90px] items-center border-b border-slate-800 py-2 text-sm"
                  >
                    <span className="text-slate-100">{row.asset}</span>
                    <span className="text-slate-300">{row.issue}</span>
                    <span
                      className={`font-semibold ${
                        row.priority === "High"
                          ? "text-fms-warn"
                          : row.priority === "Medium"
                          ? "text-fms-info"
                          : "text-emerald-300"
                      }`}
                    >
                      {row.priority}
                    </span>
                    <span className="text-slate-300">{row.eta}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-fms-border bg-fms-panel p-4">
              <h2 className="font-display text-lg font-semibold">Energy & Charging</h2>
              <div className="mt-4 space-y-4">
                <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                  <p className="text-xs text-slate-400">Stations online</p>
                  <p className="mt-2 font-display text-2xl font-semibold text-slate-100">24 / 26</p>
                  <p className="text-xs text-emerald-300">+2 restored</p>
                </div>
                <div>
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>Average SoC</span>
                    <span>68%</span>
                  </div>
                  <div className="mt-2 h-2 rounded-full bg-slate-800">
                    <div className="h-2 w-[68%] rounded-full bg-fms-accent-2" />
                  </div>
                </div>
                <div className="space-y-2 text-xs text-slate-400">
                  <div className="flex items-center justify-between">
                    <span>Fast charge utilization</span>
                    <span className="text-slate-200">82%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Swap-ready assets</span>
                    <span className="text-slate-200">112</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-fms-border bg-fms-panel p-4">
              <h2 className="font-display text-lg font-semibold">Utilization</h2>
              <div className="mt-4 space-y-3">
                {utilization.map((item) => (
                  <div key={item.label}>
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span>{item.label}</span>
                      <span className="text-slate-200">{item.value}%</span>
                    </div>
                    <div className="mt-2 h-2 rounded-full bg-slate-800">
                      <div
                        className="h-2 rounded-full bg-fms-info"
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-fms-border bg-fms-panel p-4">
              <h2 className="font-display text-lg font-semibold">Compliance</h2>
              <div className="mt-4 space-y-3">
                {complianceChecks.map((check) => (
                  <div
                    key={check.label}
                    className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2"
                  >
                    <span className="text-sm text-slate-200">{check.label}</span>
                    <span className="text-xs text-emerald-300">{check.status}</span>
                  </div>
                ))}
                <div className="rounded-xl border border-fms-border bg-slate-950/60 p-3">
                  <p className="text-xs text-slate-400">Next audit</p>
                  <p className="mt-2 font-display text-xl text-slate-100">Apr 12 • 22 days</p>
                </div>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
