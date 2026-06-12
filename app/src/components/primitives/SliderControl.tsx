"use client";

export function SliderControl({
  label,
  hint,
  min,
  max,
  step,
  value,
  onChange,
  fmt = (v) => String(v),
  marks,
}: {
  label: string;
  hint?: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
  fmt?: (v: number) => string;
  marks?: number[];
}) {
  const ticks = marks ?? [min, (min + max) / 2, max];
  const span = max - min;
  return (
    <div className="slider-wrap">
      <div className="slider-top">
        <div>
          <div className="field-label">{label}</div>
          {hint ? (
            <div className="field-hint" style={{ marginTop: 2 }}>
              {hint}
            </div>
          ) : null}
        </div>
        <div className="slider-val num">{fmt(value)}</div>
      </div>
      <input
        type="range"
        className="rng"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
      <div className="slider-scale">
        {ticks.map((m, i) => {
          const pct = span === 0 ? 0 : ((m - min) / span) * 100;
          const x = pct <= 0 ? "0" : pct >= 100 ? "-100%" : "-50%";

          return (
            <span key={i} style={{ left: `${pct}%`, transform: `translateX(${x})` }}>
              {fmt(m)}
            </span>
          );
        })}
      </div>
    </div>
  );
}
