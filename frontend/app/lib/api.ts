export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type MonthSetup = {
  personA: string;
  personB: string;
  ratioA: number;
  ratioB: number;
};

export type Transaction = {
  transactionId: string;
  date: string;
  originalDescription: string;
  merchantKey: string;
  amount: string;
  accountName: string;
  spender: string;
  category: string;
  costAssignee: number;
  reviewed: boolean;
};

export type Settlement = {
  sharedExpenses: string;
  personalExpenses: Record<string, string>;
  totalCoupleSpend: string;
  totalSpentByEach: Record<string, string>;
  expectedShared: Record<string, string>;
  actualSharedPaid: Record<string, string>;
  finalSettlement: { whoOwesWhom: string; amount: string };
};

export const CATEGORIES = [
  "rent",
  "groceries",
  "food",
  "travel",
  "car",
  "insurance",
  "subscription",
  "utilities",
  "shopping",
  "entertainment",
  "transfer",
  "other",
];

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch {
      // ignore parse errors, fall back to statusText
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function listMonths(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/months`, { cache: "no-store" });
  return handle<string[]>(res);
}

export async function getSetup(month: string): Promise<MonthSetup> {
  const res = await fetch(`${API_BASE}/api/months/${month}/setup`, { cache: "no-store" });
  return handle<MonthSetup>(res);
}

export async function createSetup(month: string, setup: MonthSetup): Promise<MonthSetup> {
  const res = await fetch(`${API_BASE}/api/months/${month}/setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(setup),
  });
  return handle<MonthSetup>(res);
}

export async function uploadStatement(month: string, person: string, file: File) {
  const formData = new FormData();
  formData.append("person", person);
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/months/${month}/upload`, {
    method: "POST",
    body: formData,
  });
  return handle<{ accountName: string; accountType: string; transactionCount: number; transactions: Transaction[] }>(res);
}

export async function listTransactions(month: string): Promise<Transaction[]> {
  const res = await fetch(`${API_BASE}/api/months/${month}/transactions`, { cache: "no-store" });
  return handle<Transaction[]>(res);
}

export async function updateTransaction(
  month: string,
  transactionId: string,
  update: { category?: string; costAssignee?: number }
): Promise<Transaction> {
  const res = await fetch(`${API_BASE}/api/months/${month}/transactions/${transactionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  return handle<Transaction>(res);
}

export async function bulkUpdateTransactions(
  month: string,
  updates: { transactionId: string; category?: string; costAssignee?: number }[]
): Promise<Transaction[]> {
  const res = await fetch(`${API_BASE}/api/months/${month}/transactions`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ updates }),
  });
  return handle<Transaction[]>(res);
}

export async function approveMonth(month: string): Promise<Settlement> {
  const res = await fetch(`${API_BASE}/api/months/${month}/approve`, { method: "POST" });
  return handle<Settlement>(res);
}

export async function getDashboard(month: string): Promise<Settlement> {
  const res = await fetch(`${API_BASE}/api/months/${month}/dashboard`, { cache: "no-store" });
  return handle<Settlement>(res);
}
