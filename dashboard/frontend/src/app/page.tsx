// src/app/page.tsx

// app/page.tsx
import { redirect } from "next/navigation";

export default function HomePage() {
  // <h1>hello</h1>
  redirect("/dashboard/Overview");
}
