// src/components/ThemeToggle.tsx
"use client";
import React from "react";
import { useTheme } from "./ThemeProvider";

export default function ThemeToggle() {
  const { isDark, toggle } = useTheme();

  return (
    <button
      onClick={toggle} 
      className=" bg-navButtonLight dark:bg-blue-900 text-white dark:text-gray-200 px-3 py-1 rounded-xl shadow transition"
      aria-label="Toggle Theme"
    >
      {isDark ? "🌙" : "☀️"}
    </button>
  );
}

