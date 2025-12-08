import { fetchOverview, fetchCertificates } from "@/app/controller/api";

export async function getOverviewData(filters = {}) {
  try {
    const data = await fetchOverview(filters);
    return data;
  } catch {
    return null;
  }
}

export async function getCertificatesData(page = 1, pageSize = 20, filters = {}) {
  try {
    const data = await fetchCertificates(page, pageSize, filters);
    return data;
  } catch {
    return null;
  }
}
