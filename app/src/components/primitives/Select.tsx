"use client";

export type SelectOption =
  | string
  | {
      value: string;
      label: string;
    };

export function Select({
  label,
  value,
  options,
  onChange,
  hint,
}: {
  label?: string;
  value: string;
  options: readonly SelectOption[];
  onChange: (v: string) => void;
  hint?: string;
}) {
  return (
    <div className="field">
      {label ? <label className="field-label">{label}</label> : null}
      <select
        className="select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => {
          const v = typeof o === "string" ? o : o.value;
          const l = typeof o === "string" ? o : o.label;
          return (
            <option key={v} value={v}>
              {l}
            </option>
          );
        })}
      </select>
      {hint ? <div className="field-hint">{hint}</div> : null}
    </div>
  );
}
