import React from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ArrowUp, FileText, Upload, Stethoscope, Info } from 'lucide-react';
import { useToast } from "@/hooks/use-toast";

interface AnalysisResultsProps {
  data: {
    summary: {
      diagnosis: string;
      medications: string;
      followUp: string;
    };
    entities: Array<{
      text: string;
      type: string;
      confidence: number;
    }>;
    icdCodes: Array<{
      code: string;
      description: string;
    }>;
    originalText: string;
  };
  onReset: () => void;
}

export const AnalysisResults: React.FC<AnalysisResultsProps> = ({ data, onReset }) => {
  const { toast } = useToast();

  console.log('AnalysisResults rendered with data:', data);
  
  // Validate required data
  if (!data?.summary) {
    console.error('Missing summary in analysis data:', data);
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800">Error: Analysis data is incomplete or missing</p>
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
            Analysis Results
          </h2>
          <p className="text-lg text-gray-600 leading-relaxed">
            AI-powered medical document analysis and clinical insights
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
        {/* Enhanced Main Summary - Larger with accent border */}
        <div className="xl:col-span-2 space-y-8">
          <Card className="border-2 border-blue-200 bg-gradient-to-br from-blue-50/50 to-white backdrop-blur-sm shadow-2xl relative overflow-hidden">
            {/* Glow effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-blue-400/5 to-transparent pointer-events-none"></div>
            
            <CardHeader className="pb-6">
              <CardTitle className="text-2xl font-bold text-blue-900 flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <FileText className="w-6 h-6 text-blue-600" />
                </div>
                Medical Summary
              </CardTitle>
              <CardDescription className="text-lg text-gray-600">
                Key clinical information extracted from your medical document
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="p-6 bg-green-50/80 rounded-xl border border-green-200/50">
                <h4 className="font-bold text-green-800 mb-3 text-lg flex items-center gap-2">
                  🩺 Primary Diagnosis
                </h4>
                <p className="text-gray-800 leading-relaxed text-base">{data.summary.diagnosis}</p>
              </div>
              
              <Separator className="my-6" />
              
              <div className="p-6 bg-blue-50/80 rounded-xl border border-blue-200/50">
                <h4 className="font-bold text-blue-800 mb-3 text-lg flex items-center gap-2">
                  💊 Prescribed Medications
                </h4>
                <p className="text-gray-800 leading-relaxed text-base">{data.summary.medications}</p>
              </div>
              
              <Separator className="my-6" />
              
              <div className="p-6 bg-purple-50/80 rounded-xl border border-purple-200/50">
                <h4 className="font-bold text-purple-800 mb-3 text-lg flex items-center gap-2">
                  📋 Follow-up Instructions
                </h4>
                <p className="text-gray-800 leading-relaxed text-base">{data.summary.followUp}</p>
              </div>
            </CardContent>
          </Card>

          {/* Enhanced ICD-10 Codes */}
          <Card className="bg-white/80 backdrop-blur-sm shadow-xl border-gray-200/50">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-gray-900 flex items-center gap-3">
                <div className="p-2 bg-orange-100 rounded-lg">
                  <span className="text-lg">🏥</span>
                </div>
                ICD-10 Disease Classifications
              </CardTitle>
              <CardDescription className="text-base text-gray-600">
                Standardized medical classification codes for identified conditions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data.icdCodes.map((icd, index) => (
                  <div key={index} className="flex items-start gap-4 p-5 bg-gray-50/80 rounded-xl border border-gray-200/50 hover:bg-gray-100/80 transition-colors">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">🏥</span>
                      <Badge variant="secondary" className="font-mono text-sm px-3 py-1">
                        {icd.code}
                      </Badge>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 leading-relaxed">{icd.description}</p>
                    </div>
                    <Info className="w-4 h-4 text-gray-400 mt-1 cursor-help" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Enhanced Sidebar */}
        <div className="space-y-8">
          {/* Enhanced Medical Entities with color coding */}
          <Card className="bg-white/80 backdrop-blur-sm shadow-xl border-gray-200/50">
            <CardHeader>
              <CardTitle className="text-xl font-bold text-gray-900 flex items-center gap-3">
                <div className="p-2 bg-indigo-100 rounded-lg">
                  <span className="text-lg">🔍</span>
                </div>
                Medical Entities
              </CardTitle>
              <CardDescription className="text-base text-gray-600">
                Identified medical terms with confidence scores
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {data.entities.map((entity, index) => (
                  <div key={index} className="flex items-center justify-between p-4 rounded-xl border border-gray-200/50 hover:shadow-md transition-all duration-300 bg-white/50">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{getEntityIcon(entity.type)}</span>
                      <Badge className={`${getEntityBadgeStyle(entity.type)} text-sm font-medium px-3 py-1`} variant="outline">
                        {entity.type}
                      </Badge>
                      <span className="text-sm font-medium text-gray-900">{entity.text}</span>
                    </div>
                    <Badge variant="secondary" className="text-xs text-gray-600 bg-gray-100">
                      {(entity.confidence * 100).toFixed(0)}%
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Enhanced Legend */}
          <Card className="bg-white/80 backdrop-blur-sm shadow-xl border-gray-200/50">
            <CardHeader>
              <CardTitle className="text-lg font-bold text-gray-900">Entity Color Guide</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                  <span className="text-base">🔴</span>
                  <div className="w-4 h-4 bg-red-100 border border-red-300 rounded-full"></div>
                  <span className="font-medium">Symptoms & Signs</span>
                </div>
                <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                  <span className="text-base">💊</span>
                  <div className="w-4 h-4 bg-green-100 border border-green-300 rounded-full"></div>
                  <span className="font-medium">Medications & Drugs</span>
                </div>
                <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                  <span className="text-base">🔬</span>
                  <div className="w-4 h-4 bg-purple-100 border border-purple-300 rounded-full"></div>
                  <span className="font-medium">Diseases & Conditions</span>
                </div>
                <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                  <span className="text-base">📋</span>
                  <div className="w-4 h-4 bg-gray-100 border border-gray-300 rounded-full"></div>
                  <span className="font-medium">Other Medical Terms</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
