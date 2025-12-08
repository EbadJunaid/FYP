
"use client";

import React, { useState, useEffect } from "react";
import { useFilters } from "./FilterProvider";
import { Filter, X } from "lucide-react";

export default function FilterButton() {
  const { filters, updateFilter, resetFilters } = useFilters();
  const [open, setOpen] = useState(false);

  /* ============================================================
     DISABLE BACKGROUND SCROLL WHEN FILTER POPOVER IS OPEN
  ============================================================ */
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";    // Disable scroll
    } else {
      document.body.style.overflow = "auto";      // Enable scroll back
    }
  }, [open]);

  return (
    <>

      {/* ============ DESKTOP VIEW (≥ xl) — Inline Filters ============ */}
      <div className="hidden xl:flex flex-wrap items-center gap-2">
        <select
          value={filters.status || ""}
          onChange={(e) => updateFilter({ status: e.target.value })}
          className="px-2 py-1 rounded border bg-navButtonLight dark:bg-navButtonDark 
                     text-navTextLight dark:text-navTextDark"
        >
          <option value="">Status</option>
          <option value="active">Active</option>
          <option value="expired">Expired</option>
          <option value="expiring_soon">Expiring Soon</option>
        </select>

        <input
          type="text"
          placeholder="Issuer"
          value={filters.issuer || ""}
          onChange={(e) => updateFilter({ issuer: e.target.value })}
          className="px-2 py-1 rounded border bg-navButtonLight dark:bg-navButtonDark 
                     text-navTextLight dark:text-navTextDark"
        />

        <input
          type="text"
          placeholder="Country"
          value={filters.country || ""}
          onChange={(e) => updateFilter({ country: e.target.value })}
          className="px-2 py-1 rounded border bg-navButtonLight dark:bg-navButtonDark 
                     text-navTextLight dark:text-navTextDark"
        />

        <select
          value={filters.validation_level || ""}
          onChange={(e) => updateFilter({ validation_level: e.target.value })}
          className="px-2 py-1 rounded border bg-navButtonLight dark:bg-navButtonDark 
                     text-navTextLight dark:text-navTextDark"
        >
          <option value="">Validation Level</option>
          <option value="DV">DV</option>
          <option value="OV">OV</option>
          <option value="EV">EV</option>
        </select>

        <button
          onClick={resetFilters}
          className="px-2 py-1 bg-gray-200 rounded"
        >
          Reset
        </button>
      </div>

      {/* ============ MOBILE VIEW (< xl) — Popover Button ============ */}
      <div className="xl:hidden relative">
        <button
          onClick={() => setOpen(!open)}
          className="px-3 py-1 flex items-center gap-2 rounded border 
                     bg-navButtonLight dark:bg-navButtonDark 
                     text-navTextLight dark:text-navTextDark shadow"
        >
          <Filter size={18} /> Filters
        </button>

        {/* ======= FILTER POPOVER ======= */}
        {open && (
          <>
            {/* ---- BACKGROUND OVERLAY (BLUR + DIM + CLICK TO CLOSE) ---- */}
            <div
              className="
                fixed inset-0 
                bg-black/30 
                backdrop-blur-sm 
                z-40
              "
              onClick={() => setOpen(false)}
            />

            {/* ---- POPOVER PANEL ---- */}
            <div
              className="
                absolute left-0 mt-2 z-50 w-64 
                bg-sidebarLight dark:bg-sidebarDark 
                shadow-xl rounded-xl p-4 flex flex-col gap-3
              "
            >
              {/* HEADER */}
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-bold text-sidebarTextLight dark:text-sidebarTextDark">
                  Filters
                </h3>
                <button onClick={() => setOpen(false)}>
                  <X size={22} className="text-sidebarTextLight dark:text-sidebarTextDark" />
                </button>
              </div>

              {/* FILTER FIELDS */}
              <select
                value={filters.status || ""}
                onChange={(e) => updateFilter({ status: e.target.value })}
                className="px-2 py-1 rounded border bg-navButtonLight dark:bg-navButtonDark
                           text-navTextLight dark:text-navTextDark w-full"
              >
                <option value="">Status</option>
                <option value="active">Active</option>
                <option value="expired">Expired</option>
                <option value="expiring_soon">Expiring Soon</option>
              </select>

              <input
                type="text"
                placeholder="Issuer"
                value={filters.issuer || ""}
                onChange={(e) => updateFilter({ issuer: e.target.value })}
                className="px-2 py-1 rounded border bg-navButtonLight dark:bg-navButtonDark
                           text-navTextLight dark:text-navTextDark w-full"
              />

              <input
                type="text"
                placeholder="Country"
                value={filters.country || ""}
                onChange={(e) => updateFilter({ country: e.target.value })}
                className="px-2 py-1 rounded border bg-navButtonLight dark:bg-navButtonDark
                           text-navTextLight dark:text-navTextDark w-full"
              />

              <select
                value={filters.validation_level || ""}
                onChange={(e) => updateFilter({ validation_level: e.target.value })}
                className="px-2 py-1 rounded border bg-navButtonLight dark:bg-navButtonDark
                           text-navTextLight dark:text-navTextDark w-full"
              >
                <option value="">Validation Level</option>
                <option value="DV">DV</option>
                <option value="OV">OV</option>
                <option value="EV">EV</option>
              </select>

              <button
                onClick={() => {
                  resetFilters();
                  setOpen(false);
                }}
                className="px-3 py-1 bg-gray-200 rounded w-full"
              >
                Reset
              </button>
            </div>
          </>
        )}
      </div>
    </>
  );
}
