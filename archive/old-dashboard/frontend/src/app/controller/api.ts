// const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// function normalizeCountry(val: string) {
  //   return val;
  // }
import { makeQueryString } from "./Filters";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export async function fetchOverview(filters: Record<string, any> = {}) {
  // const queryString = makeOverviewQueryString(filters);
  const queryString = makeQueryString(filters);
  // const url = `${API_BASE}/overview/data/${qs}`;
  console.log(queryString)
  const url = `${BASE_URL}/overview/data${queryString}`;

  console.log("Fetching overview from:", url);

  try {
    const res = await fetch(url, { cache: "no-store" });

    if (!res.ok) {
      const body = await res.text();
      console.error("API error:", res.status, body);
      throw new Error(`API error: ${res.status}`);
    }

    return await res.json();
  } catch (error) {
    console.error("Overview fetch failed:", error);
    throw error;
  }
}



export async function fetchCertificates(page = 1, pageSize = 20, filters: Record<string, any> = {}) {
  const baseFilters = { ...filters, page, page_size: pageSize };
  const queryString = makeQueryString(baseFilters);
  
  const url = `${BASE_URL}/overview/certificates${queryString}`;
  console.log("Fetching overview from:", url);

  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) {
      const body = await res.text();
      console.error("Certificates API error:", res.status, body);
      throw new Error(`API error: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error("Certificates fetch failed:", err);
    throw err;
  }
}