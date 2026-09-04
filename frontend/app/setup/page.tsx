"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createSetup } from "../lib/api";

function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function SetupPage() {
  const router = useRouter();
  const [month, setMonth] = useState(currentMonth());
  const [personA, setPersonA] = useState("");
  const [personB, setPersonB] = useState("");
  const [ratioA, setRatioA] = useState(50);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const ratioB = 100 - ratioA;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!personA.trim() || !personB.trim()) {
      setError("Both person names are required.");
      return;
    }
    if (!/^\d{4}-\d{2}$/.test(month)) {
      setError("Month must be in YYYY-MM format.");
      return;
    }
    setSubmitting(true);
    try {
      await createSetup(month, { personA, personB, ratioA, ratioB });
      router.push(`/upload/${month}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save setup.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col flex-1 items-center bg-zinc-50 px-6 py-16 dark:bg-black">
      <form
        onSubmit={handleSubmit}
        className="flex w-full max-w-md flex-col gap-4 rounded-lg border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
      >
        <h1 className="text-xl font-semibold text-black dark:text-zinc-50">Month setup</h1>

        <label className="flex flex-col gap-1 text-sm text-zinc-700 dark:text-zinc-300">
          Month
          <input
            type="month"
            required
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="rounded border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm text-zinc-700 dark:text-zinc-300">
          Person A name
          <input
            required
            value={personA}
            onChange={(e) => setPersonA(e.target.value)}
            className="rounded border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm text-zinc-700 dark:text-zinc-300">
          Person B name
          <input
            required
            value={personB}
            onChange={(e) => setPersonB(e.target.value)}
            className="rounded border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm text-zinc-700 dark:text-zinc-300">
          Split ratio ({personA || "A"} {ratioA}% / {personB || "B"} {ratioB}%)
          <input
            type="range"
            min={0}
            max={100}
            value={ratioA}
            onChange={(e) => setRatioA(Number(e.target.value))}
          />
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="mt-2 rounded-md bg-black px-4 py-2 font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-50 dark:text-black"
        >
          {submitting ? "Saving..." : "Continue to upload"}
        </button>
      </form>
    </div>
  );
}
