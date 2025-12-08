// src/components/Header.tsx
"use client";
import { usePathname } from "next/navigation";
import {sidebarPages} from "./sidebar.config"
import ThemeToggle from "./ThemeToggle";
import FilterButton from "./FilterButton";

export default function Header() {
  const pathname =usePathname();
  // If your URLs have dynamic segments, add logic to format more gracefully.
  const currentpage=sidebarPages.find(page=> page.route===pathname)
  const pageName = currentpage ? currentpage.label : "";

  return (
    <header className="w-full rounded-xl flex items-center justify-between px-6 py-4 bg-sidebarLight dark:bg-sidebarDark shadow-md">
      <h1 className="text-2xl font-bold text-navTextLight dark:text-navTextDark">
        {/* {pageName} */}
      </h1> 
      <FilterButton/>
      <ThemeToggle />
    </header>
  );
}
