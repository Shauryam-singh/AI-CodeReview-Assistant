import { useState } from "react";
import { analyzeRepo } from "../services/api";

export default function PRInputForm() {
  const [repo, setRepo] = useState("");
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const data = await analyzeRepo(repo);
    setResult(data);
  };

  return (
    <div className="p-4">
      <form onSubmit={handleSubmit} className="space-x-2">
        <input
          type="text"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="Enter GitHub repo URL"
          className="border p-2 rounded w-80"
        />
        <button className="bg-blue-500 text-white px-4 py-2 rounded">Analyze</button>
      </form>

      {result && (
        <div className="mt-4 bg-gray-100 p-4 rounded">
          <h2 className="font-semibold">Issues:</h2>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
