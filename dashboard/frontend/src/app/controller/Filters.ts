// utils/filters/overviewFilters.ts
import { normalizeCountry } from "./countryNormalize";

// export function makeOverviewQueryString(filters: Record<string, any>): string {
//   const processedFilters: Record<string, any> = {};

//   for (const [key, value] of Object.entries(filters)) {
//     if (key === "country" && value) {
//       processedFilters.country = normalizeCountry(value);
//       continue;
//     }

//     if (value !== undefined && value !== null && value !== "") {
//       processedFilters[key] = value;
//     }
//   }

//   const params = Object.entries(processedFilters)
//     .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
//     .join("&");

//   return params ? `?${params}` : "";
// }
export function makeQueryString(filters: Record<string, any>): string {
  const processedFilters: Record<string, any> = {};

  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "") continue;

    if (key === "country") {
      processedFilters.country = normalizeCountry(value as string);
      continue;
    }

    processedFilters[key] = value;
  }

  const params = new URLSearchParams(processedFilters as Record<string, string>);
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
