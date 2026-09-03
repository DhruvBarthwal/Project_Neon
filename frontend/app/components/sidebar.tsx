"use client"

import React from "react"

export type ViewType = "dashboard" | "tables" | "qa"

interface Props {
  view: ViewType
  onSelect: (view: ViewType) => void
}

const Sidebar = ({ view, onSelect }: Props) => {
  return (
    <div className=" bg-gray-300 h-full w-1/6 border-r border-gray-100 p-4 flex flex-col justify-between">
      <div>
        <p className="font-semibold text-sm mb-4 text-gray-900">Finance Controller</p>
        <nav className="flex flex-col gap-1 text-sm text-gray-600">
          <button
            onClick={() => onSelect("dashboard")}
            className={`text-left px-2.5 py-1.5 rounded-lg transition font-medium ${
              view === "dashboard" ? "bg-gray-900 text-white" : "hover:bg-gray-50 text-gray-700"
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => onSelect("tables")}
            className={`text-left px-2.5 py-1.5 rounded-lg transition font-medium ${
              view === "tables" ? "bg-gray-900 text-white" : "hover:bg-gray-50 text-gray-700"
            }`}
          >
            Tables
          </button>
          <button
            onClick={() => onSelect("qa")}
            className={`text-left px-2.5 py-1.5 rounded-lg transition font-medium ${
              view === "qa" ? "bg-gray-900 text-white" : "hover:bg-gray-50 text-gray-700"
            }`}
          >
            Assistant
          </button>
        </nav>
      </div>
    </div>
  )
}

export default Sidebar