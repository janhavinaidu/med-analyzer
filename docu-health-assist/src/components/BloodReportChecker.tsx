import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Loader,
  TestTube,
  FileText,
  Download,
  ArrowUp,
  CheckCircle,
  XCircle,
  AlertCircle,
  Upload,
  File,
  X,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { bloodApi } from "@/services/api";
import { IcdCodesSection } from './IcdCodesSection';

// Interfaces
interface BloodTest {
  testName: string;
  value: number;
  unit: string;
  normalRange: string;
  status: 'normal' | 'high' | 'low';
  severity?: 'mild' | 'moderate' | 'severe';
  suggestion?: string;
}

interface BloodData {
  tests: BloodTest[];
  summary: {
    normalCount: number;
    abnormalCount: number;
    criticalCount: number;
  };
  interpretation: string;
  recommendations: string[];
  icd_codes?: Array<{
    code: string;
    description: string;
  }>;
}

interface BloodReportCheckerProps {
  onAnalysisComplete: (data: any) => void;
  onError: (error: string) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  results?: BloodData;
  onReset?: () => void;
}

export const BloodReportChecker: React.FC<BloodReportCheckerProps> = ({
  onAnalysisComplete,
  onError,
  isLoading,
  setIsLoading,
  results,
  onReset,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const { toast } = useToast();

  // Drag + Drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  };

  const handleFileSelection = async (file: File) => {
    if (file.type !== "application/pdf") {
      onError("Please upload a PDF file only");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      onError("File size must be less than 10MB");
      return;
    }

    setSelectedFile(file);
    analyzeReport(file);
  };

  const analyzeReport = async (file: File) => {
    setIsLoading(true);
    try {
      const analysisResult = await bloodApi.uploadReport(file);
      onAnalysisComplete(analysisResult);
      toast({
        title: "✅ Analysis Complete",
        description: "Your blood test results have been analyzed successfully.",
      });
    } catch (error: any) {
      const message = error?.message || "Failed to analyze blood test results";
      onError(message);
      toast({
        title: "❌ Analysis Failed",
        description: message,
        variant: "destructive",
      });
      setSelectedFile(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelection(files[0]);
    }
  };

  const removeFile = () => setSelectedFile(null);

  const handleDownloadPDF = async () => {
    if (!results) {
      toast({
        title: "❌ No Data",
        description: "No analysis results available to download.",
        variant: "destructive",
      });
      return;
    }

    setIsDownloading(true);
    try {
      // Prepare the data payload for the backend
      const reportData = {
        analysis_results: results,
        summary: {
          "Total Tests": results.tests.length.toString(),
          "Normal Results": results.summary.normalCount.toString(),
          "Abnormal Results": results.summary.abnormalCount.toString(),
          "Critical Results": results.summary.criticalCount.toString(),
          "Interpretation": results.interpretation
        },
        blood_tests: results.tests.map(test => ({
          test_name: test.testName,
          value: test.value,
          unit: test.unit,
          status: test.status,
          normal_range: test.normalRange,
          severity: test.severity || 'normal'
        })),
        icd_codes: results.icd_codes || [],
        entities: [] // Add if you have entity data
      };

      console.log("Sending report data:", reportData); // Debug log

      const response = await fetch("http://localhost:8000/api/reports/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(reportData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Get the blob from response
      const blob = await response.blob();
      console.log("Received blob size:", blob.size); // Debug log
      
      if (blob.size === 0) {
        throw new Error("Received empty PDF file");
      }
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Blood_Report_${new Date().toISOString().split('T')[0]}.pdf`;
      
      // Trigger download
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      console.log("Download triggered successfully"); // Debug log
      
      // Clean up
      window.URL.revokeObjectURL(url);

      toast({
        title: "✅ Download Successful",
        description: "Blood report PDF has been downloaded successfully.",
      });

    } catch (error: any) {
      console.error("Download error:", error);
      toast({
        title: "❌ Download Failed",
        description: error.message || "Could not download the blood report PDF.",
        variant: "destructive",
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const getStatusBadge = (status: string, severity?: string) => {
    const base = "font-semibold px-3 py-1 rounded-full text-sm";
    switch (status) {
      case "normal":
        return <Badge className={`${base} bg-green-100 text-green-800 border-green-300`}>✅ Normal</Badge>;
      case "high":
        const highColor = severity === "severe" ? "bg-red-200 text-red-900 border-red-400" : "bg-red-100 text-red-800 border-red-300";
        return <Badge className={`${base} ${highColor}`}>🔴 High</Badge>;
      case "low":
        const lowColor = severity === "severe" ? "bg-blue-200 text-blue-900 border-blue-400" : "bg-blue-100 text-blue-800 border-blue-300";
        return <Badge className={`${base} ${lowColor}`}>🔵 Low</Badge>;
      default:
        return null;
    }
  };

  // 🔍 Render result after analysis
  if (results) {
    const { tests, summary, interpretation, recommendations } = results;
    
    return (
      <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
        {/* Header */}
        <div className="flex flex-col lg:flex-row justify-between items-center gap-4 p-6 bg-white rounded-2xl border shadow">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              <TestTube className="text-green-600 w-8 h-8" />
              Blood Test Analysis
            </h2>
            <p className="text-gray-600 text-lg">Comprehensive blood test interpretation</p>
          </div>
          <div className="flex gap-3">
            <Button 
              onClick={handleDownloadPDF} 
              variant="outline"
              disabled={isDownloading}
            >
              {isDownloading ? (
                <>
                  <Loader className="mr-2 w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Download className="mr-2 w-4 h-4" />
                  Download Report
                </>
              )}
            </Button>
            <Button onClick={onReset} variant="outline">
              <ArrowUp className="mr-2 w-4 h-4" />
              New Analysis
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="bg-green-50 border-green-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-600" />
                Normal Tests
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold text-green-700">{summary.normalCount}</p>
            </CardContent>
          </Card>

          <Card className="bg-red-50 border-red-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <XCircle className="w-5 h-5 text-red-600" />
                Abnormal Tests
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold text-red-700">{summary.abnormalCount}</p>
            </CardContent>
          </Card>

          <Card className="bg-yellow-50 border-yellow-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-yellow-600" />
                Critical Tests
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold text-yellow-700">{summary.criticalCount}</p>
            </CardContent>
          </Card>
        </div>

        {/* Test Results Table */}
        <Card>
          <CardHeader>
            <CardTitle>Detailed Test Results</CardTitle>
            <CardDescription>
              Analysis of {tests.length} blood test parameters
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Test Name</TableHead>
                    <TableHead>Result</TableHead>
                    <TableHead>Normal Range</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tests.map((test, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">{test.testName}</TableCell>
                      <TableCell>
                        {test.value} {test.unit}
                      </TableCell>
                      <TableCell>{test.normalRange}</TableCell>
                      <TableCell>{getStatusBadge(test.status, test.severity)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        {/* Interpretation + Recommendations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="bg-blue-50 border-blue-200">
            <CardHeader>
              <CardTitle>Clinical Interpretation</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-800">{interpretation}</p>
            </CardContent>
          </Card>
          <Card className="bg-purple-50 border-purple-200">
            <CardHeader>
              <CardTitle>Recommendations</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-gray-800">
                {recommendations.map((rec, i) => (
                  <li key={i} className="flex gap-2 items-start">
                    <div className="w-2 h-2 bg-purple-500 rounded-full mt-2" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // 📤 Upload UI
  return (
    <Card className="bg-white border shadow-lg">
      <CardHeader>
        <CardTitle className="text-2xl font-bold flex items-center gap-2">
          <TestTube className="text-green-600" />
          Blood Report Checker
        </CardTitle>
        <CardDescription>Upload your blood test PDF for AI-powered analysis</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className={`p-8 border-2 border-dashed text-center rounded-xl transition-colors ${
            isDragOver ? "border-green-400 bg-green-50" : selectedFile ? "border-green-400 bg-green-50" : "border-gray-300"
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {selectedFile ? (
            <div className="space-y-4">
              <File className="w-10 h-10 mx-auto text-green-600" />
              <p className="text-green-800 font-semibold">{selectedFile.name}</p>
              <p className="text-sm text-green-600">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
              {isLoading ? (
                <div className="flex justify-center items-center gap-2 text-green-600">
                  <Loader className="w-4 h-4 animate-spin" />
                  Analyzing...
                </div>
              ) : (
                <Button variant="outline" onClick={removeFile}>
                  <X className="w-4 h-4 mr-2" />
                  Remove File
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <Upload className="w-10 h-10 text-gray-400 mx-auto" />
              <p className="text-lg font-medium text-gray-700">Drag & Drop your PDF</p>
              <p className="text-sm text-gray-500">Or browse below</p>
              <label htmlFor="blood-upload">
                <Button 
                  asChild
                  className="bg-green-500 hover:bg-green-600 text-white text-sm px-3 py-1.5 rounded inline-flex items-center gap-2"
                >
                  <span>Browse PDF File</span>
                </Button>
              </label>
              <input
                id="blood-upload"
                type="file"
                className="hidden"
                accept=".pdf"
                onChange={handleFileInputChange}
              />
              <p className="text-xs text-gray-400">Only PDF, max 10MB</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};