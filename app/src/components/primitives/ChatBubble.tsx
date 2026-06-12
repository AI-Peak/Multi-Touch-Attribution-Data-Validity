import type { ReactNode } from "react";

export function ChatBubble({
  role,
  children,
}: {
  role: "user" | "assistant";
  children: ReactNode;
}) {
  return (
    <div className={"msg " + role}>
      <div className="avatar">{role === "user" ? "You" : "AI"}</div>
      <div className="bubble">{children}</div>
    </div>
  );
}
