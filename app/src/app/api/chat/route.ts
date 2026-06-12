import { GoogleGenAI } from "@google/genai";
import {
  SYSTEM_INSTRUCTION,
  PROJECT_CONTEXT,
} from "@/lib/ai/system-instruction";
import { offlineEvidenceAnswer } from "@/lib/ai/evidence";

export const runtime = "nodejs";

type ChatMessage = { role: "user" | "assistant"; content: string };

function textResponse(text: string) {
  return new Response(text, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}

export async function POST(req: Request) {
  const apiKey = process.env.GEMINI_API_KEY;

  let body: { messages?: ChatMessage[] };
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const messages = body.messages ?? [];
  if (!Array.isArray(messages) || messages.length === 0) {
    return Response.json({ error: "messages required" }, { status: 400 });
  }

  if (!apiKey) {
    const latest = [...messages].reverse().find((m) => m.role === "user");
    return textResponse(offlineEvidenceAnswer(latest?.content ?? ""));
  }

  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash-lite";

  const ai = new GoogleGenAI({ apiKey });

  const contents = messages.map((m) => ({
    role: m.role === "assistant" ? "model" : "user",
    parts: [{ text: m.content }],
  }));

  const systemInstruction = `${SYSTEM_INSTRUCTION}\n\nProject context:\n${PROJECT_CONTEXT}`;

  try {
    const stream = await ai.models.generateContentStream({
      model,
      contents,
      config: {
        systemInstruction,
      },
    });

    const encoder = new TextEncoder();
    const readable = new ReadableStream<Uint8Array>({
      async start(controller) {
        try {
          for await (const chunk of stream) {
            const text = chunk.text;
            if (text) controller.enqueue(encoder.encode(text));
          }
        } catch (err) {
          const msg =
            err instanceof Error ? err.message : "Unknown stream error";
          controller.enqueue(encoder.encode(`\n[error] ${msg}`));
        } finally {
          controller.close();
        }
      },
    });

    return new Response(readable, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    return Response.json(
      { error: `Gemini call failed: ${msg}` },
      { status: 500 },
    );
  }
}
