"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { ReportDetailResponse } from "@/lib/api/types";

const REPORT_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [report, setReport] = useState<ReportDetailResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const hasValidReportId = REPORT_ID_PATTERN.test(id ?? "");

  useEffect(() => {
    if (!hasValidReportId) return;

    const loadReport = async () => {
      try {
        const result = await apiFetch<ReportDetailResponse>(`/reports/${encodeURIComponent(id)}`);
        setReport(result);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          router.push("/login");
          return;
        }

        if (error instanceof ApiError && error.status === 404) {
          setErrorMessage("Report not found.");
          return;
        }

        setErrorMessage(error instanceof Error ? error.message : "Could not load report.");
      }
    };

    void loadReport();
  }, [hasValidReportId, id, router]);

  const displayError = hasValidReportId ? errorMessage : "Invalid report.";

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
        <Link href="/reports" className="text-sm text-gray-400 hover:text-white transition-colors">
          ← Back to Reports
        </Link>

        {displayError ? (
          <section className="glass-panel mt-8 p-8 rounded-3xl text-center min-h-[240px] flex flex-col items-center justify-center">
            <h1 className="text-2xl font-bold text-white">{displayError === "Invalid report." ? "Invalid report" : "Report unavailable"}</h1>
            <p className="mt-3 text-sm text-red-400">{displayError}</p>
          </section>
        ) : report === null ? (
          <section className="glass-panel mt-8 p-8 rounded-3xl text-center min-h-[240px] flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin mb-4" />
            <p className="text-sm text-gray-400">Loading report...</p>
          </section>
        ) : (
          <article className="mt-8 space-y-6">
            <div>
              <h1 className="text-3xl font-extrabold text-white tracking-tight">AI CFO Report</h1>
              <p className="mt-2 text-sm text-gray-400">{report.content.executive_summary}</p>
            </div>

            <section className="glass-panel p-6 rounded-2xl">
              <p className="text-xs font-medium uppercase tracking-wider text-gray-400">Financial health score</p>
              <p className="mt-2 text-3xl font-bold text-white">{report.content.overall_financial_health_score}</p>
            </section>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <section className="glass-panel p-6 rounded-2xl">
                <h2 className="font-bold text-white">Debt analysis</h2>
                <p className="mt-3 text-sm text-gray-400">Outstanding debt: {report.content.debt_analysis.total_outstanding_debt}</p>
                <p className="mt-1 text-sm text-gray-400">Debt data: {report.content.debt_analysis.has_debt ? "Available" : "Not available"}</p>
              </section>
              <section className="glass-panel p-6 rounded-2xl">
                <h2 className="font-bold text-white">Savings analysis</h2>
                <p className="mt-3 text-sm text-gray-400">Total savings: {report.content.savings_analysis.total_savings}</p>
                <p className="mt-1 text-sm text-gray-400">Savings data: {report.content.savings_analysis.has_savings_data ? "Available" : "Not available"}</p>
              </section>
              <section className="glass-panel p-6 rounded-2xl">
                <h2 className="font-bold text-white">Budget analysis</h2>
                <p className="mt-3 text-sm text-gray-400">Debit spending: {report.content.budget_analysis.total_debit_spending}</p>
                <p className="mt-1 text-sm text-gray-400">Transaction data: {report.content.budget_analysis.has_transaction_data ? "Available" : "Not available"}</p>
              </section>
            </div>

            <section className="glass-panel p-6 rounded-2xl">
              <h2 className="font-bold text-white">Priority recommendations</h2>
              {report.content.priority_recommendations.length === 0 ? (
                <p className="mt-3 text-sm text-gray-400">No priority recommendations.</p>
              ) : (
                <div className="mt-4 space-y-4">
                  {report.content.priority_recommendations.map((recommendation, index) => (
                    <div key={`${recommendation.agent}-${recommendation.title}-${index}`} className="border-t border-white/10 pt-4 first:border-t-0 first:pt-0">
                      <p className="text-sm font-semibold text-white">{recommendation.title}</p>
                      <p className="mt-1 text-sm text-gray-400">{recommendation.detail}</p>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </article>
        )}
      </main>

      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 py-8 border-t border-white/5">
        <p className="text-xs text-gray-500">Persisted AI CFO analysis.</p>
      </footer>
    </div>
  );
}
