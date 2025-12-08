import React from "react";

export default function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center py-10 ">
      <div className="animate-spin rounded-full h-32 w-32 border-t-4 border-b-4 border-blue-500"></div>
      <div className="mt-4 text-gray-500 font-bold text-xl">Loading...</div>
    </div>
  );
}