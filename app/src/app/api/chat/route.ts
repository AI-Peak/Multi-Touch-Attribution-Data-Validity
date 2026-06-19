import { GoogleGenAI } from "@google/genai";
import {
  SYSTEM_INSTRUCTION,
  PROJECT_CONTEXT,
} from "@/lib/ai/system-instruction";
import { ANSWER_EXAMPLES, ANSWER_POLICY } from "@/lib/ai/answer-policy";
import {
  hasSpecificOfflineEvidenceAnswer,
  offlineEvidenceAnswer,
  shouldReplyInVietnamese,
  shouldUseLocalEvidenceAnswer,
} from "@/lib/ai/evidence";

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

function isRateLimitError(message: string) {
  return /\b429\b|too many requests|rate limit/i.test(message);
}

function rateLimitResponse(language: "English" | "Vietnamese") {
  return language === "Vietnamese"
    ? [
        "MTA Assistant đang vượt giới hạn gọi Gemini tạm thời, nên mình chưa thể trả lời câu này bằng model.",
        "Câu hỏi này không có fallback local đủ chính xác. Bạn vui lòng thử lại sau ít phút, hoặc hỏi một câu nằm trong evidence của project như RQ1, RQ2, RQ3, safe recommendation, hoặc budget diagnostic.",
      ].join("\n\n")
    : [
        "MTA Assistant is temporarily over the Gemini rate limit, so I cannot answer this question with the model right now.",
        "This question does not have a precise local fallback. Please try again in a few minutes, or ask something grounded in the project evidence such as RQ1, RQ2, RQ3, safe recommendations, or budget diagnostics.",
      ].join("\n\n");
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

  const latest = [...messages].reverse().find((m) => m.role === "user");
  const replyLanguage = shouldReplyInVietnamese(latest?.content ?? "")
    ? "Vietnamese"
    : "English";

  if (shouldUseLocalEvidenceAnswer(latest?.content ?? "")) {
    return textResponse(offlineEvidenceAnswer(latest?.content ?? ""));
  }

  if (!apiKey) {
    return textResponse(offlineEvidenceAnswer(latest?.content ?? ""));
  }

  const model = process.env.GEMINI_MODEL || "gemini-2.5-flash-lite";

  const ai = new GoogleGenAI({ apiKey });

  const contents = messages.map((m) => ({
    role: m.role === "assistant" ? "model" : "user",
    parts: [{ text: m.content }],
  }));

  const systemInstruction = `${SYSTEM_INSTRUCTION}\n\nResponse language for this answer: ${replyLanguage}. This language rule is mandatory.\n\nAnswer policy:\n${ANSWER_POLICY}\n\nExample answers:\n${ANSWER_EXAMPLES}\n\nProject context:\n${PROJECT_CONTEXT}`;
  const streamErrorMessage =
    replyLanguage === "Vietnamese"
      ? "\n\nMTA Assistant gặp lỗi khi nhận đủ phản hồi từ model. Vui lòng thử lại câu hỏi này."
      : "\n\nMTA Assistant had trouble receiving the full model response. Please try this question again.";

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
          const msg = err instanceof Error ? err.message : String(err);
          console.error("Gemini stream error", err);
          if (isRateLimitError(msg)) {
            const question = latest?.content ?? "";
            const fallback = hasSpecificOfflineEvidenceAnswer(question)
              ? `\n\n${offlineEvidenceAnswer(question)}`
              : `\n\n${rateLimitResponse(replyLanguage)}`;
            controller.enqueue(encoder.encode(fallback));
          } else {
            controller.enqueue(encoder.encode(streamErrorMessage));
          }
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
    if (isRateLimitError(msg)) {
      const question = latest?.content ?? "";
      if (hasSpecificOfflineEvidenceAnswer(question)) {
        console.warn("Gemini rate limit; using specific offline evidence fallback", err);
        return textResponse(offlineEvidenceAnswer(question));
      }

      console.warn("Gemini rate limit; no specific offline fallback available", err);
      return textResponse(rateLimitResponse(replyLanguage));
    }

    return Response.json(
      { error: `Gemini call failed: ${msg}` },
      { status: 500 },
    );
  }
}
