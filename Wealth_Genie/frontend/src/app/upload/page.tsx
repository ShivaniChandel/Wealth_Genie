"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Auth state
  const [sessionLoading, setSessionLoading] = useState(true);
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  // Form state
  const [documentType, setDocumentType] = useState("bank_statement");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  // Drag & drop state
  const [isDragActive, setIsDragActive] = useState(false);

  // Upload/UI states
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [successData, setSuccessData] = useState<{ document_id: string; status: string } | null>(null);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession();
        if (error || !session) {
          router.push("/login");
          return;
        }
        setUserEmail(session.user?.email || null);
        setAccessToken(session.access_token);
        setSessionLoading(false);
      } catch (err) {
        console.error("Session check failed:", err);
        router.push("/login");
      }
    };
    checkSession();
  }, [router]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragActive(true);
    } else if (e.type === "dragleave") {
      setIsDragActive(false);
    }
  };

  const validateAndSetFile = (file: File) => {
    setErrorMsg("");
    setSuccessData(null);

    // Validate type (PDF only)
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setErrorMsg("Invalid file type. Only PDF documents are allowed.");
      setSelectedFile(null);
      return;
    }

    // Validate size (max 10MB)
    const max_size = 10 * 1024 * 1024;
    if (file.size > max_size) {
      setErrorMsg("File size exceeds the maximum limit of 10MB.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setErrorMsg("");
    setSuccessData(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMsg("Please select or drop a PDF file first.");
      return;
    }
    if (!accessToken) {
      setErrorMsg("Authentication token missing. Please sign in again.");
      return;
    }

    setUploadLoading(true);
    setErrorMsg("");
    setSuccessData(null);
    setUploadProgress(10); // Start progress bar

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("document_type", documentType);

      // We'll simulate upload progress steps for smooth UI feedback
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 15;
        });
      }, 200);

      const response = await fetch("http://localhost:8000/api/v1/documents/upload", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Upload failed");
      }

      const data = await response.json();
      setUploadProgress(100);
      setSuccessData(data);
    } catch (err: any) {
      console.error("Upload error:", err);
      setErrorMsg(err.message || "An unexpected error occurred during document upload.");
    } finally {
      setUploadLoading(false);
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
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-600 flex items-center justify-center font-bold text-white shadow-lg">
              W
            </div>
            <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
              Wealth Genie
            </span>
          </Link>
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

      {/* Main Upload Form */}
      <main className="relative z-10 flex-1 w-full max-w-2xl mx-auto px-6 py-12 flex flex-col justify-center">
        <div className="mb-8">
          <Link href="/dashboard" className="text-sm text-gray-400 hover:text-white flex items-center gap-1 mb-2 transition-colors">
            ← Back to Dashboard
          </Link>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Upload Document</h1>
          <p className="text-gray-400 mt-1">Upload a statement to expand your AI financial profile.</p>
        </div>

        <div className="glass-panel p-8 md:p-10 rounded-3xl shadow-2xl">
          {errorMsg && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400 flex items-center gap-2" id="upload-error">
              <span>❌</span> {errorMsg}
            </div>
          )}

          {successData && (
            <div className="mb-6 p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-sm flex flex-col gap-3" id="upload-success">
              <div className="text-emerald-400 font-semibold flex items-center gap-2">
                <span>✅</span> Document uploaded successfully!
              </div>
              <div className="font-mono text-xs text-gray-400 space-y-1">
                <div><span className="text-gray-500">Document ID:</span> {successData.document_id}</div>
                <div><span className="text-gray-500">Status:</span> {successData.status}</div>
              </div>
              <div className="mt-2 flex gap-3">
                <Link href="/dashboard" className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-semibold rounded-lg transition-colors">
                  Go to Dashboard
                </Link>
                <button onClick={handleRemoveFile} className="px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-300 text-xs font-semibold rounded-lg border border-white/10 transition-colors">
                  Upload Another File
                </button>
              </div>
            </div>
          )}

          <form onSubmit={handleUploadSubmit} className="flex flex-col gap-6" id="upload-form">
            {/* Document Type Dropdown */}
            <div className="flex flex-col gap-2">
              <label htmlFor="document-type" className="text-sm font-semibold text-gray-300">
                Document Type
              </label>
              <select
                id="document-type"
                name="document_type"
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                disabled={uploadLoading || !!successData}
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors appearance-none"
              >
                <option value="bank_statement" className="bg-[#0f172a]">Bank Statement</option>
                <option value="credit_card" className="bg-[#0f172a]">Credit Card Statement</option>
                <option value="loan" className="bg-[#0f172a]">Loan Document</option>
                <option value="salary_slip" className="bg-[#0f172a]">Salary Slip</option>
              </select>
            </div>

            {/* Drag & Drop File Zone */}
            <div className="flex flex-col gap-2">
              <label className="text-sm font-semibold text-gray-300">
                Document File (PDF only)
              </label>
              
              {!selectedFile ? (
                <div
                  onDragEnter={handleDrag}
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`w-full min-h-[220px] rounded-2xl border-2 border-dashed flex flex-col justify-center items-center p-6 text-center cursor-pointer transition-all duration-300 ${
                    isDragActive 
                      ? "border-emerald-500 bg-emerald-500/5 shadow-inner" 
                      : "border-white/10 bg-white/5 hover:border-white/20"
                  }`}
                  id="drop-zone"
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    accept=".pdf,application/pdf"
                    className="hidden"
                  />
                  <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center text-2xl mb-4">
                    📤
                  </div>
                  <p className="text-sm font-semibold text-gray-200 mb-1">
                    Drag and drop your PDF here, or click to browse
                  </p>
                  <p className="text-xs text-gray-400">
                    PDF format only. Maximum file size 10MB.
                  </p>
                </div>
              ) : (
                <div className="w-full p-5 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-xl shrink-0">
                      📄
                    </div>
                    <div className="overflow-hidden">
                      <div className="text-sm font-semibold text-gray-200 truncate" title={selectedFile.name}>
                        {selectedFile.name}
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </div>
                    </div>
                  </div>
                  {!uploadLoading && !successData && (
                    <button
                      type="button"
                      onClick={handleRemoveFile}
                      className="px-3 py-1.5 text-xs font-semibold text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors shrink-0"
                      aria-label="Remove selected file"
                    >
                      Remove
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Upload progress indicator */}
            {uploadLoading && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-gray-400 font-medium">
                  <span>Uploading statement...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
                  <div 
                    className="h-full bg-emerald-500 transition-all duration-300 ease-out"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            {!successData && (
              <button
                type="submit"
                disabled={uploadLoading || !selectedFile}
                className="w-full py-4 bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-500/30 disabled:text-gray-400 font-semibold rounded-xl shadow-lg shadow-emerald-500/20 transition-all duration-200 flex justify-center items-center gap-2"
              >
                {uploadLoading ? "Uploading Document..." : "Upload Document"}
              </button>
            )}
          </form>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 py-8 border-t border-white/5 text-center md:text-left">
        <p className="text-xs text-gray-500">
          © {new Date().getFullYear()} Wealth Genie. All uploaded documents are parsed securely and isolated per user.
        </p>
      </footer>
    </div>
  );
}
