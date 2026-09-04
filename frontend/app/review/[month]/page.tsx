"use client";

import { use, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  approveMonth,
  bulkUpdateTransactions,
  CATEGORIES,
  listTransactions,
  Transaction,
  updateTransaction,
} from "../../lib/api";

const ASSIGNEE_LABELS: Record<number, string> = {
  0: "Shared",
  1: "Person A",
  2: "Person B",
  [-1]: "Exclude",
};

export default function ReviewPage({ params }: { params: Promise<{ month: string }> }) {
  const { month } = use(params);
  const router = useRouter();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [activeAccount, setActiveAccount] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const txns = await listTransactions(month);
        if (cancelled) return;
        setTransactions(txns);
        setActiveAccount((prev) => prev ?? (txns.length > 0 ? txns[0].accountName : null));
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load transactions");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [month]);

  const accounts = useMemo(
    () => Array.from(new Set(transactions.map((t) => t.accountName))).sort(),
    [transactions]
  );

  const visible = useMemo(
    () => transactions.filter((t) => t.accountName === activeAccount),
    [transactions, activeAccount]
  );

  async function handleFieldChange(
    transactionId: string,
    update: { category?: string; costAssignee?: number }
  ) {
    setTransactions((prev) =>
      prev.map((t) => (t.transactionId === transactionId ? { ...t, ...update, reviewed: true } : t))
    );
    try {
      await updateTransaction(month, transactionId, update);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save edit");
      try {
        const txns = await listTransactions(month);
        setTransactions(txns);
      } catch {
        // ignore; the earlier error message is already shown
      }
    }
  }

  function toggleSelected(transactionId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(transactionId)) next.delete(transactionId);
      else next.add(transactionId);
      return next;
    });
  }

  async function applyBulkEdit(update: { category?: string; costAssignee?: number }) {
    if (selected.size === 0) return;
    const ids = Array.from(selected);
    try {
      await bulkUpdateTransactions(
        month,
        ids.map((id) => ({ transactionId: id, ...update }))
      );
      setTransactions((prev) =>
        prev.map((t) => (selected.has(t.transactionId) ? { ...t, ...update, reviewed: true } : t))
      );
      setSelected(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk edit failed");
    }
  }

  async function markSelectedReviewed() {
    if (selected.size === 0) return;
    const ids = Array.from(selected);
    try {
      await bulkUpdateTransactions(
        month,
        ids.map((id) => ({ transactionId: id }))
      );
      setTransactions((prev) =>
        prev.map((t) => (selected.has(t.transactionId) ? { ...t, reviewed: true } : t))
      );
      setSelected(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to mark as reviewed");
    }
  }

  function toggleSelectAllVisible() {
    setSelected((prev) => {
      const visibleIds = visible.map((t) => t.transactionId);
      const allSelected = visibleIds.length > 0 && visibleIds.every((id) => prev.has(id));
      const next = new Set(prev);
      if (allSelected) {
        visibleIds.forEach((id) => next.delete(id));
      } else {
        visibleIds.forEach((id) => next.add(id));
      }
      return next;
    });
  }

  const unreviewedCount = transactions.filter((t) => !t.reviewed).length;
  const allVisibleSelected = visible.length > 0 && visible.every((t) => selected.has(t.transactionId));

  async function handleApprove() {
    setApproving(true);
    setError(null);
    try {
      await approveMonth(month);
      router.push(`/dashboard/${month}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    } finally {
      setApproving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-zinc-500">Loading…</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 bg-zinc-50 px-6 py-10 dark:bg-black">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">Review — {month}</h1>
        <button
          onClick={handleApprove}
          disabled={approving || unreviewedCount > 0}
          title={unreviewedCount > 0 ? `${unreviewedCount} transaction(s) still need review` : ""}
          className="rounded-md bg-black px-4 py-2 font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-50 dark:text-black"
        >
          {approving ? "Approving…" : "Approve month"}
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {unreviewedCount > 0 && (
        <p className="text-sm text-amber-600">
          {unreviewedCount} transaction(s) still need review (including auto-categorized suggestions)
          before approval.
        </p>
      )}

      <div className="flex flex-wrap gap-2 border-b border-zinc-200 dark:border-zinc-800">
        {accounts.map((acc) => (
          <button
            key={acc}
            onClick={() => setActiveAccount(acc)}
            className={`rounded-t-md px-4 py-2 text-sm font-medium ${
              activeAccount === acc
                ? "bg-white text-black dark:bg-zinc-950 dark:text-zinc-50"
                : "text-zinc-500 hover:text-black dark:hover:text-zinc-100"
            }`}
          >
            {acc}
          </button>
        ))}
      </div>

      {selected.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-md bg-zinc-100 px-4 py-2 text-sm dark:bg-zinc-900">
          <span>{selected.size} selected</span>
          <select
            className="rounded border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900"
            onChange={(e) => e.target.value && applyBulkEdit({ category: e.target.value })}
            defaultValue=""
          >
            <option value="" disabled>
              Set category…
            </option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <select
            className="rounded border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900"
            onChange={(e) => e.target.value !== "" && applyBulkEdit({ costAssignee: Number(e.target.value) })}
            defaultValue=""
          >
            <option value="" disabled>
              Set assignee…
            </option>
            {Object.entries(ASSIGNEE_LABELS).map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
          <button
            onClick={markSelectedReviewed}
            className="rounded border border-zinc-300 px-2 py-1 hover:bg-zinc-200 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            Confirm as reviewed
          </button>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="border-b border-zinc-200 text-zinc-500 dark:border-zinc-800">
            <tr>
              <th className="p-2">
                <input
                  type="checkbox"
                  checked={allVisibleSelected}
                  onChange={toggleSelectAllVisible}
                  aria-label="Select all visible rows"
                />
              </th>
              <th className="p-2">Spender</th>
              <th className="p-2">Date</th>
              <th className="p-2">Account</th>
              <th className="p-2">Original description</th>
              <th className="p-2">Merchant</th>
              <th className="p-2">Amount</th>
              <th className="p-2">Category</th>
              <th className="p-2">Assignee</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((t) => (
              <tr
                key={t.transactionId}
                className={`border-b border-zinc-100 dark:border-zinc-900 ${
                  !t.reviewed ? "bg-amber-50 dark:bg-amber-950/20" : ""
                }`}
              >
                <td className="p-2">
                  <input
                    type="checkbox"
                    checked={selected.has(t.transactionId)}
                    onChange={() => toggleSelected(t.transactionId)}
                  />
                </td>
                <td className="p-2">{t.spender}</td>
                <td className="p-2 whitespace-nowrap">{t.date}</td>
                <td className="p-2">{t.accountName}</td>
                <td className="p-2 max-w-xs truncate" title={t.originalDescription}>
                  {t.originalDescription}
                </td>
                <td className="p-2">{t.merchantKey}</td>
                <td className="p-2 whitespace-nowrap">${t.amount}</td>
                <td className="p-2">
                  <select
                    value={t.category}
                    onChange={(e) => handleFieldChange(t.transactionId, { category: e.target.value })}
                    className="rounded border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900"
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="p-2">
                  <select
                    value={t.costAssignee}
                    onChange={(e) =>
                      handleFieldChange(t.transactionId, { costAssignee: Number(e.target.value) })
                    }
                    className="rounded border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900"
                  >
                    {Object.entries(ASSIGNEE_LABELS).map(([v, label]) => (
                      <option key={v} value={v}>
                        {label}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={9} className="p-4 text-center text-zinc-500">
                  No transactions in this account yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
