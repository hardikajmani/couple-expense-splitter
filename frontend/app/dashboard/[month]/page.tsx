"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { getDashboard, getSetup, listTransactions, MonthSetup, Settlement, Transaction } from "../../lib/api";

const COLORS = [
  "#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#8b5cf6",
  "#ec4899", "#84cc16", "#f97316", "#14b8a6", "#a855f7", "#64748b",
];

function categoryBreakdown(transactions: Transaction[], filter?: (t: Transaction) => boolean) {
  const totals = new Map<string, number>();
  for (const t of transactions) {
    if (t.costAssignee === -1) continue;
    if (filter && !filter(t)) continue;
    const amt = parseFloat(t.amount);
    totals.set(t.category, (totals.get(t.category) || 0) + amt);
  }
  return Array.from(totals.entries()).map(([name, value]) => ({ name, value }));
}

function CategoryPie({ title, data }: { title: string; data: { name: string; value: number }[] }) {
  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <h3 className="mb-2 text-sm font-medium text-zinc-500">{title}</h3>
        <p className="py-8 text-sm text-zinc-400">No data</p>
      </div>
    );
  }
  return (
    <div className="flex flex-col items-center rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
      <h3 className="mb-2 text-sm font-medium text-zinc-500">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(v: number) => `$${v.toFixed(2)}`} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function DashboardPage({ params }: { params: Promise<{ month: string }> }) {
  const { month } = use(params);
  const [setup, setSetup] = useState<MonthSetup | null>(null);
  const [summary, setSummary] = useState<Settlement | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getSetup(month), getDashboard(month), listTransactions(month)])
      .then(([s, d, t]) => {
        setSetup(s);
        setSummary(d);
        setTransactions(t);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load dashboard"));
  }, [month]);

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (!setup || !summary) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-zinc-500">Loading…</p>
      </div>
    );
  }

  const { personA, personB } = setup;

  return (
    <div className="flex flex-1 flex-col gap-6 bg-zinc-50 px-6 py-10 dark:bg-black">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">Dashboard — {month}</h1>
        <Link
          href={`/review/${month}`}
          className="rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900"
        >
          Back to review
        </Link>
      </div>

      <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-6 text-center dark:border-indigo-900 dark:bg-indigo-950/30">
        <p className="text-sm uppercase tracking-wide text-indigo-500">Final settlement</p>
        <p className="mt-1 text-3xl font-bold text-indigo-700 dark:text-indigo-300">
          {summary.finalSettlement.whoOwesWhom === "settled"
            ? "All settled up!"
            : `${summary.finalSettlement.whoOwesWhom}: $${summary.finalSettlement.amount}`}
        </p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-200 text-zinc-500 dark:border-zinc-800">
            <tr>
              <th className="p-2">Person</th>
              <th className="p-2">Shared paid</th>
              <th className="p-2">Personal expenses</th>
              <th className="p-2">Total spent</th>
              <th className="p-2">Expected shared contribution</th>
              <th className="p-2">Net settlement</th>
            </tr>
          </thead>
          <tbody>
            {[personA, personB].map((person) => {
              const actual = parseFloat(summary.actualSharedPaid[person] || "0");
              const expected = parseFloat(summary.expectedShared[person] || "0");
              const net = actual - expected;
              return (
                <tr key={person} className="border-b border-zinc-100 dark:border-zinc-900">
                  <td className="p-2 font-medium">{person}</td>
                  <td className="p-2">${summary.actualSharedPaid[person]}</td>
                  <td className="p-2">${summary.personalExpenses[person]}</td>
                  <td className="p-2">${summary.totalSpentByEach[person]}</td>
                  <td className="p-2">${summary.expectedShared[person]}</td>
                  <td className={`p-2 ${net >= 0 ? "text-green-700" : "text-red-600"}`}>
                    {net >= 0 ? "+" : ""}
                    {net.toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <CategoryPie
          title="Couple spend by category"
          data={categoryBreakdown(transactions, (t) => t.costAssignee === 0)}
        />
        <CategoryPie
          title={`${personA} spend by category`}
          data={categoryBreakdown(transactions, (t) => t.spender === personA)}
        />
        <CategoryPie
          title={`${personB} spend by category`}
          data={categoryBreakdown(transactions, (t) => t.spender === personB)}
        />
      </div>
    </div>
  );
}
