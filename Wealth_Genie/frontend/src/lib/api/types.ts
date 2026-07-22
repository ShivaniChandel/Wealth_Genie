/**
 * Shared API contracts for the FastAPI backend (`/api/v1/*`).
 *
 * These types mirror the backend's actual Pydantic models, not the (partially
 * stale) prose in docs/07_API_SPECIFICATION.md. Known discrepancies between
 * the docs and this file are called out inline below and repeated in the
 * implementation summary.
 *
 * Source files these types were derived from:
 *   - backend/app/schemas.py
 *   - backend/app/schemas_ext/analysis.py
 *   - backend/app/schemas_ext/financial.py
 *   - backend/app/schemas_ext/debt_analysis.py
 *   - backend/app/schemas_ext/savings_analysis.py
 *   - backend/app/schemas_ext/budget_analysis.py
 *   - backend/app/schemas_ext/ai_cfo_analysis.py
 *
 * Convention: every `Decimal`-backed field on the backend (money, rates,
 * ratios) is serialized as a JSON *string*, not a number — confirmed by
 * `backend/app/tests/test_dashboard.py` (e.g. `"total_monthly_income": "10000"`)
 * and the evaluation fixtures under `backend/evaluation/**/expected.json`.
 * This preserves exact decimal precision across the wire and must not be
 * parsed with `Number()` before doing further arithmetic — treat as display
 * strings, or parse with a decimal-safe library if math is ever needed
 * client-side.
 */

// ---------------------------------------------------------------------------
// Standard error schema (docs/07_API_SPECIFICATION.md, matches the docs)
// ---------------------------------------------------------------------------

export interface ErrorResponse {
  error: string;
  detail: string;
  status_code: number;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface TokenVerificationResponse {
  user_id: string;
  email: string;
  aud: string;
  role: string;
}

// ---------------------------------------------------------------------------
// Documents / Upload
// ---------------------------------------------------------------------------

export type DocumentType = 'bank_statement' | 'credit_card' | 'loan' | 'salary_slip';

export interface UploadResponse {
  document_id: string;
  analysis_job_id: string;
  status: string;
}

// ---------------------------------------------------------------------------
// Analysis / Processing
// ---------------------------------------------------------------------------

export type AnalysisJobStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface AnalysisJobStatusResponse {
  job_id: string;
  document_id: string;
  status: AnalysisJobStatus;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  report_id: string | null;
}

export interface FinancialProfileResponse {
  id: string;
  document_id: string;
  created_at: string;
  profile_json: UniversalFinancialProfile;
}

// ---------------------------------------------------------------------------
// Universal Financial JSON (backend/app/schemas_ext/financial.py)
// ---------------------------------------------------------------------------

export type AccountType = 'savings' | 'current' | 'salary';
export type TransactionType = 'credit' | 'debit';
export type LoanType = 'home' | 'personal' | 'auto' | 'education' | 'other';
export type RecommendationAgent = 'debt_agent' | 'savings_agent' | 'budget_agent' | 'ai_cfo';
export type RecommendationPriority = 'high' | 'medium' | 'low';

export interface UserInfo {
  id: string | null;
  name: string | null;
  email: string | null;
}

export interface Account {
  account_id: string | null;
  bank_name: string | null;
  account_type: AccountType | null;
  currency: string | null;
  opening_balance: string | null;
  closing_balance: string | null;
  statement_period_start: string | null;
  statement_period_end: string | null;
}

export interface Transaction {
  transaction_id: string | null;
  account_id: string | null;
  date: string | null;
  description: string | null;
  amount: string | null;
  type: TransactionType | null;
  category: string | null;
}

export interface Loan {
  loan_id: string | null;
  lender: string | null;
  loan_type: LoanType | null;
  principal: string | null;
  outstanding_balance: string | null;
  interest_rate: string | null;
  emi: string | null;
  tenure_remaining_months: number | null;
}

export interface CreditCard {
  card_id: string | null;
  issuer: string | null;
  credit_limit: string | null;
  outstanding_balance: string | null;
  minimum_due: string | null;
  due_date: string | null;
  interest_rate: string | null;
}

export interface Summary {
  total_monthly_income: string | null;
  total_monthly_expenses: string | null;
  total_debt: string | null;
  total_savings: string | null;
  net_worth_estimate: string | null;
  savings_rate_percent: string | null;
}

export interface Recommendation {
  agent: RecommendationAgent;
  priority: RecommendationPriority;
  title: string;
  detail: string;
}

/**
 * Always empty ({}) in `financial_profiles.profile_json` — per-agent
 * results are written to the separate `recommendations` table instead
 * (see docs/06_DATABASE_SCHEMA.md). Kept loosely typed since it is not
 * currently populated by any code path.
 */
export interface Analysis {
  debt_agent: Record<string, unknown>;
  savings_agent: Record<string, unknown>;
  budget_agent: Record<string, unknown>;
}

export interface UniversalFinancialProfile {
  user: UserInfo;
  accounts: Account[];
  transactions: Transaction[];
  loans: Loan[];
  credit_cards: CreditCard[];
  summary: Summary;
  analysis: Analysis;
  recommendations: Recommendation[];
}

// ---------------------------------------------------------------------------
// Specialist agent results (content of `recommendations` rows, and the
// nested fields of AICFOAnalysisResult below)
// ---------------------------------------------------------------------------

export type LiabilityType = 'loan' | 'credit_card';
export type HighRiskReason =
  | 'high_interest_rate'
  | 'minimum_payment_trap'
  | 'high_utilization';

export interface HighRiskItem {
  liability_type: LiabilityType;
  id: string | null;
  reason: HighRiskReason;
}

export interface DebtAnalysisResult {
  total_outstanding_debt: string;
  total_loan_debt: string;
  total_credit_card_debt: string;
  debt_to_income_ratio: string | null;
  credit_utilization_percent: string | null;
  high_risk_items: HighRiskItem[];
  recommendations: Recommendation[];
  has_debt: boolean;
}

export interface SavingsAnalysisResult {
  total_savings: string;
  monthly_income: string | null;
  monthly_expenses: string | null;
  savings_rate_percent: string | null;
  emergency_fund_months: string | null;
  recommended_emergency_fund: string | null;
  emergency_fund_gap: string | null;
  recommendations: Recommendation[];
  has_savings_data: boolean;
}

export interface CategorySpend {
  category: string;
  amount: string;
  percent_of_categorized_debit_spending: string | null;
}

export interface BudgetAnalysisResult {
  total_debit_spending: string;
  categorized_debit_spending: string;
  uncategorized_debit_spending: string;
  spending_by_category: CategorySpend[];
  monthly_income: string | null;
  monthly_expenses: string | null;
  expense_to_income_ratio: string | null;
  largest_spending_category: string | null;
  largest_spending_category_percent: string | null;
  recommendations: Recommendation[];
  has_transaction_data: boolean;
}

/**
 * NOTE: docs/07_API_SPECIFICATION.md documents the report `content` shape
 * as `{ debt_summary, savings_summary, budget_summary, priority_recommendations,
 * overall_financial_health_score }`. The actual backend
 * (schemas_ext/ai_cfo_analysis.py -> AICFOAnalysisResult) returns
 * `debt_analysis` / `savings_analysis` / `budget_analysis` plus an
 * `executive_summary` string and a combined `recommendations` list. This
 * type follows the real backend model; the docs appear to be stale and
 * should be updated separately.
 */
export interface AICFOAnalysisResult {
  executive_summary: string;
  overall_financial_health_score: number;
  debt_analysis: DebtAnalysisResult;
  savings_analysis: SavingsAnalysisResult;
  budget_analysis: BudgetAnalysisResult;
  priority_recommendations: Recommendation[];
  recommendations: Recommendation[];
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export interface ReportListItemResponse {
  id: string;
  financial_profile_id: string;
  created_at: string;
}

export interface ReportListResponse {
  reports: ReportListItemResponse[];
}

export interface ReportDetailResponse {
  id: string;
  user_id: string;
  financial_profile_id: string;
  created_at: string;
  content: AICFOAnalysisResult;
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

/**
 * NOTE: docs/07_API_SPECIFICATION.md types the monetary fields as `number`.
 * The actual backend (schemas_ext/analysis.py -> DashboardResponse) is
 * Decimal-backed and serializes them as strings — confirmed by
 * backend/app/tests/test_dashboard.py. Typed as `string` here to match
 * real behavior.
 */
export interface DashboardResponse {
  user_id: string;
  total_monthly_income: string;
  total_monthly_expenses: string;
  total_debt: string;
  total_savings: string;
  savings_rate_percent: string;
  net_worth_estimate: string;
  latest_report_id: string | null;
  documents_processed: number;
  last_updated: string | null;
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export type ChatRole = 'user' | 'assistant';

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_history: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  financial_profile_id: string;
}