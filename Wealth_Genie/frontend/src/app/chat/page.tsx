"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { ChatMessage, ChatRequest, ChatResponse } from "@/lib/api/types";

interface FailedRequest {
  message: string;
  conversationHistory: ChatMessage[];
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isWaiting, setIsWaiting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [failedRequest, setFailedRequest] = useState<FailedRequest | null>(null);

  const sendMessage = async (
    message: string,
    conversationHistory: ChatMessage[],
    appendUserMessage: boolean
  ) => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || isWaiting) return;

    const userMessage: ChatMessage = { role: "user", content: trimmedMessage };

    if (appendUserMessage) {
      setMessages((currentMessages) => [...currentMessages, userMessage]);
      setDraft("");
    }

    setErrorMessage(null);
    setFailedRequest(null);
    setIsWaiting(true);

    try {
      const request: ChatRequest = {
        message: trimmedMessage,
        conversation_history: conversationHistory,
      };
      const response = await apiFetch<ChatResponse>("/chat", {
        method: "POST",
        body: request,
      });
      setMessages((currentMessages) => [
        ...currentMessages,
        { role: "assistant", content: response.reply },
      ]);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.push("/login");
        return;
      }

      setErrorMessage(error instanceof Error ? error.message : "Could not send message.");
      setFailedRequest({ message: trimmedMessage, conversationHistory });
    } finally {
      setIsWaiting(false);
    }
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void sendMessage(draft, messages, true);
  };

  const retryLastMessage = () => {
    if (!failedRequest) return;
    void sendMessage(failedRequest.message, failedRequest.conversationHistory, false);
  };

  return (
    <div className="relative min-h-screen bg-[#030712] text-gray-100 flex flex-col overflow-hidden">
      <div className="glow-blur-green top-[10%] left-[5%]" />
      <div className="glow-blur-indigo bottom-[20%] right-[10%]" />

      <header className="relative z-10 w-full max-w-5xl mx-auto px-6 py-6 border-b border-white/5">
        <Link href="/dashboard" className="flex items-center gap-2 w-fit">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg">
            W
          </div>
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            Wealth Genie
          </span>
        </Link>
      </header>

      <main className="relative z-10 flex-1 w-full max-w-5xl mx-auto px-6 py-8 flex flex-col min-h-0">
        <div className="mb-6">
          <Link href="/dashboard" className="text-sm text-gray-400 hover:text-white transition-colors">
            ← Back to Dashboard
          </Link>
          <h1 className="mt-3 text-3xl font-extrabold text-white tracking-tight">AI Financial Coach</h1>
          <p className="mt-1 text-gray-400">Ask questions about your persisted financial profile and report.</p>
        </div>

        <section className="glass-panel flex-1 min-h-[420px] rounded-3xl p-5 md:p-7 flex flex-col">
          <div className="flex-1 overflow-y-auto space-y-4 pr-1">
            {messages.length === 0 ? (
              <div className="h-full min-h-[280px] flex flex-col items-center justify-center text-center">
                <h2 className="text-xl font-bold text-white">Start a conversation</h2>
                <p className="mt-2 text-sm text-gray-400 max-w-md">
                  Ask about spending, debt, savings, or your AI CFO recommendations.
                </p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                    message.role === "user"
                      ? "ml-auto bg-emerald-500 text-white"
                      : "bg-white/5 border border-white/10 text-gray-200"
                  }`}
                >
                  <p className="mb-1 text-xs font-semibold opacity-70">
                    {message.role === "user" ? "You" : "AI Financial Coach"}
                  </p>
                  {message.content}
                </div>
              ))
            )}

            {isWaiting && (
              <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-white/5 border border-white/10 text-sm text-gray-400">
                AI Financial Coach is thinking...
              </div>
            )}
          </div>

          {errorMessage && (
            <div className="mt-5 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
              <span>{errorMessage}</span>
              {failedRequest && (
                <button
                  type="button"
                  onClick={retryLastMessage}
                  disabled={isWaiting}
                  className="px-4 py-2 rounded-lg border border-red-400/30 hover:bg-red-500/10 disabled:opacity-50 transition-colors"
                >
                  Retry
                </button>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-5 flex gap-3">
            <label htmlFor="chat-message" className="sr-only">Message</label>
            <textarea
              id="chat-message"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask a financial question..."
              disabled={isWaiting}
              rows={2}
              className="flex-1 resize-none rounded-xl bg-white/5 border border-white/10 px-4 py-3 text-sm text-white placeholder:text-gray-500 outline-none focus:border-emerald-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isWaiting || !draft.trim()}
              className="self-end px-5 py-3 bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-500/40 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors"
            >
              Send
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
