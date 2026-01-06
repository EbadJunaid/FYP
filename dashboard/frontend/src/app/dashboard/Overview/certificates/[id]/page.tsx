"use client";

import { useEffect, useState } from "react";
import LoadingSpinner from "@/app/components/LoadingSpinner";

export default function CertificateDetailsPage() {
  const [cert, setCert] = useState<any>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem("selectedCertificate");
    if (stored) {
      setCert(JSON.parse(stored));
    }
  }, []);

  if (!cert) return <LoadingSpinner />;

  const safe = (v: any) => v ?? "N/A";

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-semibold">Certificate Details</h1>

      {/* BASIC INFO */}
      <Section title="Basic Information">
        <Detail label="Domain" value={safe(cert.domain)} />
        <Detail label="Status" value={safe(cert.status)} />
        <Detail label="Algorithm" value={safe(cert.algorithm)} />
        <Detail label="Country" value={safe(cert.country)} />
        <Detail label="Valid From" value={safe(cert.validity?.valid_from)} />
        <Detail label="Valid To" value={safe(cert.validity?.valid_to)} />
      </Section>

      {/* ISSUER */}
      <Section title="Issuer Information">
        <Detail label="Organization" value={safe(cert.issuer?.organization)} />
        <Detail label="Common Name" value={safe(cert.issuer?.common_name)} />
        <Detail label="Country" value={safe(cert.issuer?.country)} />
        <Detail label="State" value={safe(cert.issuer?.state)} />
        <Detail label="Locality" value={safe(cert.issuer?.locality)} />
        <Detail label="Org Unit" value={safe(cert.issuer?.organizational_unit)} />
      </Section>

      {/* PUBLIC KEY */}
      <Section title="Public Key">
        <Detail label="Type" value={safe(cert.public_key?.type)} />
        <Detail label="Bits" value={safe(cert.public_key?.bits)} />
        <Detail
          label="Fingerprint (SHA256)"
          value={safe(cert.public_key?.fingerprint_sha256)}
        />
      </Section>

      {/* WARNINGS */}
      <Section title={`Warnings (${cert.warnings?.count ?? 0})`}>
        {cert.warnings?.details?.length ? (
          cert.warnings.details.map((w: any, i: number) => (
            <div key={i} className="p-3 rounded bg-yellow-100 text-black">
              {w.lint_name}
            </div>
          ))
        ) : (
          <div>N/A</div>
        )}
      </Section>

      {/* ERRORS */}
      <Section title={`Errors (${cert.errors?.count ?? 0})`}>
        {cert.errors?.details?.length ? (
          cert.errors.details.map((e: any, i: number) => (
            <div key={i} className="p-3 rounded bg-red-100 text-black">
              {e.lint_name}
            </div>
          ))
        ) : (
          <div>N/A</div>
        )}
      </Section>
    </div>
  );
}

/* ---------- Helpers ---------- */

function Detail({ label, value }: { label: string; value: any }) {
  return (
    <div>
      <p className="text-sm opacity-70">{label}</p>
      <p className="text-lg font-medium">{value}</p>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-sidebarLight dark:bg-sidebarDark p-6 rounded-xl shadow space-y-3">
      <h2 className="text-xl font-semibold">{title}</h2>
      {children}
    </div>
  );
}
