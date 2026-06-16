export function csvRow(values: readonly (number | string)[]) {
  return values
    .map((value) => {
      const text = String(value);
      return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
    })
    .join(",");
}
