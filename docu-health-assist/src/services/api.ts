import axios from 'axios';
import { 
  AnalysisResponse, 
  Entity, 
  IcdCode, 
  ApiError, 
  ChatResponse,
  MessageContext,
  BloodAnalysisResponse,
  DocumentUploadResponse,
  SummaryResponse
} from '@/types/api';

const BASE_URL = 'http://localhost:8000/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error handler with improved typing
const handleError = (error: any): never => {
  console.error('API Error:', error);
  
  if (error.response) {
    throw {
      message: error.response.data.detail || 'An error occurred',
      status: error.response.status,
      data: error.response.data
    };
  } else if (error.request) {
    throw {
      message: 'Server not responding. Please try again later.',
      status: 503
    };
  } else {
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

  analyzeText: async (text: string): Promise<AnalysisResponse> => {
    try {
      const response = await api.post('/summary/structured-analysis', { text });
      
      // Add ICD codes
      const icdResponse = await api.post('/icd/analyze', { text });
      console.log('ICD Response:', icdResponse.data);
      
      const result = {
        ...response.data,
        icd_codes: icdResponse.data.icd_codes || []
      };
      console.log('Combined Result:', result);
      return result;
    } catch (error) {
      console.error('Error analyzing text:', error);
      return {
        success: false,
        primary_diagnosis: '',
        prescribed_medication: [],
        followup_instructions: '',
        medical_entities: [],
        icd_codes: [],
        error: error instanceof Error ? error.message : 'Failed to analyze text'
      };
    }
  },

  getMedicalAnalysis: async (data: { text: string }): Promise<AnalysisResponse> => {
    try {
      console.log('Analyzing text:', data.text.substring(0, 100) + '...');
      const response = await api.post('/summary/structured-analysis', { text: data.text });
      
      // Add ICD codes
      const icdResponse = await api.post('/icd/analyze', { text: data.text });
      console.log('ICD Response:', icdResponse.data);
      
      if (!response.data || !response.data.success) {
        throw new Error(response.data?.error || 'Analysis failed');
      }

      const result: AnalysisResponse = {
        success: true,
        primary_diagnosis: response.data.primary_diagnosis || '',
        prescribed_medication: response.data.prescribed_medication || [],
        followup_instructions: response.data.followup_instructions || '',
        medical_entities: response.data.medical_entities || [],
        icd_codes: icdResponse.data.icd_codes || [],
        error: response.data.error
      };
      console.log('Final Analysis Result:', result);
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
  sendMessage: async (message: string, context?: MessageContext[]): Promise<ChatResponse> => {
    try {
      console.log('Sending chat message:', message);
      console.log('With context:', context);
      
      const response = await api.post('/chat/message', { 
        text: message, 
        context: context?.map((msg: MessageContext) => ({
          role: msg.role,
          content: msg.content
        }))
      });
      
      console.log('Chat API response:', response.data);
      
      if (response.data.success && response.data.message) {
        return response.data;
      } else if (response.data.response) {
        return {
          success: true,
          message: response.data.response,
          timestamp: response.data.timestamp || new Date().toISOString()
        };
      } else {
        throw new Error('Invalid response format from chat API');
      }
    } catch (error) {
      console.error('Chat API error:', error);
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

      return response.data;
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
