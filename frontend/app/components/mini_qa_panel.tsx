"use client"

import React, { useState } from "react"
import { askQuestion } from "../connection/api"

interface Props {
  period: string
}

const MiniQAPanel = ({ period }: Props) => {
  const [convoId] = useState(() => crypto.randomUUID())
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [lastResponse, setLastResponse] = useState<string | null>(null)

  async function handleAsk() {
    const q = input.trim()
    if (!q || loading) return

    setLoading(true)
    try {
      const answer = await askQuestion(q, period, convoId)
      setLastResponse(answer)
      setInput("")
    } catch {
      setLastResponse("Diagnostic agent unreachable.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-2xl px-3 py-10 border border-gray-100 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-bold text-xs text-gray-900">AI Recon Assistant</h3>
        <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
      </div>

      {/* Response Box (Internal Max-Height with Scroll) */}
      <div className="bg-gray-50 rounded-xl p-2 border border-gray-100 min-h-[42px] max-h-[58px] overflow-y-auto mb-2 text-[10px] text-gray-700">
        {loading ? (
          <span className="text-blue-600 animate-pulse font-medium">Diagnosing ledger discrepancy...</span>
        ) : lastResponse ? (
          lastResponse
        ) : (
          <span className="text-gray-400">Ask: "Why did pay_042 fail?" or "Summarize MDR drift"</span>
        )}
      </div>

      {/* Input Form */}
      <div className="flex items-center gap-1 bg-gray-50 border border-gray-200/80 rounded-xl p-1 pl-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="Ask AI..."
          className="bg-transparent text-[11px] w-full focus:outline-none text-gray-800 placeholder-gray-400"
        />
        <button
          onClick={handleAsk}
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