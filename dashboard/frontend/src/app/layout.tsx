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
  const themeScript = `
    (function () {
      try {
        var theme = localStorage.getItem('ssl-guardian-theme');
        if (theme !== 'light' && theme !== 'dark') theme = 'dark';
        document.documentElement.classList.remove('light', 'dark');
        document.documentElement.classList.add(theme);
      } catch (error) {
        document.documentElement.classList.add('dark');
      }
    })();
  `;

  return (
    <html lang="en" className="dark" data-scroll-behavior="smooth" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
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
