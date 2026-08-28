export interface CompanyBrief {
  id: string;
  name: string;
  slug: string;
  logo_url?: string | null;
}

export interface MatchScore {
  score: number;
  reasoning: string;
  missing_skills: string[];
  interview_likelihood: string;
  difficulty: string;
  ats_compatibility: number;
  expected_salary_estimate?: string | null;
}

export interface Job {
  id: string;
  title: string;
  location?: string | null;
  work_mode: "remote" | "hybrid" | "onsite" | "unknown";
  department?: string | null;
  seniority?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  visa_sponsorship?: boolean | null;
  tags?: string[] | null;
  apply_url: string;
  posted_at?: string | null;
  ats_provider: string;
  company: CompanyBrief;
  match?: MatchScore | null;
}

export interface PaginatedJobs {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// --- Resume Intelligence (Sprint 2) ---

export interface ResumeContact {
  full_name: string;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  github_url?: string | null;
  linkedin_url?: string | null;
  portfolio_url?: string | null;
}

export interface ResumeExperienceEntry {
  company: string;
  title: string;
  start_date?: string | null;
  end_date?: string | null;
  location?: string | null;
  bullets: string[];
}

export interface ResumeEducationEntry {
  institution: string;
  degree?: string | null;
  field_of_study?: string | null;
  start_date?: string | null;
  end_date?: string | null;
}

export interface ResumeProjectEntry {
  name: string;
  description?: string | null;
  bullets: string[];
  tech_stack: string[];
  url?: string | null;
}

export interface ResumeContent {
  contact: ResumeContact;
  summary?: string | null;
  skills: string[];
  experience: ResumeExperienceEntry[];
  education: ResumeEducationEntry[];
  projects: ResumeProjectEntry[];
  achievements: string[];
  languages: string[];
}

export type ParseStatus = "pending" | "parsed" | "failed";

export interface Resume {
  id: string;
  label: string;
  is_primary: boolean;
  version: number;
  parent_resume_id?: string | null;
  parse_status: ParseStatus;
  content: ResumeContent;
  created_at: string;
  updated_at: string;
}

export interface ResumeAnalysis {
  id: string;
  resume_id: string;
  created_at: string;
  ats_score: number;
  extracted_skills: string[];
  missing_skills_by_role?: string[] | null;
  strengths: string[];
  weaknesses: string[];
}

export type DocumentFormat = "pdf" | "docx";
export type DocumentType = "tailored_resume" | "cover_letter";

export interface AppDocument {
  id: string;
  document_type: DocumentType;
  document_format: DocumentFormat;
  storage_path: string;
  created_at: string;
}

// --- Applications + Interview Prep (Sprint 3) ---

export type ApplicationStatus =
  | "saved"
  | "applied"
  | "oa"
  | "interview"
  | "offer"
  | "accepted"
  | "rejected"
  | "withdrawn";

export interface Application {
  id: string;
  status: ApplicationStatus;
  applied_at?: string | null;
  notes?: string | null;
  created_at: string;
  job: Job;
}

export interface InterviewPrep {
  id: string;
  application_id: string;
  created_at: string;
  updated_at: string;
  company_summary: string;
  latest_news: string[];
  tech_stack: string[];
  likely_rounds: string[];
  behavioral_questions: string[];
  coding_questions: string[];
  system_design_questions: string[];
  frontend_questions: string[];
  lld_questions: string[];
  hld_questions: string[];
}
