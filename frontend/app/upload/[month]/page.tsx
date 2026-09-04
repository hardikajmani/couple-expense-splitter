"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { getSetup, uploadStatement, MonthSetup } from "../../lib/api";

type UploadResult = {
  fileName: string;
  status: "success" | "error";
  message: string;
};

function UploadArea({ month, person }: { month: string; person: string }) {
  const [results, setResults] = useState<UploadResult[]>([]);
  const [uploading, setUploading] = useState(false);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    const newResults: UploadResult[] = [];
    for (const file of Array.from(files)) {
      try {
        const res = await uploadStatement(month, person, file);
        newResults.push({
          fileName: file.name,
          status: "success",
          message: `Detected ${res.accountType} account (${res.accountName}) — ${res.transactionCount} transactions`,
        });
      } catch (err) {
        newResults.push({
          fileName: file.name,
          status: "error",
          message: err instanceof Error ? err.message : "Upload failed",
        });
      }
    }
    setResults((prev) => [...newResults, ...prev]);
    setUploading(false);
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950">
      <h2 className="text-lg font-semibold text-black dark:text-zinc-50">{person}</h2>
      <label className="flex cursor-pointer flex-col items-center justify-center gap-1 rounded-md border-2 border-dashed border-zinc-300 px-4 py-8 text-center text-sm text-zinc-600 hover:border-zinc-400 dark:border-zinc-700 dark:text-zinc-400">
        <span>Drop or select CSV statement(s) — credit, chequing, savings</span>
        <input
          type="file"
          accept=".csv"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </label>
      {uploading && <p className="text-sm text-zinc-500">Uploading…</p>}
      {results.length > 0 && (
        <ul className="flex flex-col gap-1 text-sm">
          {results.map((r, i) => (
            <li key={i} className={r.status === "success" ? "text-green-700" : "text-red-600"}>
              <strong>{r.fileName}:</strong> {r.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function UploadPage({ params }: { params: Promise<{ month: string }> }) {
  const { month } = use(params);
  const [setup, setSetup] = useState<MonthSetup | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSetup(month)
      .then(setSetup)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load setup"));
  }, [month]);

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (!setup) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-zinc-500">Loading…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col items-center bg-zinc-50 px-6 py-16 dark:bg-black">
      <div className="flex w-full max-w-4xl flex-col gap-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">
            Upload statements — {month}
          </h1>
          <Link
            href={`/review/${month}`}
            className="rounded-md bg-black px-4 py-2 font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-black"
          >
            Review transactions →
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <UploadArea month={month} person={setup.personA} />
          <UploadArea month={month} person={setup.personB} />
        </div>
      </div>
    </div>
  );
}
