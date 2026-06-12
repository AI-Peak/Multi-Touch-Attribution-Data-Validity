"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { PageHead } from "@/components/primitives/PageHead";
import { ChatBubble } from "@/components/primitives/ChatBubble";
import { PromptChip } from "@/components/primitives/PromptChip";
import { IconInfo, IconSend } from "@/lib/icons";
import { VN_PROMPTS } from "@/lib/ai/system-instruction";
import { citationsForText } from "@/lib/ai/evidence";

type Message = { role: "user" | "assistant"; content: string };

const GREETING: Message = {
  role: "assistant",
  content:
    "Hello — I'm the project research assistant. I answer strictly from this study's precomputed evidence about the MTA dataset's validity.\n\nAsk about the three research questions, the 83.63% label issue, or how to present the findings.",
};

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, thinking]);

  async function send(text?: string) {
    const q = (text ?? draft).trim();
    if (!q || thinking) return;
    setError(null);

    const userMsg: Message = { role: "user", content: q };
    const history = [...messages, userMsg];
    setMessages(history);
    setDraft("");
    setThinking(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: history.filter((m) => m !== GREETING || messages.length === 1),
        }),
      });

      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as
          | { error?: string }
          | null;
        setError(body?.error ?? `Request failed: ${res.status}`);
        setThinking(false);
        return;
      }

      if (!res.body) {
        setError("No response body");
        setThinking(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      const assistantMsg: Message = { role: "assistant", content: "" };
      setMessages((m) => [...m, assistantMsg]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const decoded = decoder.decode(value, { stream: true });
        setMessages((m) => {
          const copy = [...m];
          const lastIdx = copy.length - 1;
          const last = copy[lastIdx];
          if (last) copy[lastIdx] = { ...last, content: last.content + decoded };
          return copy;
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setThinking(false);
    }
  }

  return (
    <div
      className="page"
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        paddingBottom: 18,
      }}
    >
      <PageHead
        eyebrow="AI Research Assistant"
        title="Ask the evidence"
        desc="A grounded assistant for interrogating the validity findings. It does not browse the web or invent numbers."
      />

      <div className="chat-notice">
        <IconInfo size={15} />
        <span>
          Powered by Gemini when configured; otherwise uses an offline evidence
          fallback. Citation chips link back to project pages.
        </span>
      </div>

      <div className="chat-wrap" style={{ flex: 1, minHeight: 0 }}>
        <div className="chat-scroll scroll-area" ref={scrollRef}>
          {messages.map((m, i) => (
            <ChatBubble key={i} role={m.role}>
              {m.content.split("\n\n").map((para, pi) => (
                <p key={pi}>{para}</p>
              ))}
              {m.role === "assistant" ? (
                <div className="citation-row">
                  {citationsForText(m.content).map((citation) => (
                    <Link
                      className="citation-chip"
                      href={citation.href}
                      key={citation.id}
                      title={citation.note}
                    >
                      {citation.label}
                    </Link>
                  ))}
                </div>
              ) : null}
            </ChatBubble>
          ))}
          {thinking ? (
            <ChatBubble role="assistant">
              <span style={{ color: "var(--ink-3)", fontStyle: "italic" }}>
                Retrieving from evidence…
              </span>
            </ChatBubble>
          ) : null}
          {error ? (
            <div
              style={{
                padding: "10px 13px",
                background: "var(--amber-tint)",
                border: "1px solid var(--amber-line)",
                borderLeft: "3px solid var(--amber)",
                borderRadius: 6,
                color: "var(--amber-700)",
                fontSize: 12,
              }}
            >
              {error}
            </div>
          ) : null}
        </div>

        <div style={{ paddingTop: 14 }}>
          <div className="prompt-chips">
            {VN_PROMPTS.map((p) => (
              <PromptChip key={p} onClick={() => send(p)}>
                {p}
              </PromptChip>
            ))}
          </div>
          <div className="chat-input-bar">
            <textarea
              rows={1}
              placeholder="Ask about the dataset's validity…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <button
              className="send-btn"
              disabled={!draft.trim() || thinking}
              onClick={() => send()}
              type="button"
              aria-label="Send"
            >
              <IconSend size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
