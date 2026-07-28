"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ApiError, apiFetch } from "@/lib/api/client";
import type { AnalysisJobStatusResponse } from "@/lib/api/types";

const POLLING_INTERVAL_MS = 3000;
const JOB_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default function ProcessingPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();
  const [status, setStatus] = useState<AnalysisJobStatusResponse["status"] | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [connectionMessage, setConnectionMessage] = useState<string | null>(null);
  const hasValidJobId = JOB_ID_PATTERN.test(jobId ?? "");

  useEffect(() => {
    if (!hasValidJobId) return;

    let cancelled = false;
    let terminal = false;
    let inFlight = false;

    const pollStatus = async () => {
      if (cancelled || terminal || inFlight) return;

      inFlight = true;

      try {
        const result = await apiFetch<AnalysisJobStatusResponse>(
          `/analysis/status/${encodeURIComponent(jobId)}`
        );

        if (cancelled) return;

        setStatus(result.status);
        setConnectionMessage(null);

        if (result.status === "completed") {
          terminal = true;
          router.push("/dashboard");
        } else if (result.status === "failed") {
          terminal = true;
          setErrorMessage(result.error_message || "Document processing failed.");
        }
      } catch (error) {
        if (cancelled) return;

        if (error instanceof ApiError && error.status === 401) {
          terminal = true;
          router.push("/login");
        } else if (error instanceof ApiError && error.status === 404) {
          terminal = true;
          setErrorMessage("Analysis job not found.");
        } else {
          setConnectionMessage("Connection issue. Retrying shortly.");
        }
      } finally {
        inFlight = false;
      }
    };

    void pollStatus();
    const intervalId = window.setInterval(() => void pollStatus(), POLLING_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [hasValidJobId, jobId, router]);

  const displayError = hasValidJobId ? errorMessage : "Invalid analysis job ID.";
  const isFailed = displayError !== null;
  const statusLabel = status === "queued" ? "Queued" : "Processing";
  const statusDescription =
    status === "queued"
      ? "Your document is queued for analysis."
      : "Your document is being analyzed. This page updates automatically.";

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

      <main className="relative z-10 flex-1 w-full max-w-2xl mx-auto px-6 py-12 flex items-center">
        <section className="glass-panel w-full p-8 md:p-10 rounded-3xl text-center">
          {isFailed ? (
            <>
              <div className="w-16 h-16 mx-auto rounded-2xl bg-red-500/10 flex items-center justify-center text-3xl mb-6">
                ✕
              </div>
              <h1 className="text-2xl font-bold text-white">Processing failed</h1>
              <p className="mt-3 text-sm text-red-400">{displayError}</p>
              <Link
                href="/dashboard"
                className="inline-flex mt-8 px-6 py-3 bg-white/5 hover:bg-white/10 text-white font-semibold rounded-xl border border-white/10 transition-all duration-200"
              >
                Back to Dashboard
              </Link>
            </>
          ) : (
            <>
              <div className="w-14 h-14 mx-auto rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin mb-6" />
              <p className="text-sm font-semibold text-emerald-400 uppercase tracking-wider">
                {statusLabel}
              </p>
              <h1 className="mt-2 text-2xl font-bold text-white">Processing your document</h1>
              <p className="mt-3 text-sm text-gray-400">{statusDescription}</p>
              {connectionMessage && (
                <p className="mt-6 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-sm text-amber-300">
                  {connectionMessage}
                </p>
              )}
            </>
          )}
        </section>
      </main>

      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 py-8 border-t border-white/5 text-center md:text-left">
        <p className="text-xs text-gray-500">Your analysis is securely processed in the background.</p>
      </footer>
    </div>
  );
}
