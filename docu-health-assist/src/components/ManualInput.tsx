import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FileText, Sparkles } from 'lucide-react';
import { useToast } from "@/components/ui/use-toast";
import { documentApi } from '@/services/api';
import { AnalysisResponse } from '@/types/api';
import { Badge } from "@/components/ui/badge";
import { IcdCodesSection } from './IcdCodesSection'; // Import your ICD codes component

interface IcdCode {
  code: string;
  description: string;
}

interface ManualInputProps {
  onAnalysisComplete: (data: AnalysisResponse) => void;
  onError: (message: string) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export const ManualInput: React.FC<ManualInputProps> = ({
  onAnalysisComplete,
  onError,
  isLoading,
  setIsLoading
}) => {
  const [inputText, setInputText] = useState('');
  const [icdCodes, setIcdCodes] = useState<IcdCode[]>([]);
  const { toast } = useToast();

  const handleAnalyze = async () => {
    if (!inputText.trim()) {
      onError('Please enter medical text to analyze');
      return;
    }

    setIsLoading(true);
    try {
      // Get the medical analysis
      const medicalAnalysis = await documentApi.getMedicalAnalysis({
        text: inputText
      });
      
      // Update local ICD codes if available
      if (medicalAnalysis.icd_codes && medicalAnalysis.icd_codes.length > 0) {
        setIcdCodes(medicalAnalysis.icd_codes);
      }
      
      onAnalysisComplete(medicalAnalysis);
      
      toast({
        title: "✅ Analysis Complete",
        description: "Your medical text has been analyzed successfully.",
      });
    } catch (error: any) {
      onError(error.message || 'Failed to analyze text');
      toast({
        title: "❌ Analysis Failed",
        description: error.message || 'Failed to analyze text',
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCorrectText = async () => {
    if (!inputText.trim()) {
      onError('Please enter text to correct');
      return;
    }

    toast({
      title: "🔄 Text Correction Started",
      description: "AI is reviewing and correcting the entered text...",
    });

    try {
      const result = await documentApi.analyzeText(inputText);
      if (result.success) {
        // Update ICD codes if available
        if (result.icd_codes && result.icd_codes.length > 0) {
          setIcdCodes(result.icd_codes);
        }
      }
      
      toast({
        title: "✅ Text Corrected",
        description: "Text has been reviewed and corrected for medical terminology.",
      });
    } catch (error: any) {
      toast({
        title: "❌ Correction Failed",
        description: error.message || 'Failed to correct text',
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      <Card className="bg-white/90 backdrop-blur-sm border-gray-200/50 shadow-2xl">
        <CardHeader className="pb-6">
          <CardTitle className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <div className="p-3 bg-blue-100 rounded-xl">
              <FileText className="w-7 h-7 text-blue-600" />
            </div>
            Enter Medical Information
          </CardTitle>
          <CardDescription className="text-base text-gray-600 leading-relaxed">
            Type or paste your prescription, discharge notes, or other medical documentation below for AI analysis
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          <div className="relative">
            <Textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter your medical text here... For example:

Patient: John Doe
Date: 12/01/2024
Chief Complaint: Follow-up for hypertension
Diagnosis: Essential hypertension (I10)
Current Medications: Lisinopril 10mg daily
Blood Pressure: 140/90 mmHg
Plan: Continue current medication, lifestyle modifications
Follow-up: 6 weeks for BP recheck"
              className="min-h-[300px] resize-y text-base leading-relaxed border-gray-300 focus:border-blue-500 focus:ring-blue-500/20 bg-white/95 backdrop-blur-sm transition-all duration-300"
            />
            {inputText.length > 50 && (
              <div className="absolute top-3 right-3">
                <Sparkles className="w-5 h-5 text-blue-400 animate-pulse" />
              </div>
            )}
          </div>
          
          <div className="flex gap-4 justify-end">
            <Button
              variant="outline"
              onClick={handleCorrectText}
              disabled={isLoading || !inputText.trim()}
              className="bg-white hover:bg-gray-50"
            >
              Correct Text
            </Button>
            <Button
              onClick={handleAnalyze}
              disabled={isLoading || !inputText.trim()}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              {isLoading ? 'Analyzing...' : 'Analyze Text'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* ADD THIS: Display ICD Codes Section */}
      {icdCodes.length > 0 && (
        <IcdCodesSection icdCodes={icdCodes} />
      )}
    </div>
  );
};