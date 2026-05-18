"use client";
import { Github, Linkedin, Mail } from "lucide-react";

export default function Footer() {
  return (
    <footer className="rounded-xl flex flex-col md:flex-row items-center justify-between px-6 py-4 bg-sidebarLight dark:bg-sidebarDark shadow-inner">
      <div className="flex flex-row gap-6 items-center">
        {/* Github */}
        <a
          href="https://github.com/yourusername/yourproject"
          target="_blank"
          rel="noopener noreferrer"
          className="group"
        >
          <div className="
            w-10 h-10 flex items-center justify-center 
            rounded-lg 
            bg-gray-200 dark:bg-gray-900 
            transition-colors duration-200
            group-hover:bg-[#171515] group-hover:dark:bg-[#3e3e3e]
          ">
            <Github 
              size={23}
              className="text-gray-700 dark:text-gray-200 group-hover:text-white"
            />
          </div>
        </a>
        {/* LinkedIn */}
        <a
          href="https://linkedin.com/in/yourlinkedin"
          target="_blank"
          rel="noopener noreferrer"
          className="group"
        >
          <div className="
            w-10 h-10 flex items-center justify-center 
            rounded-lg 
            bg-gray-200 dark:bg-gray-900 
            transition-colors duration-200
            group-hover:bg-[#0077b5] group-hover:dark:bg-[#29538b]
          ">
            <Linkedin
              size={23}
              className="text-gray-700 dark:text-gray-200 group-hover:text-white"
            />
          </div>
        </a>
        {/* Email */}
        <a
          href="mailto:your.email@example.com"
          className="group"
        >
          <div className="
            w-10 h-10 flex items-center justify-center 
            rounded-lg 
            bg-gray-200 dark:bg-gray-900 
            transition-colors duration-200
            group-hover:bg-[#ca7a06] group-hover:dark:bg-[#b47d31]
          ">
            <Mail
              size={23}
              className="text-gray-700 dark:text-gray-200 group-hover:text-white"
            />
          </div>
        </a>
      </div>
      <div className="text-sm text-navTextLight dark:text-navTextDark mt-2 md:mt-0">
        &copy; {new Date().getFullYear()} All rights reserved.
      </div>
    </footer>
  );
}
