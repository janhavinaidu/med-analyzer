import React from 'react';
import { Card } from "@/components/ui/card";
import { Activity, Pill, FileText, TestTube, CheckCircle, XCircle } from 'lucide-react';

interface InsightsBarProps {
  data?: {
    entities: Array<{
      text: string;
      type: string;
      confidence: number;
    }>;
    icdCodes: Array<{
      code: string;
      description: string;
    }>;
  };
  bloodData?: {
    summary?: {
      normalCount: number;
      abnormalCount: number;
      criticalCount: number;
    };
    tests?: Array<any>;
  };
}

export const InsightsBar: React.FC<InsightsBarProps> = ({ data, bloodData }) => {
  // Medical document insights
  const diseaseCount = data?.entities?.filter(e => e.type.toLowerCase() === 'disease').length ?? 0;
  const medicationCount = data?.entities?.filter(e => e.type.toLowerCase() === 'medication').length ?? 0;
  const symptomCount = data?.entities?.filter(e => e.type.toLowerCase() === 'symptom').length ?? 0;
  const icdCount = data?.icdCodes?.length ?? 0;

  // Blood report insights
  const normalCount = bloodData?.summary?.normalCount ?? 0;
  const abnormalCount = bloodData?.summary?.abnormalCount ?? 0;
  const totalTests = bloodData?.tests?.length ?? 0;

  return (
    <Card className="mb-8 p-6 bg-gradient-to-r from-blue-50/90 to-green-50/90 backdrop-blur-sm border-blue-200/50 shadow-xl">
      <div className="flex items-center justify-center">
        <h3 className="text-lg font-semibold text-gray-900 mr-8 flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-600" />
          Insights at a Glance
        </h3>

        <div className="flex items-center gap-6 flex-wrap justify-center">
          {data && (
            <>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
                <span className="text-sm font-medium text-gray-700">{diseaseCount} Diagnoses</span>
              </div>

              <div className="flex items-center gap-2">
                <Pill className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium text-gray-700">{medicationCount} Medications</span>
              </div>

              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <span className="text-sm font-medium text-gray-700">{symptomCount} Symptoms</span>
              </div>

              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium text-gray-700">{icdCount} ICD Codes</span>
              </div>
            </>
          )}

          {bloodData?.summary && (
            <>
              <div className="flex items-center gap-2">
                <TestTube className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium text-gray-700">{totalTests} Tests</span>
              </div>

              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium text-gray-700">{normalCount} Normal</span>
              </div>

              <div className="flex items-center gap-2">
                <XCircle className="w-4 h-4 text-red-600" />
                <span className="text-sm font-medium text-gray-700">{abnormalCount} Abnormal</span>
              </div>
            </>
          )}
        </div>
      </div>
    </Card>
  );
};
