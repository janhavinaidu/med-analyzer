import React, { useState, useCallback } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Upload, File, X, Loader, FileText } from 'lucide-react';
import { useToast } from "@/hooks/use-toast";
import { documentApi } from '@/services/api';
import { AnalysisResponse } from '@/types/api';
import { Badge } from "@/components/ui/badge";

interface IcdCode {
  code: string;
  description: string;
}

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
  const [icdCodes, setIcdCodes] = useState<IcdCode[]>([]);
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

  const handleFileSelection = async (file: File) => {
    if (!acceptedTypes.includes(file.type)) {
      onError('Please upload a PDF or image file (JPEG, PNG, GIF)');
      return;
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      onError('File size must be less than 10MB');
      return;
    }

    setSelectedFile(file);
    setIsLoading(true);
    try {
      // Upload and process the file
      const uploadResult = await documentApi.uploadPdf(file);
      setExtractedText(uploadResult.text);
      setShowTextEditor(true);

      // Get initial ICD codes
      const analysisResult = await documentApi.analyzeText(uploadResult.text);
      if (analysisResult.icd_codes && analysisResult.icd_codes.length > 0) {
        setIcdCodes(analysisResult.icd_codes);
      }

      toast({
        title: "✅ Text Extraction Complete",
        description: "Text extracted successfully. Please review and edit if needed.",
      });
    } catch (error: any) {
      onError(error.message || 'Failed to process file');
      toast({
        title: "❌ File Processing Failed",
        description: error.message || 'Failed to process file',
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
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

    handleFileSelection(file);
  };

  const handleAnalyze = async () => {
    if (!extractedText.trim()) {
      onError('Please provide text to analyze');
      return;
    }

    setIsLoading(true);
    try {
      // Get medical analysis
      const analysisResult = await documentApi.getMedicalAnalysis({
        text: extractedText
      });
      
      // Update local ICD codes if available
      if (analysisResult.icd_codes && analysisResult.icd_codes.length > 0) {
        setIcdCodes(analysisResult.icd_codes);
      }
      
      onAnalysisComplete(analysisResult);
      
      toast({
        title: "✅ Analysis Complete",
        description: "Your medical document has been analyzed.",
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
    setIcdCodes([]);
  };

  return (
    <div className="space-y-6">
      {!showTextEditor ? (
        <Card
          className="border-2 border-dashed border-gray-300 hover:border-blue-500 transition-colors duration-200 relative overflow-hidden"
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input
            type="file"
            id="fileInput"
            className="hidden"
            accept=".pdf,.jpg,.jpeg,.png,.gif"
            onChange={handleFileInputChange}
            disabled={isLoading}
          />
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Upload className="w-12 h-12 text-gray-400 mb-4" />
            <p className="text-lg font-medium text-gray-700 mb-2">
              Drop your medical document here
            </p>
            <p className="text-sm text-gray-500 mb-6">
              Supported formats: PDF, JPEG, PNG, GIF
            </p>
            <Button
              onClick={(e) => {
                e.stopPropagation();
                document.getElementById('fileInput')?.click();
              }}
              className="bg-blue-500 hover:bg-blue-600 text-white font-semibold px-6 py-2 rounded-lg flex items-center gap-2 transition-colors duration-200"
              disabled={isLoading}
            >
              <Upload className="w-5 h-5" />
              {isLoading ? 'Uploading...' : 'Upload Document'}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card className="relative">
            <CardHeader>
              <CardTitle>Extracted Text</CardTitle>
              <CardDescription>Review and edit the extracted text if needed</CardDescription>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="absolute top-4 right-4 flex gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={removeFile}
                  className="h-8 w-8"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <Textarea
                value={extractedText}
                onChange={(e) => setExtractedText(e.target.value)}
                className="min-h-[300px] font-mono text-sm"
                placeholder="Extracted text will appear here..."
              />
              <div className="flex justify-end mt-4">
                <Button
                  onClick={handleAnalyze}
                  disabled={isLoading || !extractedText.trim()}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {isLoading ? (
                    <>
                      <Loader className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    'Analyze Document'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

        
         
        </>
      )}
    </div>
  );
};
