import axios from 'axios';

const BASE_URL = 'http://localhost:8000/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error handler
const handleError = (error: any) => {
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

  analyzeText: async (text: string) => {
    try {
      const response = await api.post('/text/analyze', { text });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  getMedicalAnalysis: async (data: { text: string }) => {
    try {
      console.log('Sending analysis request with text:', data.text);
      const response = await api.post('/analysis/full', { text: data.text });
      console.log('Received analysis response:', response.data);

      if (response.data.success) {
        const transformedData = {
          summary: {
            diagnosis: response.data.entities
              .filter(e => e.type === 'DISEASE' || e.type === 'DIAGNOSIS')
              .map(e => e.text).join(', '),
            medications: response.data.entities
              .filter(e => e.type === 'MEDICATION' || e.type === 'DRUG')
              .map(e => e.text).join(', '),
            followUp: response.data.entities
              .filter(e => e.type === 'PROCEDURE' || e.type === 'TREATMENT')
              .map(e => e.text).join(', ')
          },
          entities: response.data.entities,
          icdCodes: response.data.icd_codes,
          originalText: response.data.originalText
        };

        return transformedData;
      } else {
        throw new Error(response.data.detail || 'Analysis failed');
      }
    } catch (error) {
      console.error('Error in getMedicalAnalysis:', error);
      handleError(error);
      throw error;
    }
  },

  getSummary: async (text: string) => {
    try {
      const response = await api.post('/summary/generate', { text });
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

      const data = {
        ...response.data,
        summary: {
          normalCount: 0,
          abnormalCount: 0,
          criticalCount: 0,
          ...(response.data.summary || {})
        },
        tests: response.data.tests || []
      };

      return data;
    } catch (error) {
      console.error('Blood analysis error:', error);
      handleError(error);
      throw error;
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

      const data = {
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

      return data;
    } catch (error) {
      console.error('Blood report upload error:', error);
      handleError(error);
      throw error;
    }
  }
};

export default {
  documentApi,
  chatApi,
  reportApi,
  bloodApi
};
