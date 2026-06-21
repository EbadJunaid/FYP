import Card from "@/app/components/Card";

export const getSummaryCards = (summary: any) => {
  const baseCertsPath = "/dashboard/Overview/certificates";

  const cardData = [
    { title: "Total Certificates", value: summary.total_certificates, href: `${baseCertsPath}` },
    { title: "Active Certificates", value: summary.active_certificates, href: `${baseCertsPath}?status=active` },
    { title: "Expired Certificates", value: summary.expired_certificates, href: `${baseCertsPath}?status=expired` },
    { title: "Expiring Soon", value: summary.expiring_soon, href: `${baseCertsPath}?status=expiring_soon` },
    { title: "Unique Domains", value: summary.unique_domains_count },
    { title: "Unique Issuers", value: summary.unique_issuers_count },
    { title: "Warnings", value: summary.warnings },
    { title: "Errors", value: summary.errors },
    // { title: "Fatals", value: summary.fatals },

  ];

  return cardData.map((card, idx) => (
    <Card
      key={idx}
      title={card.title}
      value={card.value}
      className="flex flex-col items-start justify-start h-32 hover:bg-navButtonHoverLight dark:hover:bg-navButtonHoverDark"
      href={card.href}
    />
  ));
};
