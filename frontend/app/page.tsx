"use client";

import { useState, useRef, useEffect } from "react";

type Message = {
  role: "user" | "agent";
  text: string;
};

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const convoIdRef = useRef<string>(crypto.randomUUID());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage() {
    if (!input.trim() || loading) return;

    const userText = input;
    setMessages((prev) => [...prev, { role: "user", text: userText }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/intent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: userText,
          user_department: "support",
          user_role: "agent",
          user_id: "u123",
          convo_id: convoIdRef.current,
        }),
      });

      const data = await res.json();

      let agentText: string;
      if (data.is_safe === false) {
        agentText = data.message ?? "Blocked by guardrails.";
      } else if (data.status === "awaiting_confirmation") {
        agentText = data.question;
      } else {
        agentText = data.response ?? "No response.";
      }

      setMessages((prev) => [...prev, { role: "agent", text: agentText }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "agent", text: "Error reaching backend." }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") sendMessage();
  }

  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type a message..."
        style={{ width: "100%", padding: 10, fontSize: 16 }}
        disabled={loading}
      />

      <div style={{ marginTop: 20 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 10 }}>
            <strong>{m.role === "user" ? "You" : "Agent"}:</strong> {m.text}
          </div>
        ))}
        {loading && <div>Agent is thinking...</div>}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}