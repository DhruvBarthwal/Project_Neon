"use client";

import Sidebar from "./components/sidebar";
import Dashboard from "./components/dashboard";
import Navbar from "./components/navbar";


export default function Home() {
  return (
    <div className="flex h-screen w-full">
      <Sidebar/>
      <div className="flex flex-col h-full w-full">
        <Navbar/>
        <Dashboard/>
      </div>
    </div>
  );
}