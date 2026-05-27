export default function TeamDynamicsDashboard() {
  const teamRoles = [
    { role: "FiST Leader", x: 50, y: 50, size: 42, label: "Lead" },
    { role: "JTAC", x: 22, y: 26, size: 30, label: "JTAC" },
    { role: "FSO", x: 78, y: 28, size: 28, label: "FSO" },
    { role: "FOA", x: 24, y: 78, size: 25, label: "FOA" },
    { role: "FOM", x: 76, y: 76, size: 26, label: "FOM" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-blue-50 to-cyan-50 p-6 text-slate-800">
      <div className="mb-6 flex items-start justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">
            Team Dynamics Interpretation Dashboard
          </h1>
          <p className="mt-2 max-w-4xl text-lg text-slate-600">
            A non-expert interpretation interface that combines visual storytelling,
            plain-language explanations, and teamwork translation.
          </p>
        </div>
        <div className="rounded-2xl bg-white px-5 py-4 shadow">
          <div className="text-xs uppercase tracking-wide text-slate-500">Selected Run</div>
          <div className="text-2xl font-bold text-blue-700">R-024</div>
          <div className="text-sm text-slate-500">Scenario 3 · Fog + communication load</div>
        </div>
      </div>

      <div className="mb-6 rounded-3xl bg-white p-5 shadow">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Mission Storyboard</h2>
          <span className="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700">
            Clickable event markers in final prototype
          </span>
        </div>

        <div className="relative h-32">
          <div className="absolute left-8 right-8 top-16 h-3 rounded-full bg-gradient-to-r from-blue-200 via-amber-300 via-red-300 to-green-300" />
          {[
            ["Setup", "🛰️", "Phase 1", "left-[5%]", "bg-blue-100"],
            ["Fog Event", "⚠️", "Phase 2", "left-[34%]", "bg-amber-100"],
            ["Comm Surge", "📡", "Phase 3", "left-[63%]", "bg-red-100"],
            ["Recovery", "✅", "End", "left-[88%]", "bg-green-100"],
          ].map(([name, icon, phase, pos, bg]) => (
            <div key={name} className={`absolute top-3 -translate-x-1/2 text-center ${pos}`}>
              <div className={`mx-auto flex h-16 w-16 items-center justify-center rounded-full ${bg} text-3xl shadow-md`}>
                {icon}
              </div>
              <div className="mt-2 text-sm font-semibold">{name}</div>
              <div className="text-xs text-slate-500">{phase}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-3 space-y-6">
          <div className="rounded-3xl bg-white p-5 shadow">
            <h2 className="mb-4 text-xl font-semibold">Scenario Runs</h2>
            <div className="space-y-3">
              {["R-024 · Fog + Communication Load", "R-025 · Radio Failure", "R-026 · High Workload"].map((run, index) => (
                <div
                  key={run}
                  className={`rounded-2xl border p-4 ${index === 0 ? "border-blue-500 bg-blue-50" : "bg-white"}`}
                >
                  <div className="font-semibold">{run.split(" · ")[0]}</div>
                  <div className="text-sm text-slate-500">{run.split(" · ")[1]}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-3xl bg-white p-5 shadow">
            <h2 className="mb-4 text-xl font-semibold">Teamwork Translation</h2>
            <div className="space-y-4 text-sm">
              <div className="rounded-2xl border border-red-200 bg-red-50 p-4">
                <div className="mb-1 font-semibold">🔥 High Adaptation</div>
                <div>The team changed coordination patterns after uncertainty increased.</div>
              </div>
              <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
                <div className="mb-1 font-semibold">🔗 Stronger Interdependency</div>
                <div>Actions became more sequentially connected across roles.</div>
              </div>
              <div className="rounded-2xl border border-green-200 bg-green-50 p-4">
                <div className="mb-1 font-semibold">👥 Shared Influence</div>
                <div>Influence was spread across several team members, not just one role.</div>
              </div>
            </div>
          </div>
        </div>

        <div className="col-span-6 space-y-6">
          <div className="rounded-3xl bg-white p-6 shadow">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold">Adaptation</h2>
                <p className="text-sm text-slate-500">Entropy-based reorganization over time</p>
              </div>
              <span className="rounded-full bg-red-100 px-5 py-2 font-semibold text-red-700">High</span>
            </div>

            <div className="relative h-52 overflow-hidden rounded-3xl bg-gradient-to-r from-yellow-100 via-red-100 to-orange-100">
              <svg className="absolute inset-0 h-full w-full" viewBox="0 0 620 220" preserveAspectRatio="none">
                <path d="M0 165 C70 150 105 120 155 132 C210 148 240 170 300 155 C350 143 360 52 415 72 C482 96 500 142 620 104" fill="none" stroke="#dc2626" strokeWidth="7" strokeLinecap="round" />
                <path d="M0 184 C70 170 105 145 155 154 C210 165 240 188 300 176 C350 162 360 78 415 97 C482 122 500 166 620 130 L620 220 L0 220 Z" fill="rgba(248,113,113,.22)" />
                <line x1="390" y1="30" x2="390" y2="200" stroke="#991b1b" strokeWidth="2" strokeDasharray="7 7" />
                <circle cx="390" cy="66" r="11" fill="#991b1b" />
              </svg>
              <div className="absolute right-5 top-5 rounded-2xl bg-white/85 px-4 py-3 text-sm shadow">
                <div className="font-semibold text-red-700">Reorganization spike</div>
                <div className="text-slate-600">After fog event</div>
              </div>
            </div>

            <p className="mt-4 text-sm leading-relaxed text-slate-700">
              Plain-language reading: the team used a wider variety of coordination states after the fog event, suggesting an adaptive shift rather than routine behavior.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="rounded-3xl bg-white p-6 shadow">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold">Dynamic Interdependency</h2>
                  <p className="text-sm text-slate-500">Coordination flow</p>
                </div>
                <span className="rounded-full bg-blue-100 px-4 py-2 text-sm font-semibold text-blue-700">Moderate</span>
              </div>
              <div className="relative h-56 overflow-hidden rounded-3xl bg-gradient-to-br from-cyan-100 to-blue-200">
                <svg className="absolute inset-0 h-full w-full" viewBox="0 0 320 230">
                  <path d="M55 115 C110 60 185 60 258 105" fill="none" stroke="#2563eb" strokeWidth="7" strokeLinecap="round" />
                  <path d="M55 115 C118 165 190 170 258 105" fill="none" stroke="#60a5fa" strokeWidth="4" strokeLinecap="round" strokeDasharray="8 8" />
                  <circle cx="55" cy="115" r="24" fill="#1d4ed8" />
                  <circle cx="160" cy="72" r="24" fill="#2563eb" />
                  <circle cx="258" cy="105" r="24" fill="#3b82f6" />
                  <text x="55" y="121" textAnchor="middle" fill="white" fontSize="11">Lead</text>
                  <text x="160" y="78" textAnchor="middle" fill="white" fontSize="11">JTAC</text>
                  <text x="258" y="111" textAnchor="middle" fill="white" fontSize="11">FSO</text>
                </svg>
              </div>
              <p className="mt-4 text-sm text-slate-700">The team’s actions became more sequentially connected during the communication-heavy segment.</p>
            </div>

            <div className="rounded-3xl bg-white p-6 shadow">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold">Influence Distribution</h2>
                  <p className="text-sm text-slate-500">AMI-based role influence</p>
                </div>
                <span className="rounded-full bg-green-100 px-4 py-2 text-sm font-semibold text-green-700">Balanced</span>
              </div>
              <div className="relative h-56 overflow-hidden rounded-3xl bg-gradient-to-br from-green-100 to-emerald-200">
                <svg className="absolute inset-0 h-full w-full" viewBox="0 0 320 230">
                  {teamRoles.slice(1).map((r) => (
                    <line key={r.role} x1="160" y1="115" x2={(r.x / 100) * 320} y2={(r.y / 100) * 230} stroke="#15803d" strokeWidth="4" opacity=".75" />
                  ))}
                  {teamRoles.map((r) => (
                    <g key={r.role}>
                      <circle cx={(r.x / 100) * 320} cy={(r.y / 100) * 230} r={r.size / 2} fill="#16a34a" opacity=".92" />
                      <text x={(r.x / 100) * 320} y={(r.y / 100) * 230 + 4} textAnchor="middle" fill="white" fontSize="10" fontWeight="700">{r.label}</text>
                    </g>
                  ))}
                </svg>
              </div>
              <p className="mt-4 text-sm text-slate-700">The FiST Leader remained central, but influence was shared across supporting roles during the event.</p>
            </div>
          </div>
        </div>

        <div className="col-span-3 flex flex-col rounded-3xl bg-white p-5 shadow">
          <h2 className="mb-4 text-xl font-semibold">AI Interpretation Assistant</h2>
          <div className="flex-1 space-y-4 overflow-y-auto">
            <div className="ml-8 rounded-2xl bg-blue-100 p-3 text-sm">What does the adaptation spike mean?</div>
            <div className="mr-6 rounded-2xl bg-slate-100 p-3 text-sm leading-relaxed">
              The spike means the team shifted into more varied coordination patterns after the fog event. In plain terms, they changed how they worked together when the task became uncertain.
            </div>
            <div className="ml-8 rounded-2xl bg-blue-100 p-3 text-sm">Does that mean the team performed well?</div>
            <div className="mr-6 rounded-2xl bg-slate-100 p-3 text-sm leading-relaxed">
              Not automatically. Adaptation means the team changed. Whether that change helped depends on whether performance and teamwork ratings improved during or after the event.
            </div>
            <div className="rounded-2xl border border-yellow-300 bg-yellow-50 p-4 text-sm">
              <div className="mb-2 font-semibold">⚠ Interpretation confidence: Moderate</div>
              <div className="mb-3 text-slate-700">Some sensor channels may contain movement noise during this phase.</div>
              <div className="h-3 overflow-hidden rounded-full bg-yellow-200">
                <div className="h-full w-2/3 rounded-full bg-yellow-500" />
              </div>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <input className="flex-1 rounded-xl border p-3" placeholder="Ask about the result..." />
            <button className="rounded-xl bg-blue-600 px-4 text-white hover:bg-blue-700">Send</button>
          </div>
        </div>
      </div>
    </div>
  );
}
