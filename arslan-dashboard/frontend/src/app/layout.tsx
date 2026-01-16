import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/context/ThemeContext";
import SWRProvider from "@/providers/SWRProvider";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SSL Guardian - Certificate Monitoring Dashboard",
  description: "Monitor and analyze SSL certificates for security vulnerabilities",
  keywords: ["SSL", "TLS", "certificate", "security", "monitoring"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} antialiased bg-background text-foreground`}>
        <SWRProvider>
          <ThemeProvider defaultTheme="dark">
            {children}
          </ThemeProvider>
        </SWRProvider>
      </body>
    </html>
  );
}
