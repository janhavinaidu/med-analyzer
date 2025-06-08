import React from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ArrowUp, FileText, Upload, Stethoscope, Info, History, Pill } from 'lucide-react';
import { useToast } from "@/hooks/use-toast";

interface AnalysisResultsProps {
  data: {
    success: boolean;
    diagnosis: string[];
    clinical_treatment: string[];
    medical_history: string[];
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
  onReset: () => void;
}

export const AnalysisResults: React.FC<AnalysisResultsProps> = ({ data, onReset }) => {
  const { toast } = useToast();

  console.log('AnalysisResults rendered with data:', data);
  
  // Validate required data
  if (!data?.success) {
    console.error('Analysis failed:', data?.error);
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800">Error: {data?.error || 'Analysis failed'}</p>
      </div>
    );
  }

  const handleDownloadPDF = () => {
    // Animated feedback
    toast({
      title: "✅ PDF Generation Started",
      description: "Your comprehensive medical analysis report is being prepared...",
      className: "animate-scale-in",
    });
  };

  const getEntityBadgeStyle = (type: string) => {
    switch (type.toLowerCase()) {
      case 'disease':
        return 'bg-purple-100 text-purple-800 border-purple-300 hover:bg-purple-200 transition-colors';
      case 'medication':
        return 'bg-green-100 text-green-800 border-green-300 hover:bg-green-200 transition-colors';
      case 'symptom':
        return 'bg-red-100 text-red-800 border-red-300 hover:bg-red-200 transition-colors';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300 hover:bg-gray-200 transition-colors';
    }
  };

  const getEntityIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'disease':
        return '🔬';
      case 'medication':
        return '💊';
      case 'symptom':
        return '🔴';
      default:
        return '📋';
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
      {/* Enhanced Header */}
      <div className="flex flex-col lg:flex-row lg:justify-between lg:items-center gap-4 p-6 bg-white/70 backdrop-blur-sm rounded-2xl border border-gray-200/50 shadow-lg">
        <div>
          <h2 className="text-4xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <Stethoscope className="w-8 h-8 text-blue-600" />
            Medical Analysis Results
          </h2>
          <p className="text-lg text-gray-600 leading-relaxed">
            AI-powered medical document analysis with structured insights
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            onClick={handleDownloadPDF}
            className="h-12 px-6 bg-white/80 hover:bg-blue-50 border-blue-200 transition-all duration-300 hover:scale-105"
          >
            <Upload className="w-5 h-5 mr-2" />
            Download Report
          </Button>
          <Button 
            variant="outline" 
            onClick={onReset}
            className="h-12 px-6 bg-white/80 hover:bg-gray-50 transition-all duration-300 hover:scale-105"
          >
            <ArrowUp className="w-5 h-5 mr-2" />
            New Analysis
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Main Content - 2 Columns */}
        <div className="xl:col-span-2 space-y-8">
          {/* Diagnosis Section */}
          <Card className="border-2 border-purple-200 bg-gradient-to-br from-purple-50/50 to-white backdrop-blur-sm shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-purple-400/5 to-transparent pointer-events-none"></div>
            <CardHeader className="pb-6">
              <CardTitle className="text-2xl font-bold text-purple-900 flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <Stethoscope className="w-6 h-6 text-purple-600" />
                </div>
                Diagnosis & Clinical Findings
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {data.diagnosis.map((item, index) => (
                  <li key={index} className="flex items-start gap-3 p-3 bg-purple-50/50 rounded-lg border border-purple-100/50">
                    <span className="text-purple-800 mt-1">•</span>
                    <span className="text-gray-800">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Clinical Treatment Section */}
          <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50/50 to-white backdrop-blur-sm shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-400/5 to-transparent pointer-events-none"></div>
            <CardHeader className="pb-6">
              <CardTitle className="text-2xl font-bold text-blue-900 flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <Pill className="w-6 h-6 text-blue-600" />
                </div>
                Clinical Treatment
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {data.clinical_treatment.map((item, index) => (
                  <li key={index} className="flex items-start gap-3 p-3 bg-blue-50/50 rounded-lg border border-blue-100/50">
                    <span className="text-blue-800 mt-1">•</span>
                    <span className="text-gray-800">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Medical History Section */}
          <Card className="border-2 border-green-200 bg-gradient-to-br from-green-50/50 to-white backdrop-blur-sm shadow-2xl relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-green-400/5 to-transparent pointer-events-none"></div>
            <CardHeader className="pb-6">
              <CardTitle className="text-2xl font-bold text-green-900 flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <History className="w-6 h-6 text-green-600" />
                </div>
                Medical History
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {data.medical_history.map((item, index) => (
                  <li key={index} className="flex items-start gap-3 p-3 bg-green-50/50 rounded-lg border border-green-100/50">
                    <span className="text-green-800 mt-1">•</span>
                    <span className="text-gray-800">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - ICD Codes and Entities */}
        <div className="space-y-8">
          {/* ICD-10 Codes */}
          <Card className="bg-white/80 backdrop-blur-sm shadow-xl border-gray-200/50">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-gray-900 flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <span className="text-lg">🏥</span>
                </div>
                ICD-10 Classifications
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data.icd_codes.map((icd, index) => (
                  <div key={index} className="flex items-start gap-3 p-3 bg-gray-50/80 rounded-lg border border-gray-200/50">
                    <Badge variant="secondary" className="font-mono shrink-0">
                      {icd.code}
                    </Badge>
                    <span className="text-sm text-gray-800">{icd.description}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Medical Entities */}
          <Card className="bg-white/80 backdrop-blur-sm shadow-xl border-gray-200/50">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-gray-900 flex items-center gap-3">
                <div className="p-2 bg-indigo-100 rounded-lg">
                  <span className="text-lg">🔍</span>
                </div>
                Medical Entities
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {data.medical_entities.map((entity, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className={`text-sm px-3 py-1.5 flex items-center gap-1.5 ${getEntityBadgeStyle(entity.type)}`}
                  >
                    {getEntityIcon(entity.type)}
                    <span className="font-medium">{entity.text}</span>
                    <span className="text-xs opacity-75">({Math.round(entity.confidence * 100)}%)</span>
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
