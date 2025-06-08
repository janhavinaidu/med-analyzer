import React from 'react';
import { Card } from "@/components/ui/card";
import { Activity, Pill, FileText, TestTube, CheckCircle, XCircle } from 'lucide-react';

interface InsightsBarProps {
  data?: {
    success: boolean;
    primary_diagnosis: string;
    prescribed_medication: string[];
    followup_instructions: string;
    medical_entities: Array<{
      text: string;
      type: string;
      confidence: number;
    }>;
    icd_codes: Array<{
      code: string;
      description: string;
    }>;
    error?: string;
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
  const hasDiagnosis = data?.primary_diagnosis ? 1 : 0;
  const treatmentCount = data?.prescribed_medication?.length ?? 0;
  const hasHistory = data?.followup_instructions ? 1 : 0;
  const icdCount = data?.icd_codes?.length ?? 0;

  // Blood report insights
  const normalCount = bloodData?.summary?.normalCount ?? 0;
  const abnormalCount = bloodData?.summary?.abnormalCount ?? 0;
  const totalTests = bloodData?.tests?.length ?? 0;

  return (
    <Card className="mb-8 p-6 bg-gradient-to-r from-blue-50/90 to-green-50/90 backdrop-blur-sm border-blue-200/50 shadow-xl">
      <div className="flex flex-col gap-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
          <Activity className="w-5 h-5 text-blue-600" />
          Insights at a Glance
        </h3>

        {data && (
          <>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
              <span className="text-sm font-medium text-gray-700">
                {hasDiagnosis ? "Primary Diagnosis Found" : "No Primary Diagnosis"}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Pill className="w-4 h-4 text-green-600" />
              <span className="text-sm font-medium text-gray-700">{treatmentCount} Treatments</span>
            </div>

            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span className="text-sm font-medium text-gray-700">
                {hasHistory ? "Medical History Found" : "No Medical History"}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-medium text-gray-700">{icdCount} ICD Codes</span>
            </div>
          </>
        )}

        {bloodData && (
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
    </Card>
  );
};
