import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, Upload, MessageCircle, Sparkles } from 'lucide-react';
import { chatApi } from '@/services/api';
import { ChatResponse } from '@/types/api';

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

export const ChatBot: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: "👋 Hello! I'm your AI medical assistant. I can help explain your analysis results, clarify medical terms, or answer questions about your health information. How can I assist you today?",
      isUser: false,
      timestamp: new Date()
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasNewResponse, setHasNewResponse] = useState(false);

  const handleSendMessage = async () => {
    if (!inputText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      isUser: true,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      // Get context from previous messages (last 5 messages)
      const context = messages
        .slice(-5)
        .map(msg => ({
          role: msg.isUser ? 'user' : 'assistant',
          content: msg.text
        }));

      const response = await chatApi.sendMessage(inputText, context);
      
      const aiResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: response.message,
        isUser: false,
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, aiResponse]);
      
      // Trigger pulse effect for new response if chat is minimized
      if (!isOpen) {
        setHasNewResponse(true);
        setTimeout(() => setHasNewResponse(false), 3000);
      }
    } catch (error: any) {
      // Add error message to chat
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "I apologize, but I'm having trouble processing your request right now. Please try again.",
        isUser: false,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleOpen = () => {
    setIsOpen(true);
    setHasNewResponse(false);
  };

  if (!isOpen) {
    return (
      <div className="fixed bottom-8 right-8 z-50">
        <Button
          onClick={handleOpen}
          className={`h-16 w-16 rounded-full shadow-2xl bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 border-2 border-blue-200 transition-all duration-300 hover:scale-110 ${
            hasNewResponse ? 'animate-pulse ring-4 ring-blue-300/50' : ''
          }`}
          size="lg"
        >
          <div className="relative">
            <MessageCircle className="w-7 h-7 text-white" />
            {hasNewResponse && (
              <Sparkles className="w-4 h-4 text-yellow-300 absolute -top-1 -right-1 animate-pulse" />
            )}
          </div>
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-8 right-8 z-50 w-96 h-[36rem] max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)]">
      <Card className="h-full flex flex-col overflow-hidden shadow-2xl border-gray-200/50">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-t-lg">
          <CardTitle className="text-lg font-bold flex items-center gap-2">
            <div className="p-1 bg-white/20 rounded-lg">
              <MessageCircle className="h-5 w-5" />
            </div>
            Medical Assistant
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsOpen(false)}
            className="h-8 w-8 p-0 text-white hover:bg-white/20 rounded-full"
          >
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        
        <CardContent className="flex-1 overflow-hidden p-0">
          <ScrollArea className="h-[calc(100%-4rem)] px-4">
            <div className="space-y-4 py-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`rounded-lg px-4 py-2 max-w-[85%] ${
                      message.isUser
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    <p className="text-sm">{message.text}</p>
                    <p className="text-xs mt-1 opacity-70">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          <div className="p-4 border-t border-gray-200 bg-white/80 backdrop-blur-sm">
            <div className="flex space-x-2">
              <Input
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about your medical analysis..."
                disabled={isLoading}
                className="flex-1 border-gray-300 focus:border-blue-500 focus:ring-blue-500/20 bg-white/90"
              />
              <Button
                onClick={handleSendMessage}
                disabled={isLoading || !inputText.trim()}
                size="sm"
                className="px-4 bg-blue-600 hover:bg-blue-700 transition-all duration-300 hover:scale-105"
              >
                <Upload className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center leading-relaxed">
              Press Enter to send • AI assistant for medical information only
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
