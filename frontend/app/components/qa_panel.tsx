"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChatMessage, PeriodStatus } from "../types/types";
import { askQuestion } from "../connection/api";

interface Props {
  period: string;
  periods?: PeriodStatus[];
  onNavigate?: (period: string, table?: string) => void;
}

const QAPanel = ({ period: defaultPeriod, periods = [], onNavigate }: Props) => {
  const [currentPeriod, setCurrentPeriod] = useState(defaultPeriod);
  const [convoId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Keep synced if parent changes initial period
  useEffect(() => {
    if (defaultPeriod && !currentPeriod) {
      setCurrentPeriod(defaultPeriod);
    }
  }, [defaultPeriod]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  async function handleSend() {
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    try {
      const answer = await askQuestion(question, currentPeriod, convoId);
      setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Unable to retrieve insights from the reconciliation engine right now. Please retry shortly.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-[#f8fafc] h-full w-full flex flex-col items-center overflow-hidden">
      {/* Top Header with Independent Period Selector */}
      <header className="w-full border-b border-slate-200/80 bg-white/90 backdrop-blur-md px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-sm font-bold text-slate-900 tracking-tight">
            Reconciliation Analyst
          </h1>
          <p className="text-[11px] text-slate-400 font-mono">
            Global Ledger Session
          </p>
        </div>

        {periods.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Target Period:</span>
            <div className="relative">
              <select
                value={currentPeriod}
                onChange={(e) => setCurrentPeriod(e.target.value)}
                className="appearance-none bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-800 text-xs font-semibold py-1.5 pl-3 pr-8 rounded-xl cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-mono transition shadow-sm"
              >
                {periods.map((p) => (
                  <option key={p.period} value={p.period}>
                    {p.period}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-500">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Main Centered Chat Container */}
      <div className="flex-1 w-full max-w-3xl overflow-y-auto px-4 py-6 flex flex-col space-y-6">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center my-auto min-h-[320px]">
            <h2 className="text-2xl font-bold text-slate-800 tracking-tight">
              Reconciliation Assistant
            </h2>
            <p className="text-sm text-slate-400 max-w-md mt-1.5 leading-relaxed">
              Ask about discrepancies, settlement delays, UTR references, or
              match variances across cycles.
            </p>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className="w-full flex flex-col animate-in fade-in duration-200">
              {m.role === "user" ? (
                <div className="self-end max-w-[80%] bg-slate-900 text-white text-sm px-4 py-2.5 rounded-2xl rounded-tr-sm shadow-sm leading-relaxed whitespace-pre-wrap font-medium">
                  {m.content}
                </div>
              ) : (
                <div className="flex gap-3.5 items-start text-slate-800 leading-relaxed text-sm py-2">
                  <div className="flex-1 overflow-x-auto text-slate-800 font-normal">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        a: ({ href, children, ...props }) => {
                          const isTableAction =
                            href?.startsWith("#view_tables") ||
                            href?.startsWith("action:view_tables");

                          if (isTableAction) {
                            const rawQuery = href ? href.split("?")[1] || "" : "";
                            const params = new URLSearchParams(rawQuery);
                            const targetPeriod = params.get("period") || currentPeriod;
                            const targetTable = params.get("table") || "exceptions";

                            return (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  if (onNavigate) {
                                    onNavigate(targetPeriod, targetTable);
                                  }
                                }}
                                className="my-2 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gray-100 hover:bg-gray-200 border border-gray-200 text-gray-700 text-xs font-semibold shadow-sm transition active:scale-95 cursor-pointer"
                              >
                                <span>{children}</span>
                                <span className="text-gray-500 font-bold"></span>
                              </button>
                            );
                          }

                          return (
                            <a
                              href={href}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-gray-600 underline"
                              {...props}
                            >
                              {children}
                            </a>
                          );
                        },

                        h1: ({ node, ...props }) => (
                          <h1 className="text-lg font-bold text-slate-900 mt-4 mb-2 pb-1 border-b border-slate-200" {...props} />
                        ),
                        h2: ({ node, ...props }) => (
                          <h2 className="text-base font-bold text-slate-900 mt-4 mb-2 flex items-center gap-1.5" {...props} />
                        ),
                        h3: ({ node, ...props }) => (
                          <h3 className="text-sm font-bold text-slate-900 mt-3 mb-1.5 uppercase tracking-wide text-gray-700" {...props} />
                        ),
                        h4: ({ node, ...props }) => (
                          <h4 className="text-xs font-bold text-slate-700 mt-2 mb-1" {...props} />
                        ),
                        p: ({ node, ...props }) => <p className="mb-2 leading-relaxed text-slate-700" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-disc list-outside pl-4 mb-2 space-y-1 text-slate-700" {...props} />,
                        ol: ({ node, ...props }) => <ol className="list-decimal list-outside pl-4 mb-2 space-y-1 text-slate-700" {...props} />,
                        li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
                        hr: ({ node, ...props }) => <hr className="my-4 border-slate-200" {...props} />,
                        code: ({ node, className, children, ...props }) => (
                          <code className="bg-slate-100 text-slate-900 font-mono text-[12px] px-1.5 py-0.5 rounded border border-slate-200/80 font-semibold" {...props}>
                            {children}
                          </code>
                        ),
                        blockquote: ({ node, ...props }) => (
                          <blockquote className="border-l-4 border-blue-500 bg-blue-50/50 p-2.5 rounded-r-xl my-2 text-xs text-slate-700 italic" {...props} />
                        ),
                        table: ({ node, ...props }) => (
                          <div className="my-3 w-full overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
                            <table className="w-full text-left border-collapse text-xs" {...props} />
                          </div>
                        ),
                        thead: ({ node, ...props }) => (
                          <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold uppercase tracking-wider" {...props} />
                        ),
                        tbody: ({ node, ...props }) => <tbody className="divide-y divide-slate-100 bg-white" {...props} />,
                        tr: ({ node, ...props }) => <tr className="hover:bg-slate-50/75 transition-colors" {...props} />,
                        th: ({ node, ...props }) => <th className="px-3.5 py-2 text-slate-700 font-bold" {...props} />,
                        td: ({ node, ...props }) => <td className="px-3.5 py-2 text-slate-600 align-top" {...props} />,
                      }}
                    >
                      {m.content}
                    </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div className="flex gap-2 items-center text-slate-500 text-sm py-2">
            <span className="text-slate-500 text-lg animate-pulse">Thinking</span>
            <span
              className="w-2 h-2 rounded-full bg-gray-400"
              style={{ animation: "qa-fade 1.4s ease-in-out infinite", animationDelay: "0s" }}
            />
            <span
              className="w-2 h-2 rounded-full bg-gray-400"
              style={{ animation: "qa-fade 1.4s ease-in-out infinite", animationDelay: "0.2s" }}
            />
            <span
              className="w-2 h-2 rounded-full bg-gray-400"
              style={{ animation: "qa-fade 1.4s ease-in-out infinite", animationDelay: "0.4s" }}
            />
            <style>{`
              @keyframes qa-fade {
                0%, 80%, 100% { opacity: 0.2; }
                40% { opacity: 1; }
              }
            `}</style>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Centered Input Bar */}
      <div className="w-full max-w-3xl px-4 pb-5 pt-2 flex-shrink-0">
        <div className="bg-white border border-slate-200 rounded-3xl shadow-sm focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-500 transition-all flex items-end px-4 py-2.5 gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={`Ask anything about ${currentPeriod} records...`}
            rows={1}
            className="flex-1 bg-transparent border-none text-sm text-slate-800 placeholder-slate-400 focus:outline-none resize-none max-h-40 overflow-y-auto leading-relaxed py-1"
            style={{
              height: "auto",
            }}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
            }}
          />

          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            aria-label="Send query"
            className="w-8 h-8 rounded-full bg-slate-900 hover:bg-slate-800 active:scale-95 disabled:bg-slate-100 disabled:text-slate-300 text-white flex items-center justify-center transition cursor-pointer flex-shrink-0"
          >
            <svg className="w-4 h-4 translate-x-[0.5px]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14m-7-7l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default QAPanel;