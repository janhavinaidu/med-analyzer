import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { FileText } from 'lucide-react';

interface IcdCode {
  code: string;
  description: string;
}

interface IcdCodesSectionProps {
  icdCodes: IcdCode[];
  className?: string;
}

export const IcdCodesSection: React.FC<IcdCodesSectionProps> = ({ icdCodes, className = "" }) => {
  if (!icdCodes || icdCodes.length === 0) {
    return null;
  }

  return (
    <Card className={`border-2 border-orange-200 bg-gradient-to-br from-orange-50/50 to-white backdrop-blur-sm shadow-2xl relative overflow-hidden ${className}`}>
      <div className="absolute inset-0 bg-gradient-to-r from-orange-400/5 to-transparent pointer-events-none"></div>
      <CardHeader className="pb-6">
        <CardTitle className="text-2xl font-bold text-orange-900 flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-lg">
            <FileText className="w-6 h-6 text-orange-600" />
          </div>
          Identified ICD-10 Codes
        </CardTitle>
        <CardDescription className="text-orange-700">
          Standardized medical classification codes
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {icdCodes.map((icd, index) => (
            <div key={index} className="flex items-start gap-3 p-3 bg-orange-50/50 rounded-lg border border-orange-100/50">
              <Badge variant="secondary" className="font-mono shrink-0 bg-orange-100 text-orange-800">
                {icd.code}
              </Badge>
              <span className="text-gray-800">{icd.description}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}; 