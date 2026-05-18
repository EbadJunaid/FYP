"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { sidebarPages } from "./sidebar.config";
import { Menu } from "lucide-react";

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  /* ------------------------------------------------------------
     Disable background scrolling when drawer is open
  ------------------------------------------------------------- */
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "auto";
    }
  }, [open]);


  return (
    <>
      {/* HAMBURGER BUTTON (< xl) */}
      <button
        className="xl:hidden absolute left-4 top-2 h-12 w-14 flex items-center justify-center rounded-2xl
                   bg-navButtonLight dark:bg-blue-900 shadow-md "
        onClick={() => setOpen(true)}
      >
        <Menu size={26} className="text-sidebarTextLight dark:text-sidebarTextDark" />
      </button>

      {/* BACKDROP OVERLAY (dim + closes drawer) */}
      {open && (
        <div
          onClick={() => setOpen(false)}
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-30 xl:hidden transition-opacity"
        />
      )}

      {/* DESKTOP SIDEBAR (>= xl) */}
      <aside
        className="
          hidden xl:flex flex-col bg-sidebarLight dark:bg-sidebarDark
          h-screen overflow-auto w-80 px-6 py-3 shadow-xl
        "
      >
        <h2 className="text-2xl font-bold mb-4 text-sidebarTextLight dark:text-sidebarTextDark">
          Certificate Analysis
        </h2>

        <nav className="flex flex-col gap-2">
          {sidebarPages.map((item) => (
            <Link
              key={item.label}
              href={item.route}
              className="flex items-center gap-2 px-4 py-2
                         bg-navButtonLight dark:bg-navButtonDark text-navTextLight dark:text-navTextDark
                         text-xl hover:bg-navButtonHoverLight dark:hover:bg-navButtonHoverDark
                         rounded-2xl border-2 border-navButtonBorderLight dark:border-navButtonBorderDark
                         transition"
            >
              <item.icon size={15} />
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      {/* MOBILE DRAWER (< xl) */}
      <div
        className={`
          xl:hidden fixed top-0 left-0 h-full w-64 bg-sidebarLight dark:bg-sidebarDark 
          shadow-xl z-40 transform transition-transform duration-300
          ${open ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        {/* TOP BAR: TITLE + CLOSE BUTTON */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-gray-300 dark:border-gray-700">
          <h2 className="text-xl font-bold text-sidebarTextLight dark:text-sidebarTextDark">
            Certificate Analysis
          </h2>

          <button
            onClick={() => setOpen(false)}
            className="text-sidebarTextLight dark:text-sidebarTextDark text-3xl leading-none"
          >
            ×
          </button>
        </div>

        {/* SCROLLABLE CONTENT */}
        <div className="flex flex-col gap-4 p-5 overflow-y-auto h-[calc(100%-70px)]">
          <nav className="flex flex-col gap-2">
            {sidebarPages.map((item) => (
              <Link
                key={item.label}
                href={item.route}
                onClick={() => setOpen(false)}
                className="flex items-center gap-2 px-4 py-2
                           bg-navButtonLight dark:bg-navButtonDark text-navTextLight dark:text-navTextDark
                           text-base rounded-xl border-2 border-navButtonBorderLight dark:border-navButtonBorderDark
                           hover:bg-navButtonHoverLight dark:hover:bg-navButtonHoverDark transition"
              >
                <item.icon size={15} />
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </>
  );
}

