import React from "react"

const Sidebar = () => {
  return (
    <div className="h-full w-1/6 border-r border-gray-100 p-4">
      <p className="font-semibold text-sm mb-4">Finance controller</p>
      <nav className="flex flex-col gap-1 text-sm text-gray-600">
        <span className="px-2 py-1.5 rounded-lg bg-gray-100 text-gray-900">Dashboard</span>
        <span className="px-2 py-1.5 rounded-lg text-gray-300">Q&amp;A (coming soon)</span>
      </nav>
    </div>
  )
}

export default Sidebar