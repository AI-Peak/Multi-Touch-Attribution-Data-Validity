import type { ReactNode } from "react";

export type TableCol<T> = {
  key: keyof T & string;
  label: string;
  align?: "l" | "r";
};

export type TableRow = Record<string, ReactNode> & {
  __total?: boolean;
  __key?: string;
};

export function Table<T extends TableRow>({
  cols,
  rows,
}: {
  cols: TableCol<T>[];
  rows: T[];
}) {
  return (
    <table className="tbl">
      <thead>
        <tr>
          {cols.map((c) => (
            <th key={c.key} className={c.align === "r" ? "r" : ""}>
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, ri) => (
          <tr key={r.__key ?? ri} className={r.__total ? "row-total" : ""}>
            {cols.map((c) => (
              <td key={c.key} className={c.align === "r" ? "r" : ""}>
                {r[c.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
