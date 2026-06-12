"use client";

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: readonly string[];
  active: number;
  onChange: (i: number) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t, i) => (
        <button
          key={t}
          role="tab"
          aria-selected={active === i}
          className={"tab" + (active === i ? " active" : "")}
          onClick={() => onChange(i)}
        >
          {t}
        </button>
      ))}
    </div>
  );
}
