"use client"

import React, { useState, useRef, useEffect } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { askQuestion } from "../connection/api"

interface Props {
  period: string
}

interface Turn {
  question: string
  answer: string
}

const SUGGESTIONS = ["Why did pay_042 fail?", "Summarize MDR drift", "Which exceptions are highest risk?"]

const MiniQAPanel = ({ period }: Props) => {
  const [convoId] = useState(() => crypto.randomUUID())
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [turns, setTurns] = useState<Turn[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [turns, loading])

  async function handleAsk(question?: string) {
    const q = (question ?? input).trim()
    if (!q || loading) return

    setLoading(true)
    setInput("")
    try {
      const answer = await askQuestion(q, period, convoId)
      setTurns((prev) => [...prev, { question: q, answer }])
    } catch {
      setTurns((prev) => [...prev, { question: q, answer: "Couldn't reach the assistant. Try again." }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl px-3 py-2.5 border border-gray-100 shadow-sm flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-bold text-xs text-gray-900">Ask about this period</h3>
        {loading && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />}
      </div>

      {/* Conversation history */}
      <div
        ref={scrollRef}
        className="bg-gray-50 rounded-xl p-2 border border-gray-100 max-h-[180px] overflow-y-auto mb-2 space-y-2"
      >
        {turns.length === 0 && !loading ? (
          <div className="flex flex-wrap gap-1">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => handleAsk(s)}
                className="text-[9px] text-gray-600 bg-white border border-gray-200 rounded-full px-2 py-1 hover:border-gray-300 hover:bg-gray-50 transition"
              >
                {s}
              </button>
            ))}
          </div>
        ) : (
          <>
            {turns.map((t, i) => (
              <div key={i} className="space-y-0.5">
                <p className="text-[10px] font-medium text-gray-800">{t.question}</p>
                <div className="text-[10px] text-gray-500 leading-relaxed qa-markdown overflow-x-auto">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
                      table: ({ children }) => (
                        <table className="border-collapse text-[9px] my-1 w-full">{children}</table>
                      ),
                      th: ({ children }) => (
                        <th className="border border-gray-200 bg-white px-1.5 py-0.5 text-left font-semibold text-gray-700">
                          {children}
                        </th>
                      ),
                      td: ({ children }) => (
                        <td className="border border-gray-200 px-1.5 py-0.5">{children}</td>
                      ),
                      ul: ({ children }) => <ul className="list-disc pl-3 mb-1 space-y-0.5">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal pl-3 mb-1 space-y-0.5">{children}</ol>,
                      code: ({ children }) => (
                        <code className="bg-white border border-gray-200 rounded px-1 text-[9px] font-mono">
                          {children}
                        </code>
                      ),
                      strong: ({ children }) => <strong className="font-semibold text-gray-700">{children}</strong>,
                    }}
                  >
                    {t.answer}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
            {loading && (
              <p className="text-[10px] text-blue-600 font-medium">Looking into it...</p>
            )}
          </>
        )}
      </div>

      {/* Input Form */}
      <div className="flex items-center gap-1 bg-gray-50 border border-gray-200/80 rounded-xl p-1 pl-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="Ask a question..."
          className="bg-transparent text-[11px] w-full focus:outline-none text-gray-800 placeholder-gray-400"
        />
        <button
          onClick={() => handleAsk()}
          disabled={loading || !input.trim()}
          className="p-1 bg-gray-900 text-white rounded-lg hover:bg-blue-600 transition disabled:opacity-40"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 10l7-7m0 0l7 7m-7-7v18" />
          </svg>
        </button>
      </div>
    </div>
  )
}

export default MiniQAPanel