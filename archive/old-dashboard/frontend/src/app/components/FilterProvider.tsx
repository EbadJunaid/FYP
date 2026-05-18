"use client";
import React, { createContext, useContext, useState } from "react";

export interface FilterType {
  status?: string;
  issuer?: string;
  country?: string;
//   domain?: string;
  validation_level?: string;
}

interface FilterContextType {
  filters: FilterType;
  setFilters: (f: FilterType) => void;
  updateFilter: (changes: Partial<FilterType>) => void;
  resetFilters: () => void;
}

const FilterContext = createContext<FilterContextType | undefined>(undefined);

export function FilterProvider({ children }: { children: React.ReactNode }) {
  const [filters, setFiltersState] = useState<FilterType>({});

  const setFilters = (f: FilterType) => setFiltersState(f);
  const updateFilter = (changes: Partial<FilterType>) =>
    setFiltersState(prev => ({ ...prev, ...changes }));
  const resetFilters = () => setFiltersState({});

  return (
    <FilterContext.Provider value={{ filters, setFilters, updateFilter, resetFilters }}>
      {children}
    </FilterContext.Provider>
  );
}

export function useFilters() {
  const context = useContext(FilterContext);
  if (!context) throw new Error("useFilters must be used within a FilterProvider");
  return context;
}
