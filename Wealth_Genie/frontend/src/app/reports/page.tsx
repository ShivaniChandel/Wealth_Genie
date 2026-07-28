"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { ReportListResponse } from "@/lib/api/types";

export default function ReportsPage() {
  const router = useRouter();
  const [reports, setReports] = useState<ReportListResponse["reports"] | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const loadReports = async () => {
      try {
        const result = await apiFetch<ReportListResponse>("/reports");
        setReports(result.reports);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          router.push("/login");
          return;
        }

        setErrorMessage(error instanceof Error ? error.message : "Could not load reports.");
      }
    };

    void loadReports();
  }, [router]);

  const formatCreatedAt = (value: string) => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  };

  return (
    <div className="relative min-h-screen bg-[#030712] text-gray-100 flex flex-col justify-between overflow-hidden">
      <div className="glow-blur-green top-[10%] left-[5%]" />
      <div className="glow-blur-indigo bottom-[20%] right-[10%]" />

      <header className="relative z-10 w-full max-w-7xl mx-auto px-6 py-6 border-b border-white/5">
        <Link href="/dashboard" className="flex items-center gap-2 w-fit">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg">
            W
          </div>
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            Wealth Genie
          </span>
        </Link>
      </header>

      <main className="relative z-10 flex-1 w-full max-w-5xl mx-auto px-6 py-12">
        <div className="mb-8">
          <Link href="/dashboard" className="text-sm text-gray-400 hover:text-white transition-colors">
            ← Back to Dashboard
          </Link>
          <h1 className="mt-3 text-3xl font-extrabold text-white tracking-tight">Reports</h1>
          <p className="mt-1 text-gray-400">Your persisted AI CFO reports.</p>
        </div>

        {errorMessage ? (
          <section className="glass-panel p-8 rounded-3xl text-center min-h-[240px] flex flex-col items-center justify-center">
            <h2 className="text-xl font-bold text-white">Reports unavailable</h2>
            <p className="mt-3 text-sm text-red-400">{errorMessage}</p>
          </section>
        ) : reports === null ? (
          <section className="glass-panel p-8 rounded-3xl text-center min-h-[240px] flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin mb-4" />
            <p className="text-sm text-gray-400">Loading reports...</p>
          </section>
        ) : reports.length === 0 ? (
          <section className="glass-panel p-8 rounded-3xl text-center min-h-[240px] flex flex-col items-center justify-center">
            <h2 className="text-xl font-bold text-white">No reports yet</h2>
            <p className="mt-3 text-sm text-gray-400">Reports appear after document analysis completes.</p>
          </section>
        ) : (
          <div className="grid gap-4">
            {reports.map((report) => (
              <Link
                key={report.id}
                href={`/reports/${report.id}`}
                className="glass-panel p-6 rounded-2xl hover:border-white/20 transition-colors"
              >
                <p className="text-lg font-semibold text-white">AI CFO Report</p>
                <p className="mt-2 text-sm text-gray-400">Created: {formatCreatedAt(report.created_at)}</p>
                <p className="mt-1 text-xs text-gray-500 break-all">
                  Financial profile: {report.financial_profile_id}
                </p>
              </Link>
            ))}
          </div>
        )}
      </main>

      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 py-8 border-t border-white/5">
        <p className="text-xs text-gray-500">Persisted financial analysis for your account.</p>
      </footer>
    </div>
  );
}
