import Link from "next/link";
import { listMonths } from "./lib/api";

export default async function Home() {
  let months: string[] = [];
  let error: string | null = null;
  try {
    months = await listMonths();
  } catch {
    error = "Could not reach the backend API. Is it running?";
  }

  return (
    <div className="flex flex-col flex-1 items-center bg-zinc-50 font-sans dark:bg-black px-6 py-16">
      <main className="flex w-full max-w-2xl flex-col gap-8">
        <div className="text-center">
          <h1 className="text-3xl font-semibold tracking-tight text-black dark:text-zinc-50">
            Couple Expense Splitter
          </h1>
          <p className="mt-2 text-zinc-600 dark:text-zinc-400">
            Upload monthly statements, review transactions, and see who owes whom.
          </p>
        </div>

        <Link
          href="/setup"
          className="rounded-md bg-black px-4 py-3 text-center font-medium text-white hover:bg-zinc-800 dark:bg-zinc-50 dark:text-black"
        >
          + Start a new month
        </Link>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {months.length > 0 && (
          <div>
            <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-zinc-500">
              Previous months
            </h2>
            <ul className="flex flex-col gap-2">
              {months.map((month) => (
                <li key={month}>
                  <Link
                    href={`/dashboard/${month}`}
                    className="block rounded-md border border-zinc-200 px-4 py-3 hover:bg-zinc-100 dark:border-zinc-800 dark:hover:bg-zinc-900"
                  >
                    {month}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </div>
  );
}
