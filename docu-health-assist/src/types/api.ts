// types/api.ts

export interface Entity {
  text: string;
  label: string;
  confidence?: number;
  start?: number;
  end?: number;
}

export interface IcdCode {
  code: string;
  description: string;
  category?: string;
}

export interface AnalysisResponse {
  success: boolean;
  primary_diagnosis: string;
  prescribed_medication: string[];
  followup_instructions: string;
  medical_entities: Entity[];
  icd_codes: IcdCode[];
  error?: string;
}

export interface ApiError {
  message: string;
  status: number;
  data?: any;
}

export interface ChatResponse {
  success: boolean;
  message: string;
  timestamp: string;
  response?: string; // Alternative field name for backward compatibility
}

export interface MessageContext {
  role: string;
  content: string;
}

export interface ChatRequest {
  text: string;
  context?: MessageContext[];
}

// Blood test related types
export interface BloodTest {
  testName: string;
  value: number;
  unit: string;
  normalRange?: string;
  status?: 'normal' | 'high' | 'low' | 'critical';
  interpretation?: string;
}

export interface BloodAnalysisResponse {
  success: boolean;
  summary: {
    normalCount: number;
    abnormalCount: number;
    criticalCount: number;
  };
  tests: BloodTest[];
  recommendations?: string[];
  error?: string;
}

// Document upload types
export interface DocumentUploadResponse {
  success: boolean;
  filename: string;
  extractedText?: string;
  error?: string;
}

// Summary types
export interface SummaryResponse {
  success: boolean;
  bulletPoints: string[];
  keyFindings?: string[];
  error?: string;
}

// Report generation types
export interface ReportData {
  patientInfo?: {
    name: string;
    age: number;
    gender: string;
    id?: string;
  };
  testResults: any[];
  analysis: string;
  recommendations: string[];
}

export interface ReportResponse {
  success: boolean;
  reportId: string;
  reportUrl?: string;
  error?: string;
}