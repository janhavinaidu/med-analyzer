export interface Entity {
  text: string;
  type: string;
  confidence: number;
}

export interface IcdCode {
  code: string;
  description: string;
}

export interface Summary {
  primary_diagnosis: string;
  prescribed_medication: string[];
  followup_instructions: string;
}

export interface BloodTest {
  testName: string;
  value: number;
  unit: string;
  normalRange: string;
  status: 'normal' | 'high' | 'low';
  severity?: 'mild' | 'moderate' | 'severe';
  suggestion?: string;
}

export interface BloodData {
  tests: BloodTest[];
  summary: {
    normalCount: number;
    abnormalCount: number;
    criticalCount: number;
  };
  interpretation: string;
  recommendations: string[];
}

export interface AnalysisResponse {
  success: boolean;
  primary_diagnosis: string;
  prescribed_medication: string[];
  followup_instructions: string;
  medical_entities: Entity[];
  icd_codes: IcdCode[];
  error?: string;
  blood_data?: BloodData;
}

export interface ChatResponse {
  message: string;
  context?: any;
}

export interface BloodReportAnalysis {
  parameters: {
    name: string;
    value: number;
    unit: string;
    normalRange: string;
    status: 'normal' | 'high' | 'low';
    interpretation?: string;
  }[];
  summary: string;
  recommendations: string[];
}

export interface ApiError {
  message: string;
  status: number;
  data?: any;
} 