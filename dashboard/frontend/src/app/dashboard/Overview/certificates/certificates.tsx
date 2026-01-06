  "use client";

  import { useEffect, useState } from "react";
  import { useSearchParams, useRouter } from "next/navigation";
  import { getCertificatesData } from "@/app/controller/dataFetcher";
  import LoadingSpinner from "@/app/components/LoadingSpinner";
  import Card from "@/app/components/Card";
  import { useFilters } from "@/app/components/FilterProvider";

  export default function CertificatesPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const { filters } = useFilters();

    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [selectedCert, setSelectedCert] = useState<any>(null);

    const page = parseInt(searchParams.get("page") || "1", 10);
    const page_size = 20;

    // Accept filters passed from URL (ex: ?status=active)
    const statusFromUrl = searchParams.get("status") || undefined;

    useEffect(() => {
      let mounted = true;
      setLoading(true);

      const fetchData = async () => {
        const activeFilters: any = { ...filters };
        if (statusFromUrl) activeFilters.status = statusFromUrl;

        const res = await getCertificatesData(page, page_size, activeFilters);
        // console.log("i am in useeffect")
        if (!mounted) return;

        setData(res);

        if (res?.results?.length > 0) {
          setSelectedCert(res.results[0]);
        }

        setLoading(false);

      };

      fetchData();

      return () => {
        mounted = false;
      };
    }, [page, page_size, statusFromUrl, filters]);

    if (loading) return <LoadingSpinner />;
    if (!data) return <div className="p-6">No data available</div>;

    const handlePageChange = (newPage: number) => {
      const params = new URLSearchParams(searchParams.toString());
      params.set("page", newPage.toString());
      router.push(`/dashboard/Overview/certificates?${params.toString()}`);
    };

    return (


        <div className="-mt-2 flex flex-col bg-yellow-400">
          <div className="bg-red-400 ">
              <table className="w-full">
                <thead className="text-left bg-navButtonHoverLight dark:bg-navButtonHoverDark font-semibold">
                  <tr>
                    {/* <th >Domain</th>
                    <th >Issuer</th>
                    <th >Status</th>
                    <th >Valid Upto</th>
                    <th >Algorithm</th>
                    <th >Warnings</th>
                    <th >Errors</th> */}
                    <th className="p-4">Domain</th>
                    <th className="p-4">Issuer</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Valid Upto</th>
                    <th className="p-4">Algorithm</th>
                    <th className="p-4">Warnings</th>
                    <th className="p-4">Errors</th>
                  </tr>
                </thead>
                <tbody className="bg-pink-400">
                    {data.results.map((cert: any, idx: number) => (
                    <tr
                      key={idx}
                      onClick={() => {
                        sessionStorage.setItem(
                          "selectedCertificate",
                          JSON.stringify(cert)
                        );
                        router.push(`/dashboard/Overview/certificates/${cert.id}`);
                      }}
                      className="cursor-pointer text-navTextLight dark:text-navTextDark hover:bg-navButtonHoverLight dark:hover:bg-navButtonHoverDark transition"
                    >
                      <td className="p-4">{cert.domain}</td>
                      <td className="p-4">
                        {cert.issuer.organization || cert.issuer.common_name}
                      </td>
                      <td className="p-4 capitalize">{cert.status}</td>
                      <td className="p-4">{cert.validity.valid_to}</td>
                      <td className="p-4">{cert.algorithm}</td>
                      <td className="p-4">{cert.warnings.count}</td>
                      <td className="p-4">{cert.errors.count}</td>

                    </tr>
                  ))}
                </tbody>
              </table>
          </div>
          
          <div className="mt-6 flex justify-between bg-green-400">
               <button
                  disabled={page === 1}
                  onClick={() => handlePageChange(page - 1)}
                  className="px-4 py-2 rounded bg-gray-700 text-white disabled:opacity-30"
                >
                  Previous
                </button>

                <button
                  disabled={page >= data.total_pages}
                  onClick={() => handlePageChange(page + 1)}
                  className="px-4 py-2 rounded bg-gray-700 text-white disabled:opacity-30"
                >
                  Next
                </button>
          </div>
        </div>

      // <div className="flex flex-col p-2">
      //   {/* <h1 className="text-3xl font-bold mb-6">Certificates</h1> */}

      //   {/* -------- TOP CARD (Showing selected certificate) -------- */}
      //   {/* {selectedCert && (
      //     <Card
      //       title={`Certificate Details`}
      //       value={
      //         <div className="flex flex-col md:flex-row align-items justify-between p-4 gap-4 text-lg">
      //           <div>
      //           <p><strong>Domain:</strong> {selectedCert.domain ||selectedCert.id }</p>

      //           <p><strong>Issuer:</strong> {selectedCert.issuer.organization || selectedCert.issuer.common_name}</p>
      //           <p><strong>Status:</strong> {selectedCert.status}</p>
      //           <p><strong>Valid From:</strong> {selectedCert.validity.valid_from}</p>
      //           </div>
      //           <div>

      //           <p><strong>Valid Upto:</strong> {selectedCert.validity.valid_to}</p>
      //           <p><strong>Algorithm:</strong> {selectedCert.algorithm}</p>
      //           <p><strong>Country:</strong> {selectedCert.country || "N/A"}</p>
      //           <p><strong>Key Bits:</strong> {selectedCert.public_key.bits || "N/A"}</p>
      //           </div>
      //         </div>
      //       }
      //       className="mb-6 w-full"
      //     />
      //   )} */}

      //   {/* -------- TABLE -------- */}
      //   <div className="bg-red-400 rounded-xl shadow-lg bg-sidebarLight dark:bg-sidebarDark w-full">
      //     <table className="min-w-full text-left text-lg">
      //       <thead className="sticky top-2 z-10 bg-navButtonHoverLight dark:bg-navButtonHoverDark font-semibold">
      //         <tr>
      //           <th className="p-4">Domain</th>
      //           <th className="p-4">Issuer</th>
      //           <th className="p-4">Status</th>
      //           <th className="p-4">Valid Upto</th>
      //           <th className="p-4">Algorithm</th>
      //           <th className="p-4">Warnings</th>
      //           <th className="p-4">Errors</th>

      //         </tr>
      //       </thead>

      //       <tbody>
      //         {data.results.map((cert: any, idx: number) => (
      //           <tr
      //             key={idx}
      //             onClick={() => {
      //               sessionStorage.setItem(
      //                 "selectedCertificate",
      //                 JSON.stringify(cert)
      //               );
      //               router.push(`/dashboard/Overview/certificates/${cert.id}`);
      //             }}
      //             className="cursor-pointer text-navTextLight dark:text-navTextDark hover:bg-navButtonHoverLight dark:hover:bg-navButtonHoverDark transition"
      //           >
      //             <td className="p-4">{cert.domain}</td>
      //             <td className="p-4">
      //               {cert.issuer.organization || cert.issuer.common_name}
      //             </td>
      //             <td className="p-4 capitalize">{cert.status}</td>
      //             <td className="p-4">{cert.validity.valid_to}</td>
      //             <td className="p-4">{cert.algorithm}</td>
      //             <td className="p-4">{cert.warnings.count}</td>
      //             <td className="p-4">{cert.errors.count}</td>

      //           </tr>
      //         ))}
      //       </tbody>
      //     </table>
      //   </div>

      //   {/* -------- PAGINATION -------- */}
      //   <div className="mt-6 flex justify-between">
      //     <button
      //       disabled={page === 1}
      //       onClick={() => handlePageChange(page - 1)}
      //       className="px-4 py-2 rounded bg-gray-700 text-white disabled:opacity-30"
      //     >
      //       Previous
      //     </button>

      //     <button
      //       disabled={page >= data.total_pages}
      //       onClick={() => handlePageChange(page + 1)}
      //       className="px-4 py-2 rounded bg-gray-700 text-white disabled:opacity-30"
      //     >
      //       Next
      //     </button>
      //   </div>
      // </div>

    );
  }

