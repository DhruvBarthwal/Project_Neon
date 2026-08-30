"use client"

import React, { useState } from "react"
import { ChatMessage } from "../types/types"
import { askQuestion } from "../connection/api"

interface Props {
  period: string
}

const QAPanel = ({ period }: Props) => {
  const [convoId] = useState(() => crypto.randomUUID())
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSend() {
    const question = input.trim()
    if (!question || loading) return

    setMessages((prev) => [...prev, { role: "user", content: question }])
    setInput("")
    setLoading(true)

    try {
      const answer = await askQuestion(question, period, convoId)
      setMessages((prev) => [...prev, { role: "assistant", content: answer }])
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong reaching the agent — try again." },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-[#f5f9fc] h-full w-full flex flex-col">
      <div className="mx-8 pt-6 pb-2">
        <h1 className="font-semibold text-3xl">Ask about {period}</h1>
      </div>

      <div className="flex-1 overflow-y-auto mx-8 my-4 flex flex-col gap-3">
        {messages.length === 0 && (
          <p className="text-gray-400 text-sm">
            Try: "why didn't pay_202605_00042 settle?" or "what's our match rate?"
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-lg rounded-2xl px-4 py-2 text-sm whitespace-pre-line ${
              m.role === "user"
                ? "self-end bg-gray-900 text-white"
                : "self-start bg-white border border-gray-100"
            }`}
          >
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="self-start bg-white border border-gray-100 rounded-2xl px-4 py-2 text-sm text-gray-400">
            Thinking...
          </div>
        )}
      </div>

      <div className="mx-8 mb-6 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask a question about this period's reconciliation..."
          className="flex-1 rounded-lg border border-gray-200 px-4 py-2 text-sm bg-white"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-gray-900 text-white text-sm disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  )
}

export default QAPanel