'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Wrench,
  Brain,
  Crown,
  FileText,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  Loader2
} from 'lucide-react';

interface ModelInfo {
  id: string;
  display_name: string;
  supports_tools: boolean;
  supports_streaming: boolean;
  context_window: number;
  best_for: string;
  cost_per_1m: number;
  tier: 'free' | 'paid';
}

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (modelId: string) => void;
  isLoading?: boolean;
}

export function ModelSelector({ selectedModel, onModelChange, isLoading = false }: ModelSelectorProps) {
  const [models, setModels] = useState<{
    free_tool_models: ModelInfo[];
    free_reasoning_models: ModelInfo[];
    paid_models: ModelInfo[];
  }>({
    free_tool_models: [],
    free_reasoning_models: [],
    paid_models: []
  });
  const [currentModelInfo, setCurrentModelInfo] = useState<ModelInfo | null>(null);

  // Load models from API
  useEffect(() => {
    const loadModels = async () => {
      try {
        const response = await fetch('/api/models');
        if (response.ok) {
          const data = await response.json();
          setModels(data);
        }
      } catch (error) {
        console.error('Failed to load models:', error);
      }
    };
    loadModels();
  }, []);

  // Load current model info
  useEffect(() => {
    const loadModelInfo = async () => {
      if (!selectedModel) return;
      try {
        const response = await fetch(`/api/models/${encodeURIComponent(selectedModel)}/capabilities`);
        if (response.ok) {
          const data = await response.json();
          setCurrentModelInfo(data);
        }
      } catch (error) {
        console.error('Failed to load model info:', error);
      }
    };
    loadModelInfo();
  }, [selectedModel]);

  const formatContextWindow = (tokens: number) => {
    if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`;
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(0)}K`;
    return tokens.toString();
  };

  const getTierIcon = (tier: string) => {
    switch (tier) {
      case 'free': return '🆓';
      case 'paid': return '💎';
      default: return '🤔';
    }
  };

  const getToolSupportBadge = (supportsTools: boolean) => {
    return supportsTools ? (
      <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
        <CheckCircle className="w-3 h-3 mr-1" />
        🔧 Tool Calling Supported
      </Badge>
    ) : (
      <Badge variant="secondary" className="bg-orange-100 text-orange-800 border-orange-200">
        <AlertTriangle className="w-3 h-3 mr-1" />
        No Tool Support (Reasoning Only)
      </Badge>
    );
  };

  return (
    <div className="space-y-4">
      {/* Model Selector */}
      <div className="flex items-center gap-4">
        <label className="text-sm font-medium text-gray-700">AI Model:</label>
        <Select value={selectedModel} onValueChange={onModelChange} disabled={isLoading}>
          <SelectTrigger className="w-80">
            <SelectValue placeholder="Select a model..." />
          </SelectTrigger>
          <SelectContent>
            {/* Free Tool Models */}
            <div className="px-2 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">
              🆓 Free Models (Tool Support)
            </div>
            {models.free_tool_models.map((model) => (
              <SelectItem key={model.id} value={model.id}>
                <div className="flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-green-600" />
                  <span>{model.display_name}</span>
                  <Badge variant="outline" className="text-xs">
                    {formatContextWindow(model.context_window)}
                  </Badge>
                </div>
              </SelectItem>
            ))}

            {/* Free Reasoning Models */}
            <div className="px-2 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wide border-t mt-2 pt-2">
              🧠 Free Models (Reasoning Only)
            </div>
            {models.free_reasoning_models.map((model) => (
              <SelectItem key={model.id} value={model.id}>
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-orange-600" />
                  <span>{model.display_name}</span>
                  <Badge variant="outline" className="text-xs">
                    {formatContextWindow(model.context_window)}
                  </Badge>
                </div>
              </SelectItem>
            ))}

            {/* Paid Models */}
            <div className="px-2 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wide border-t mt-2 pt-2">
              💎 Paid Models
            </div>
            {models.paid_models.map((model) => (
              <SelectItem key={model.id} value={model.id}>
                <div className="flex items-center gap-2">
                  <Crown className="w-4 h-4 text-purple-600" />
                  <span>{model.display_name}</span>
                  <Badge variant="outline" className="text-xs">
                    {formatContextWindow(model.context_window)}
                  </Badge>
                  <Badge variant="outline" className="text-xs text-green-600">
                    ${model.cost_per_1m}/1M
                  </Badge>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {isLoading && <Loader2 className="w-4 h-4 animate-spin text-gray-500" />}
      </div>

      {/* Model Info Card */}
      {currentModelInfo && (
        <Card className="p-4 bg-gray-50">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-semibold text-lg">
                  {getTierIcon(currentModelInfo.tier)} {currentModelInfo.display_name}
                </h3>
                {getToolSupportBadge(currentModelInfo.supports_tools)}
              </div>

              <div className="flex flex-wrap gap-2 mb-3">
                <Badge variant="outline">
                  <FileText className="w-3 h-3 mr-1" />
                  {formatContextWindow(currentModelInfo.context_window)} context
                </Badge>
                {currentModelInfo.tier === 'paid' && (
                  <Badge variant="outline">
                    <DollarSign className="w-3 h-3 mr-1" />
                    ${currentModelInfo.cost_per_1m}/1M tokens
                  </Badge>
                )}
              </div>

              <p className="text-sm text-gray-600 mb-3">
                <strong>Best for:</strong> {currentModelInfo.best_for}
              </p>
            </div>
          </div>

          {/* Warning for non-tool models */}
          {!currentModelInfo.supports_tools && (
            <Alert className="mt-3 border-orange-200 bg-orange-50">
              <AlertTriangle className="h-4 w-4 text-orange-600" />
              <AlertDescription className="text-orange-800">
                <strong>Warning:</strong> This model doesn't support tool calling. Switch to a tool-capable model
                (Qwen3 Next 80B, Trinity Large, DeepSeek V3, Devstral 2, Nemotron 3 Nano, or Mimo V2 Flash)
                to use MCP tools and filesystem operations.
              </AlertDescription>
            </Alert>
          )}
        </Card>
      )}
    </div>
  );
}