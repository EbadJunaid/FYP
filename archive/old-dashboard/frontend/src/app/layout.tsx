
import "./globals.css";
import Sidebar from "@/app/components/Sidebar";
import Header from "@/app/components/Header";
import Footer from "./components/Footer";
import { ThemeProvider } from "@/app/components/ThemeProvider";
import { FilterProvider } from "@/app/components/FilterProvider";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-bgLight dark:bg-bgDark">
        <ThemeProvider>
          <FilterProvider>

          {/* <div className="relative flex min-h-screen w-full"> */}
            <div className="relative flex h-screen w-full">

            {/* Sidebar (desktop and mobile drawer handled inside component) */}
            <Sidebar />

            {/* Main content */}
            <div className="flex-1 flex flex-col h-screen px-2 gap-2">

              {/* Header */}
              <Header />

              {/* Main body */}
              <main className="flex-1 w-full p-2 overflow-y-auto">

                {children}
              </main>

              <Footer />
            </div>
          </div>
          </FilterProvider>

        </ThemeProvider>
      </body>
    </html>
  );
}



// function ThemeInitScript() {
//   return (
//     <script
//       dangerouslySetInnerHTML={{
//         __html: `
//           (function() {
//             try {
//               var theme = localStorage.getItem('theme');
//               if (theme === 'dark') {
//                 document.documentElement.classList.add('dark');
//               } else {
//                 document.documentElement.classList.remove('dark');
//               }
//             } catch (e) {}
//           })();
//         `,
//       }}
//     />
//   );
// }
