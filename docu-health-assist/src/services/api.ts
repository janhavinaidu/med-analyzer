import axios from 'axios';

const BASE_URL = 'http://localhost:8000/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Type definitions for medical analysis
interface MedicalAnalysisResponse {
  success: boolean;
  diagnosis: string[];
  clinical_treatment: string[];
  medical_history: string[];
  medical_entities?: Array<{
    text: string;
    type: string;
    confidence: number;
  }>;
  icd_codes?: Array<{
    code: string;
    description: string;
  }>;
  error?: string;
}

// Error handler with improved typing
const handleError = (error: any): never => {
  console.error('API Error:', error);
  
  if (error.response) {
    // Server responded with error
    throw {
      message: error.response.data.detail || 'An error occurred',
      status: error.response.status,
      data: error.response.data
    };
  } else if (error.request) {
    // Request made but no response
    throw {
      message: 'Server not responding. Please try again later.',
      status: 503
    };
  } else {
    // Something else went wrong
    throw {
      message: error.message || 'An unexpected error occurred',
      status: 500
    };
  }
};

// API endpoints
export const documentApi = {
  uploadPdf: async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await api.post('/pdf/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  analyzeText: async (text: string) => {
    try {
      const response = await api.post('/text/analyze', { text });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  getMedicalAnalysis: async (data: { text: string }): Promise<MedicalAnalysisResponse> => {
    try {
      console.log('Sending structured analysis request:', data.text.substring(0, 100) + '...');
      
      // Call the new structured-analysis endpoint
      const response = await api.post('/summary/structured-analysis', { text: data.text });
      console.log('Received structured analysis response:', response.data);

      if (!response.data || !response.data.success) {
        throw new Error(response.data?.error || 'Analysis failed');
      }

      // Ensure all required fields are present with defaults
      const result: MedicalAnalysisResponse = {
        success: true,
        diagnosis: response.data.diagnosis || [],
        clinical_treatment: response.data.clinical_treatment || [],
        medical_history: response.data.medical_history || [],
        medical_entities: response.data.medical_entities || [],
        icd_codes: response.data.icd_codes || []
      };

      return result;
    } catch (error) {
      console.error('Error in getMedicalAnalysis:', error);
      throw handleError(error);
    }
  },

  getSummary: async (text: string) => {
    try {
      const response = await api.post('/summary/bullet-points', { text });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  }
};

export const chatApi = {
  sendMessage: async (message: string, context?: any) => {
    try {
      const response = await api.post('/chat/message', { message, context });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  }
};

export const reportApi = {
  analyzeBloodReport: async (data: any) => {
    try {
      const response = await api.post('/report/blood-analysis', data);
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  generateReport: async (data: any) => {
    try {
      const response = await api.post('/report/generate', data);
      return response.data;
    } catch (error) {
      handleError(error);
    }
  }
};

export const bloodApi = {
  analyzeTests: async (tests: Array<{ testName: string, value: number, unit: string }>) => {
    try {
      const response = await api.post('/blood/analyze', { tests });
      console.log('Blood analysis response:', response.data);

      if (!response.data || typeof response.data !== 'object') {
        throw new Error('Invalid response format from server');
      }

      return {
        ...response.data,
        summary: {
          normalCount: 0,
          abnormalCount: 0,
          criticalCount: 0,
          ...(response.data.summary || {})
        },
        tests: response.data.tests || []
      };
    } catch (error) {
      console.error('Blood analysis error:', error);
      throw handleError(error);
    }
  },

  uploadReport: async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      console.log('Uploading blood report:', file.name);
      const response = await api.post('/blood/upload-blood-report', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      console.log('Blood report upload response:', response.data);

      if (!response.data || typeof response.data !== 'object') {
        throw new Error('Invalid response format from server');
      }

      return {
        tests: response.data.tests || [],
        interpretation: response.data.interpretation || '',
        recommendations: response.data.recommendations || [],
        summary: {
          normalCount: 0,
          abnormalCount: 0,
          criticalCount: 0,
          ...(response.data.summary || {})
        }
      };
    } catch (error) {
      console.error('Blood report upload error:', error);
      throw handleError(error);
    }
  }
};

export default {
  documentApi,
  chatApi,
  reportApi,
  bloodApi
};
