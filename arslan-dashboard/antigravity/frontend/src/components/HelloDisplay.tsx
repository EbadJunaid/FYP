import { BackendResponse } from "@/models/ResponseModel";

export default function HelloDisplay({ data }: { data: BackendResponse }) {
  return (
    <div className="p-6 max-w-sm mx-auto bg-white rounded-xl shadow-lg flex items-center space-x-4 border border-blue-200">
      <div>
        <div className="text-xl font-medium text-black">Backend Status</div>
        <p className="text-slate-500">{data.message}</p>
      </div>
    </div>
  );
}