import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileUpload } from '@/components/FileUpload';
import { ManualInput } from '@/components/ManualInput';
import { AnalysisResults } from '@/components/AnalysisResults';
import { BloodReportChecker } from '@/components/BloodReportChecker';
import { ChatBot } from '@/components/ChatBot';
import { InsightsBar } from '@/components/InsightsBar';
import { FileText, Upload, Stethoscope, TestTube } from 'lucide-react';

const Index = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [analysisData, setAnalysisData] = useState(null);
  const [bloodReportData, setBloodReportData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAnalysisComplete = (data) => {
    console.log('Analysis completed with data:', data);
    setAnalysisData(data);
    setIsLoading(false);
  };

  const handleBloodReportComplete = (data) => {
    setBloodReportData(data);
    setIsLoading(false);
  };

  const handleError = (errorMessage) => {
    console.error('Analysis error:', errorMessage);
    setError(errorMessage);
    setIsLoading(false);
  };

  const resetAnalysis = () => {
    console.log('Resetting analysis data');
    setAnalysisData(null);
    setBloodReportData(null);
    setError('');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50/40 via-white to-green-50/30">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Enhanced Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="p-4 bg-blue-100/80 rounded-3xl shadow-lg backdrop-blur-sm">
              <Stethoscope className="w-10 h-10 text-blue-600" />
            </div>
            <h1 className="text-6xl font-bold text-gray-900 tracking-tight bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent">
              MedAnalyzer Pro
            </h1>
          </div>
          <p className="text-xl text-gray-600 max-w-4xl mx-auto leading-relaxed font-medium">
            Advanced AI-powered medical document analysis with ICD-10 coding, entity extraction, 
            and comprehensive blood test interpretation for healthcare professionals.
          </p>
        </div>

        {/* Insights Bar - Only show when analysis is complete */}
        {(analysisData || bloodReportData) && (
          <InsightsBar 
            data={analysisData} 
            bloodData={bloodReportData} 
          />
        )}

        {!analysisData && !bloodReportData ? (
          <Card className="max-w-6xl mx-auto shadow-2xl border-0 bg-white/80 backdrop-blur-lg">
            <CardHeader className="text-center pb-8 pt-10">
              <CardTitle className="text-4xl font-bold text-gray-900 mb-4">
                Choose Analysis Type
              </CardTitle>
              <CardDescription className="text-lg text-gray-600 leading-relaxed max-w-3xl mx-auto">
                Select your preferred input method for medical document analysis or blood report checking
              </CardDescription>
            </CardHeader>
            <CardContent className="px-10 pb-10">
              <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full grid-cols-3 mb-10 h-16 bg-gray-100/90 p-1.5 rounded-2xl">
                  <TabsTrigger 
                    value="upload" 
                    className="flex items-center gap-3 text-base font-semibold transition-all duration-300 hover:scale-105 data-[state=active]:bg-white data-[state=active]:shadow-lg data-[state=active]:text-blue-600 rounded-xl"
                  >
                    <Upload className="w-5 h-5" />
                    Document Upload
                  </TabsTrigger>
                  <TabsTrigger 
                    value="manual" 
                    className="flex items-center gap-3 text-base font-semibold transition-all duration-300 hover:scale-105 data-[state=active]:bg-white data-[state=active]:shadow-lg data-[state=active]:text-blue-600 rounded-xl"
                  >
                    <FileText className="w-5 h-5" />
                    Manual Entry
                  </TabsTrigger>
                  <TabsTrigger 
                    value="bloodreport" 
                    className="flex items-center gap-3 text-base font-semibold transition-all duration-300 hover:scale-105 data-[state=active]:bg-white data-[state=active]:shadow-lg data-[state=active]:text-green-600 rounded-xl"
                  >
                    <TestTube className="w-5 h-5" />
                    Blood Report
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="upload" className="mt-10">
                  <FileUpload
                    onAnalysisComplete={handleAnalysisComplete}
                    onError={handleError}
                    isLoading={isLoading}
                    setIsLoading={setIsLoading}
                  />
                </TabsContent>

                <TabsContent value="manual" className="mt-10">
                  <ManualInput
                    onAnalysisComplete={handleAnalysisComplete}
                    onError={handleError}
                    isLoading={isLoading}
                    setIsLoading={setIsLoading}
                  />
                </TabsContent>

                <TabsContent value="bloodreport" className="mt-10">
                  <BloodReportChecker
                    onAnalysisComplete={handleBloodReportComplete}
                    onError={handleError}
                    isLoading={isLoading}
                    setIsLoading={setIsLoading}
                  />
                </TabsContent>
              </Tabs>

              {error && (
                <div className="mt-8 p-6 bg-red-50/90 backdrop-blur-sm border-2 border-red-200/50 rounded-2xl animate-fade-in shadow-lg">
                  <p className="text-red-800 text-center font-semibold text-lg">{error}</p>
                </div>
              )}
            </CardContent>
          </Card>
        ) : (
          <>
            {analysisData && (
              <AnalysisResults 
                data={analysisData} 
                onReset={resetAnalysis}
              />
            )}
            {bloodReportData && (
              <div className="max-w-7xl mx-auto">
                <BloodReportChecker
                  onAnalysisComplete={handleBloodReportComplete}
                  onError={handleError}
                  isLoading={isLoading}
                  setIsLoading={setIsLoading}
                  results={bloodReportData}
                  onReset={resetAnalysis}
                />
              </div>
            )}
          </>
        )}

        <ChatBot />
      </div>
    </div>
  );
};

export default Index;
