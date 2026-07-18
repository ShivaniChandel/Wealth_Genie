"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

interface TokenVerificationData {
  user_id: string;
  email: string;
  aud: string;
  role: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [sessionLoading, setSessionLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  
  // Backend verification state
  const [verificationLoading, setVerificationLoading] = useState(false);
  const [verificationResult, setVerificationResult] = useState<TokenVerificationData | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (error || !session) {
          router.push("/login");
          return;
        }

        setUserEmail(session.user?.email || null);
        setSessionLoading(false);

        // Fetch verification from the backend
        verifyBackendToken(session.access_token);
      } catch (err) {
        console.error("Session check failed:", err);
        router.push("/login");
      }
    };

    checkSession();

    // Setup auth state listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === "SIGNED_OUT") {
        router.push("/login");
      } else if (session) {
        setUserEmail(session.user?.email || null);
        verifyBackendToken(session.access_token);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [router]);

  const verifyBackendToken = async (accessToken: string) => {
    setVerificationLoading(true);
    setVerificationError(null);
    try {
      const response = await fetch("http://localhost:8000/api/v1/auth/verify-token", {
        method: "GET",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to verify token with backend");
      }

      const data: TokenVerificationData = await response.json();
      setVerificationResult(data);
    } catch (err: any) {
      console.error("Backend verification error:", err);
      setVerificationError(err.message || "Could not reach backend API");
    } finally {
      setVerificationLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      router.push("/login");
    } catch (err) {
      console.error("Logout failed:", err);
    }
  };

  if (sessionLoading) {
    return (
      <div className="min-h-screen bg-[#030712] text-gray-100 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 animate-spin" />
          <p className="text-gray-400 text-sm font-medium">Verifying Session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen bg-[#030712] text-gray-100 flex flex-col justify-between overflow-hidden">
      {/* Decorative Blur Backgrounds */}
      <div className="glow-blur-green top-[10%] left-[5%]" />
      <div className="glow-blur-indigo bottom-[20%] right-[10%]" />

      {/* Header */}
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
          <span className="hidden sm:inline text-sm text-gray-400 font-medium">
            {userEmail}
          </span>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm font-medium bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white rounded-xl border border-white/10 transition-all duration-200"
          >
            Log Out
          </button>
        </div>
      </header>

      {/* Main Dashboard Area */}
      <main className="relative z-10 flex-1 w-full max-w-7xl mx-auto px-6 py-12 flex flex-col gap-10">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">
            Financial Dashboard
          </h1>
          <p className="text-gray-400 mt-1">
            Overview of your financial reports and agent recommendations.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Empty State Panel */}
          <div className="lg:col-span-2 glass-panel p-8 md:p-10 rounded-3xl flex flex-col justify-center items-center text-center min-h-[300px]">
            <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center text-3xl mb-6">
              📁
            </div>
            <h3 className="text-xl font-bold text-white mb-2">No documents processed yet</h3>
            <p className="text-gray-400 text-sm max-w-md mb-8 leading-relaxed">
              Upload bank statements, credit card statements, loan contracts, or salary slips. The Wealth Genie AI agents will analyze them and build your financial profile.
            </p>
            <Link href="/upload" className="px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/20 transition-all duration-200">
              Upload First Document
            </Link>
          </div>

          {/* Backend Connection / Token Validation Panel */}
          <div className="glass-panel p-8 rounded-3xl flex flex-col justify-between">
            <div>
              <h2 className="text-lg font-bold text-white mb-3">Backend Integration</h2>
              <p className="text-gray-400 text-xs leading-relaxed mb-6">
                FastAPI JWT verification status. This panel validates that the Next.js client JWT token is successfully validated by the FastAPI middleware using `SUPABASE_JWT_SECRET`.
              </p>

              <div className="space-y-4">
                <div className="flex items-center justify-between text-xs p-3 rounded-lg bg-white/5 border border-white/5">
                  <span className="text-gray-400">Connection State:</span>
                  {verificationLoading ? (
                    <span className="text-yellow-400 font-semibold animate-pulse">Verifying...</span>
                  ) : verificationError ? (
                    <span className="text-red-400 font-semibold">Offline/Error</span>
                  ) : (
                    <span className="text-emerald-400 font-semibold">Active</span>
                  )}
                </div>

                {verificationError && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
                    <strong>Error:</strong> {verificationError}
                  </div>
                )}

                {verificationResult && (
                  <div className="space-y-2 text-xs p-4 rounded-lg bg-white/5 border border-white/5 font-mono">
                    <div className="text-gray-300 font-bold mb-1 border-b border-white/5 pb-1">Token Claims:</div>
                    <div className="overflow-x-auto whitespace-nowrap">
                      <span className="text-gray-400">User ID:</span>{" "}
                      <span className="text-emerald-400">{verificationResult.user_id}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Audience:</span>{" "}
                      <span className="text-indigo-400">{verificationResult.aud}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Role:</span>{" "}
                      <span className="text-teal-400">{verificationResult.role}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <button
              onClick={() => {
                supabase.auth.getSession().then(({ data: { session } }) => {
                  if (session) verifyBackendToken(session.access_token);
                });
              }}
              disabled={verificationLoading}
              className="mt-6 w-full py-3 bg-white/5 hover:bg-white/10 disabled:bg-white/5 text-gray-300 hover:text-white font-medium text-xs rounded-xl border border-white/10 transition-all duration-200"
            >
              Force Re-verify Token
            </button>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 py-8 border-t border-white/5 text-center md:text-left">
        <p className="text-xs text-gray-500">
          © {new Date().getFullYear()} Wealth Genie. All data is encrypted and validated server-side.
        </p>
      </footer>
    </div>
  );
}
