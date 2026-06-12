"use client";

export function NumberInput({
  label,
  value,
  onChange,
  prefix,
  step = 1,
  min,
  hint,
}: {
  label?: string;
  value: number;
  onChange: (v: number) => void;
  prefix?: string;
  step?: number;
  min?: number;
  hint?: string;
}) {
  return (
    <div className="field">
      {label ? <label className="field-label">{label}</label> : null}
      <div style={{ position: "relative" }}>
        {prefix ? (
          <span
            style={{
              position: "absolute",
              left: 9,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--ink-3)",
              fontSize: 13,
              fontFamily: "var(--font-mono)",
              pointerEvents: "none",
            }}
          >
            {prefix}
          </span>
        ) : null}
        <input
          type="number"
          className="input num-input"
          value={Number.isFinite(value) ? value : ""}
          step={step}
          min={min}
          style={prefix ? { paddingLeft: 22 } : undefined}
          onChange={(e) => {
            const v = e.target.value === "" ? 0 : parseFloat(e.target.value);
            onChange(Number.isFinite(v) ? v : 0);
          }}
        />
      </div>
      {hint ? <div className="field-hint">{hint}</div> : null}
    </div>
  );
}
