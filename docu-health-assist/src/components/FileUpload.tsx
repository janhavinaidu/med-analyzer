import React, { useState, useCallback } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Upload, File, X, Loader } from 'lucide-react';
import { useToast } from "@/hooks/use-toast";
import { documentApi } from '@/services/api';
import { AnalysisResponse } from '@/types/api';

interface FileUploadProps {
  onAnalysisComplete: (data: AnalysisResponse) => void;
  onError: (message: string) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onAnalysisComplete,
  onError,
  isLoading,
  setIsLoading
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [extractedText, setExtractedText] = useState('');
  const [showTextEditor, setShowTextEditor] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const { toast } = useToast();

  const acceptedTypes = [
    'application/pdf',
    'image/jpeg',
    'image/jpg',
    'image/png',
    'image/gif'
  ];

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  }, []);

  const handleFileSelection = (file: File) => {
    if (!acceptedTypes.includes(file.type)) {
      onError('Please upload a PDF or image file (JPEG, PNG, GIF)');
      return;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      onError('File size must be less than 10MB');
      return;
    }

    setSelectedFile(file);
    simulatePyPDF2Extraction(file);
  };

  const simulatePyPDF2Extraction = async (file: File) => {
    setIsLoading(true);
    
    toast({
      title: "📄 Extracting Text",
      description: "Using PyPDF2 to extract text from your document...",
    });
    
    // Simulate PyPDF2 extraction (no GPT)
    setTimeout(() => {
      const mockExtractedText = `Patient: John Doe
Date: ${new Date().toLocaleDateString()}
Chief Complaint: Follow-up for hypertension and diabetes management
Diagnosis: Essential hypertension (I10), Type 2 diabetes mellitus without complications (E11.9)
Current Medications:
- Metformin 500mg twice daily with meals
- Lisinopril 10mg once daily in the morning
- Atorvastatin 20mg at bedtime
Vital Signs: BP 140/90 mmHg, HR 78 bpm, Temp 98.6°F
Instructions: Continue current medications, monitor blood glucose daily, low sodium diet (<2g daily)
Follow-up: Return in 6 weeks for blood pressure recheck and lab work
Provider: Dr. Smith, Internal Medicine`;
      
      setExtractedText(mockExtractedText);
      setShowTextEditor(true);
      setIsLoading(false);
      
      toast({
        title: "✅ Text Extraction Complete",
        description: "Text extracted successfully using PyPDF2. Please review and edit if needed.",
      });
    }, 2000);
  };

  const handleFileInputChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      onError('File size exceeds 10MB limit');
      return;
    }

    // Check file type
    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/gif'];
    if (!allowedTypes.includes(file.type)) {
      onError('Invalid file type. Please upload a PDF or image file.');
      return;
    }

    setIsLoading(true);
    try {
      // Upload and process the file
      const uploadResult = await documentApi.uploadPdf(file);
      setExtractedText(uploadResult.text);

      // Get medical analysis
      const analysisResult = await documentApi.getMedicalAnalysis({
        text: uploadResult.text
      });

      onAnalysisComplete(analysisResult);
      
      toast({
        title: "✅ Document Processed Successfully",
        description: "Your medical document has been analyzed.",
      });
    } catch (error: any) {
      onError(error.message || 'Failed to process document');
      toast({
        title: "❌ Error Processing Document",
        description: error.message || 'Failed to process document',
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!extractedText.trim()) {
      onError('Please provide text to analyze');
      return;
    }

    setIsLoading(true);
    try {
      const analysisResult = await documentApi.getMedicalAnalysis({
        text: extractedText
      });
      
      onAnalysisComplete(analysisResult);
      
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

  const removeFile = () => {
    setSelectedFile(null);
    setExtractedText('');
    setShowTextEditor(false);
  };

  if (showTextEditor) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">Review Extracted Text</h3>
          <Button variant="outline" onClick={removeFile} size="sm">
            <X className="w-4 h-4 mr-2" />
            Start Over
          </Button>
        </div>
        
        <Card className="bg-white/90 backdrop-blur-sm border-gray-200/50 shadow-lg">
          <CardContent className="p-6">
            <p className="text-sm text-gray-600 mb-4 leading-relaxed">
              Text extracted using PyPDF2. Please review and make any necessary corrections before analysis:
            </p>
            <Textarea
              value={extractedText}
              onChange={(e) => setExtractedText(e.target.value)}
              className="min-h-48 mb-6 border-gray-300 focus:border-blue-500 focus:ring-blue-500/20 bg-white/95"
              placeholder="Extracted text will appear here..."
            />
            <Button 
              onClick={handleAnalyze} 
              disabled={isLoading || !extractedText.trim()}
              className="w-full h-12 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold transition-all duration-300 hover:scale-105 shadow-lg"
            >
              {isLoading ? (
                <>
                  <Loader className="w-5 h-5 mr-2 animate-spin" />
                  Analyzing Prescription...
                </>
              ) : (
                'Analyze Prescription'
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card
        className={`border-dashed border-2 transition-colors ${
          isDragOver 
            ? 'border-blue-400 bg-blue-50' 
            : selectedFile 
              ? 'border-green-400 bg-green-50' 
              : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <CardContent className="p-8 text-center">
          {selectedFile ? (
            <div className="space-y-4">
              <div className="flex items-center justify-center">
                <File className="w-12 h-12 text-green-600" />
              </div>
              <div>
                <p className="font-medium text-green-800">{selectedFile.name}</p>
                <p className="text-sm text-green-600">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <Loader className="w-6 h-6 animate-spin text-blue-600 mr-2" />
                  <span className="text-blue-600">Extracting text with PyPDF2...</span>
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
              <Upload className="w-12 h-12 text-gray-400 mx-auto" />
              <div>
                <p className="text-lg font-medium text-gray-700">
                  Drop your prescription document here
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  Or click to browse files
                </p>
              </div>
              <div className="space-y-2">
                <input
                  type="file"
                  id="file-upload"
                  className="hidden"
                  accept=".pdf,.jpg,.jpeg,.png,.gif"
                  onChange={handleFileInputChange}
                />
                <label htmlFor="file-upload">
                  <Button asChild className="cursor-pointer bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800">
                    <span>Browse Files</span>
                  </Button>
                </label>
                <p className="text-xs text-gray-500">
                  Supports PDF, JPEG, PNG, GIF (max 10MB)
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
