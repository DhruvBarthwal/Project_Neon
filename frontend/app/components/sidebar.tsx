import React from "react"

interface Props {
  view: "dashboard" | "qa"
  onSelect: (view: "dashboard" | "qa") => void
}

const Sidebar = ({ view, onSelect }: Props) => {
  return (
    <div className="h-full w-1/6 border-r border-gray-100 p-4">
      <p className="font-semibold text-sm mb-4">Finance controller</p>
      <nav className="flex flex-col gap-1 text-sm text-gray-600">
        <button
          onClick={() => onSelect("dashboard")}
          className={`text-left px-2 py-1.5 rounded-lg ${view === "dashboard" ? "bg-gray-100 text-gray-900" : ""}`}
        >
          Dashboard
        </button>
        <button
          onClick={() => onSelect("qa")}
          className={`text-left px-2 py-1.5 rounded-lg ${view === "qa" ? "bg-gray-100 text-gray-900" : ""}`}
        >
          Q&amp;A
        </button>
      </nav>
    </div>
  )
}

export default Sidebar