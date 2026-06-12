export function PageHead({
  eyebrow,
  title,
  desc,
}: {
  eyebrow?: string;
  title: string;
  desc?: string;
}) {
  return (
    <div className="page-head">
      {eyebrow ? <div className="page-eyebrow">{eyebrow}</div> : null}
      <h1 className="page-title">{title}</h1>
      {desc ? <p className="page-desc">{desc}</p> : null}
    </div>
  );
}
