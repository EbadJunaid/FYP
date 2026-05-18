"use client";

import React from "react";

interface PageLayoutProps {
  topLeft: React.ReactNode;
  topRight: React.ReactNode;
  bottom: React.ReactNode;
  classNameTop?: string;       // optional extra styles for top section
  classNameBottom?: string;    // optional extra styles for bottom section
}

export default function PageLayout({
  topLeft,
  topRight,
  bottom,
  classNameTop = "",
  classNameBottom = "",
}: PageLayoutProps) {
  return (
    <div className="w-full flex flex-col gap-6">

      {/* TOP TWO CARDS */}
      <div className={`grid grid-cols-1 md:grid-cols-2 gap-6${classNameTop}`}>
        <div className="w-full">{topLeft}</div>
        <div className="w-full">{topRight}</div>
      </div>

      {/* BOTTOM SECTION */}
      <div className={`w-full ${classNameBottom}`}>
        {bottom}
      </div>
      
    </div>
  );
}
