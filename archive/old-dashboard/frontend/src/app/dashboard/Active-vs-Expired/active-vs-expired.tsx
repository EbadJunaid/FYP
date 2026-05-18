import PageLayout from "@/app/components/PageLayout";
import Card from "@/app/components/Card";

export default function Active_vs_expired() {
  return (
    <PageLayout
      topLeft={
        <Card title="Active Certificates" value={120}  />
      }
      topRight={
        <Card title="Expired Certificates" value={45} />
      }
      bottom={
        <Card title="bottom card" value={13}/>
      }
    />
  );
}
