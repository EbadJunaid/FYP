"use client";
import Link from "next/link";

interface CardProps {
  title: string;
  value: React.ReactNode;
  className?: string;
  href?: string; // Optional route
}

export default function Card({ title, value, className = "", href }: CardProps) {
  const handleClick = () => {
    if (href === undefined) return; // do nothing
    if (!href) alert("🚧 Feature in progress...");
  };

  const Wrapper = href ? Link : "div";

  return (
    <Wrapper
      href={href || "#"}
      onClick={href ? undefined : handleClick}
      className={`block p-5  text-lg 
        rounded-xl shadow-xl font-semibold
        bg-sidebarLight dark:bg-sidebarDark
        text-navTextLight dark:text-navTextDark
        transition 
        cursor-pointer select-none ${className}`}
    >
      <span className="text-xl font-bold mb-1">{title}</span>
      <span className="text-4xl font-bold">{value}</span>
    </Wrapper>
  );
}
