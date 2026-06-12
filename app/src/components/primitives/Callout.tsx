import type { ReactNode } from "react";
import { IconWarn, IconInfo } from "@/lib/icons";

export function Callout({
  title,
  children,
  variant = "warning",
}: {
  title?: string;
  children: ReactNode;
  variant?: "warning" | "info";
}) {
  const Icon = variant === "info" ? IconInfo : IconWarn;
  return (
    <div className={"callout" + (variant === "info" ? " neutral" : "")}>
      <div className="co-icon">
        <Icon size={17} />
      </div>
      <div>
        {title ? <div className="co-title">{title}</div> : null}
        <div className="co-body">{children}</div>
      </div>
    </div>
  );
}
