// utils/country/countryNormalize.ts

const countryMap: Record<string, string> = {
  "pakistan": "PK",
  "india": "IN",
  "united states": "US",
  "united kingdom": "GB",
};

export function normalizeCountry(input: string): string {
  const lowered = input.trim().toLowerCase();
  return countryMap[lowered] || input;
}
