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
  diagnosis: string;
  medications: string;
  followUp: string;
}

export interface AnalysisResponse {
  summary: Summary;
  entities: Entity[];
  icdCodes: IcdCode[];
  originalText: string;
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