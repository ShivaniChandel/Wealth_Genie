"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { DashboardResponse } from "@/lib/api/types";

export default function DashboardPage() {
  const router = useRouter();
  const [sessionLoading, setSessionLoading] = useState(true);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setDashboardLoading(true);
    setDashboardError(null);

    try {
      const data = await apiFetch<DashboardResponse>("/dashboard");
      setDashboard(data);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        router.push("/login");
        return;
      }

      setDashboardError(
        error instanceof Error ? error.message : "Could not load dashboard data."
      );
    } finally {
      setDashboardLoading(false);
    }
  }, [router]);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const {
          data: { session },
          error,
        } = await supabase.auth.getSession();

        if (error || !session) {
          router.push("/login");
          return;
        }

        setUserEmail(session.user?.email || null);
        setSessionLoading(false);
        await loadDashboard();
      } catch (error) {
        console.error("Session check failed:", error);
        router.push("/login");
      }
    };

    checkSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === "SIGNED_OUT") {
        router.push("/login");
      } else if (session) {
        setUserEmail(session.user?.email || null);
        await loadDashboard();
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [loadDashboard, router]);

  const handleLogout = async () => {
    try {
      await apiFetch<void>("/auth/logout", { method: "POST" }).catch((error) =>
        console.warn("Backend logout notification failed:", error)
      );
      await supabase.auth.signOut();
      router.push("/login");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  const formatCurrency = (value: string) => `₹${value}`;
  const formatLastUpdated = (value: string | null) => {
    if (!value) return "Not available";

    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  };

  if (sessionLoading) {
    return (
      <div className="min-h-screen bg-[#030712] text-gray-100 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin" />
          <p className="text-gray-400 text-sm font-medium">Verifying session...</p>
        </div>
      </div>
    );
  }

  const metricCards = dashboard
    ? [
        { label: "Net Worth", value: formatCurrency(dashboard.net_worth_estimate) },
        { label: "Monthly Income", value: formatCurrency(dashboard.total_monthly_income) },
        { label: "Monthly Expenses", value: formatCurrency(dashboard.total_monthly_expenses) },
        { label: "Total Savings", value: formatCurrency(dashboard.total_savings) },
        { label: "Total Debt", value: formatCurrency(dashboard.total_debt) },
        { label: "Savings Rate", value: `${dashboard.savings_rate_percent}%` },
        { label: "Documents Processed", value: String(dashboard.documents_processed) },
        { label: "Last Updated", value: formatLastUpdated(dashboard.last_updated) },
      ]
    : [];

  return (
    <div className="relative min-h-screen bg-[#030712] text-gray-100 flex flex-col justify-between overflow-hidden">
      <div className="glow-blur-green top-[10%] left-[5%]" />
      <div className="glow-blur-indigo bottom-[20%] right-[10%]" />

      <header className="relative z-10 w-full max-w-7xl mx-auto px-6 py-6 flex justify-between items-center border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg">
            W
          </div>
          <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            Wealth Genie
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden sm:inline text-sm text-gray-400 font-medium">{userEmail}</span>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white rounded-xl border border-white/10 transition-all duration-200"
          >
            Log Out
          </button>
        </div>
      </header>

      <main className="relative z-10 flex-1 w-full max-w-7xl mx-auto px-6 py-12 flex flex-col gap-10">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Financial Dashboard</h1>
          <p className="text-gray-400 mt-1">Overview of your latest persisted financial data.</p>
        </div>

        {dashboardError ? (
          <div className="glass-panel p-8 md:p-10 rounded-3xl flex flex-col justify-center items-center text-center min-h-[300px]">
            <h2 className="text-xl font-bold text-white mb-2">Dashboard unavailable</h2>
            <p className="text-red-400 text-sm max-w-md mb-6">{dashboardError}</p>
            <button
              onClick={loadDashboard}
              className="px-6 py-3 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-xl border border-white/10 transition-all duration-200"
            >
              Try Again
            </button>
          </div>
        ) : dashboardLoading || !dashboard ? (
          <div className="glass-panel p-8 md:p-10 rounded-3xl flex flex-col justify-center items-center text-center min-h-[300px]">
            <div className="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin mb-4" />
            <p className="text-gray-400 text-sm font-medium">Loading dashboard...</p>
          </div>
        ) : dashboard.documents_processed === 0 ? (
          <div className="glass-panel p-8 md:p-10 rounded-3xl flex flex-col justify-center items-center text-center min-h-[300px]">
            <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center text-3xl mb-6">
              📁
            </div>
            <h2 className="text-xl font-bold text-white mb-2">No documents processed yet</h2>
            <p className="text-gray-400 text-sm max-w-md mb-8 leading-relaxed">
              Upload a financial document to build your financial dashboard.
            </p>
            <Link
              href="/upload"
              className="px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/20 transition-all duration-200"
            >
              Upload First Document
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {metricCards.map((metric) => (
              <section key={metric.label} className="glass-panel p-6 rounded-2xl">
                <p className="text-xs font-medium uppercase tracking-wider text-gray-400">{metric.label}</p>
                <p className="mt-3 text-2xl font-bold text-white break-words">{metric.value}</p>
              </section>
            ))}
          </div>
        )}
      </main>

      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 py-8 border-t border-white/5 text-center md:text-left">
        <p className="text-xs text-gray-500">
          © {new Date().getFullYear()} Wealth Genie. All data is encrypted and validated server-side.
        </p>
      </footer>
    </div>
  );
}
