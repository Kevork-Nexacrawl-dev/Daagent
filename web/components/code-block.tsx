'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import toast from 'react-hot-toast';

interface CodeBlockProps {
  children: string;
  language?: string;
  className?: string;
}

export function CodeBlock({ children, language, className }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      toast.success('Copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error('Failed to copy');
    }
  };

  // Extract language from className (format: "language-python")
  const lang = className?.replace('language-', '') || language || 'text';

  return (
    <div className="relative group my-4">
      {/* Language badge + copy button */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800 rounded-t-lg">
        <span className="text-xs text-gray-400 font-mono">{lang}</span>
        <Button
          onClick={copyToClipboard}
          size="sm"
          variant="ghost"
          className="h-6 px-2 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          {copied ? (
            <Check className="w-3 h-3 text-green-500" />
          ) : (
            <Copy className="w-3 h-3" />
          )}
        </Button>
      </div>

      {/* Code content */}
      <pre className="overflow-x-auto p-4 bg-gray-950 rounded-b-lg">
        <code className={`text-sm font-mono text-gray-100 ${className || ''}`}>
          {children}
        </code>
      </pre>
    </div>
  );
}