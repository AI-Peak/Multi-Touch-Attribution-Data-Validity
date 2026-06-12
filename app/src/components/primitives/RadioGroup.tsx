"use client";

export type RadioOption<T extends string> = {
  value: T;
  label: string;
  sub?: string;
};

export function RadioGroup<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: ReadonlyArray<RadioOption<T>>;
  onChange: (v: T) => void;
}) {
  return (
    <div className="radio-group">
      {options.map((o) => (
        <div
          key={o.value}
          role="radio"
          aria-checked={value === o.value}
          tabIndex={0}
          className={"radio" + (value === o.value ? " sel" : "")}
          onClick={() => onChange(o.value)}
          onKeyDown={(e) => {
            if (e.key === " " || e.key === "Enter") {
              e.preventDefault();
              onChange(o.value);
            }
          }}
        >
          <span className="dot" />
          <div className="r-text">
            <div className="r-label">{o.label}</div>
            {o.sub ? <div className="r-sub">{o.sub}</div> : null}
          </div>
        </div>
      ))}
    </div>
  );
}
