"use client";

import { useState, type ReactNode } from "react";

interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

export function TabSwitcher({ tabs, defaultTab }: { tabs: Tab[]; defaultTab?: string }) {
  const [active, setActive] = useState(defaultTab ?? tabs[0]?.id ?? "");

  return (
    <div>
      <div className="mb-8 flex gap-1 rounded-xl border border-border bg-surface p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`flex-1 rounded-lg px-4 py-2.5 font-mono text-sm uppercase tracking-wider transition ${
              active === tab.id
                ? "bg-lavender/10 text-lavender"
                : "text-dim hover:text-fg"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div>
        {tabs.map((tab) => (
          <div key={tab.id} className={active === tab.id ? "block" : "hidden"}>
            {tab.content}
          </div>
        ))}
      </div>
    </div>
  );
}
