'use client';

import { useState, useRef, useEffect, memo } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Send, Bot, User, Wrench, Loader2, MessageSquare } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { CodeBlock } from '@/components/code-block';
import { Toaster } from 'react-hot-toast';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
}

interface ToolCall {
  name: string;
  args: Record<string, any>;
  result?: string;
}

const MAX_MESSAGES_DISPLAY = 50;

// Memoized User Message Component
const UserMessage = memo(({ content }: { content: string }) => (
  <div className="flex gap-4">
    <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
      <User className="w-5 h-5" />
    </div>
    <div className="flex-1">
      <p className="text-white whitespace-pre-wrap">{content}</p>
    </div>
  </div>
));
UserMessage.displayName = 'UserMessage';

// Memoized Assistant Message Component
const AssistantMessage = memo(({
  content,
  toolCalls
}: {
  content: string;
  toolCalls?: ToolCall[]
}) => (
  <div className="flex gap-4">
    <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center flex-shrink-0">
      <Bot className="w-5 h-5" />
    </div>
    <div className="flex-1 space-y-3">
      <div className="prose prose-invert max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code(props) {
              const { className, children, ...rest } = props;
              const match = /language-(\w+)/.exec(className || '');
              const language = match ? match[1] : '';
              const isInline = !className?.includes('language-');

              if (isInline) {
                return (
                  <code className="px-1.5 py-0.5 bg-gray-800 rounded text-sm font-mono text-blue-400" {...rest}>
                    {children || ''}
                  </code>
                );
              } else {
                return (
                  <CodeBlock language={language} className={className}>
                    {String(children || '').replace(/\n$/, '')}
                  </CodeBlock>
                );
              }
            },
            a(props) {
              const { href, children } = props;
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 underline"
                >
                  {children || ''}
                </a>
              );
            },
            p(props) {
              const { children } = props;
              return <p className="text-white mb-4 last:mb-0">{children || ''}</p>;
            },
            ul(props) {
              const { children } = props;
              return <ul className="list-disc list-inside text-white mb-4 space-y-1">{children || ''}</ul>;
            },
            ol(props) {
              const { children } = props;
              return <ol className="list-decimal list-inside text-white mb-4 space-y-1">{children || ''}</ol>;
            },
            h1(props) {
              const { children } = props;
              return <h1 className="text-2xl font-bold text-white mb-4 mt-6">{children || ''}</h1>;
            },
            h2(props) {
              const { children } = props;
              return <h2 className="text-xl font-bold text-white mb-3 mt-5">{children || ''}</h2>;
            },
            h3(props) {
              const { children } = props;
              return <h3 className="text-lg font-bold text-white mb-2 mt-4">{children || ''}</h3>;
            },
            blockquote(props) {
              const { children } = props;
              return (
                <blockquote className="border-l-4 border-gray-600 pl-4 italic text-gray-300 my-4">
                  {children || ''}
                </blockquote>
              );
            },
            table(props) {
              const { children } = props;
              return (
                <div className="overflow-x-auto my-4">
                  <table className="min-w-full border border-gray-700">{children || ''}</table>
                </div>
              );
            },
            th(props) {
              const { children } = props;
              return (
                <th className="border border-gray-700 px-4 py-2 bg-gray-800 text-left text-white font-semibold">
                  {children || ''}
                </th>
              );
            },
            td(props) {
              const { children } = props;
              return (
                <td className="border border-gray-700 px-4 py-2 text-gray-300">
                  {children || ''}
                </td>
              );
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
      {toolCalls && toolCalls.length > 0 && (
        <div className="space-y-2">
          {toolCalls.map((tool, toolIdx) => (
            <Card key={toolIdx} className="p-3 bg-gray-900 border-gray-800">
              <div className="flex items-start gap-2">
                <Wrench className="w-4 h-4 text-yellow-500 mt-1" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-yellow-500">
                    {tool.name}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {JSON.stringify(tool.args, null, 2)}
                  </p>
                  {tool.result && (
                    <p className="text-xs text-gray-300 mt-2 bg-gray-950 p-2 rounded">
                      {tool.result.slice(0, 200)}
                      {tool.result.length > 200 ? '...' : ''}
                    </p>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  </div>
));
AssistantMessage.displayName = 'AssistantMessage';

// Memoized Streaming Response Component
const StreamingResponse = memo(({ content }: { content: string }) => (
  <div className="flex gap-4">
    <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center flex-shrink-0">
      <Bot className="w-5 h-5" />
    </div>
    <div className="flex-1">
      <div className="prose prose-invert max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code(props) {
              const { className, children, ...rest } = props;
              const isInline = !className?.includes('language-');
              return isInline ? (
                <code className="px-1.5 py-0.5 bg-gray-800 rounded text-sm font-mono text-blue-400" {...rest}>
                  {children || ''}
                </code>
              ) : (
                <pre className="bg-gray-950 p-4 rounded-lg overflow-x-auto">
                  <code className="text-sm font-mono text-gray-100">{children || ''}</code>
                </pre>
              );
            },
            p(props) {
              const { children } = props;
              return <p className="text-white mb-2 last:mb-0">{children || ''}</p>;
            },
            a(props) {
              const { href, children } = props;
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 underline"
                >
                  {children || ''}
                </a>
              );
            },
            ul(props) {
              const { children } = props;
              return <ul className="list-disc list-inside text-white mb-4 space-y-1">{children || ''}</ul>;
            },
            ol(props) {
              const { children } = props;
              return <ol className="list-decimal list-inside text-white mb-4 space-y-1">{children || ''}</ol>;
            },
            h1(props) {
              const { children } = props;
              return <h1 className="text-2xl font-bold text-white mb-4 mt-6">{children || ''}</h1>;
            },
            h2(props) {
              const { children } = props;
              return <h2 className="text-xl font-bold text-white mb-3 mt-5">{children || ''}</h2>;
            },
            h3(props) {
              const { children } = props;
              return <h3 className="text-lg font-bold text-white mb-2 mt-4">{children || ''}</h3>;
            },
            blockquote(props) {
              const { children } = props;
              return (
                <blockquote className="border-l-4 border-gray-600 pl-4 italic text-gray-300 my-4">
                  {children || ''}
                </blockquote>
              );
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
      <span className="inline-block w-1 h-4 bg-white animate-pulse ml-1" />
    </div>
  </div>
));
StreamingResponse.displayName = 'StreamingResponse';

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('auto');
  const [activeModel, setActiveModel] = useState<string>('Auto (Smart)');
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // SSE connection cleanup
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentResponse]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    // Abort any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const userMessage: Message = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setCurrentResponse('');
    setCurrentToolCalls([]);

    // Create new abort controller for this request
    abortControllerRef.current = new AbortController();

    // Collect streaming data in local variables
    let streamedResponse = '';
    let streamedToolCalls: ToolCall[] = [];

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          messages: [...messages, userMessage],
          selectedModel: selectedModel  // ADD THIS LINE
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            try {
              const event = JSON.parse(jsonStr);

              if (event.type === 'text') {
                streamedResponse += event.content;
                setCurrentResponse(streamedResponse);
              } else if (event.type === 'tool') {
                const newTool = { name: event.name, args: event.args, result: event.result };
                streamedToolCalls = [...streamedToolCalls, newTool];
                setCurrentToolCalls(streamedToolCalls);
              } else if (event.type === 'model_info') {
                // NEW: Update active model display
                setActiveModel(event.model_name);
              } else if (event.type === 'done') {
                // Finalize with local variables (no closure issues)
                setMessages((prev) => [
                  ...prev,
                  {
                    role: 'assistant',
                    content: streamedResponse,
                    toolCalls: streamedToolCalls.length > 0 ? streamedToolCalls : undefined,
                  },
                ]);
                setCurrentResponse('');
                setCurrentToolCalls([]);
                setIsLoading(false);
                abortControllerRef.current = null;
              } else if (event.type === 'error') {
                console.error('Stream error:', event.message);
                setIsLoading(false);
                abortControllerRef.current = null;
              }
            } catch (e) {
              console.error('Failed to parse SSE event:', e);
            }
          }
        }
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Request was aborted');
      } else {
        console.error('Chat error:', error);
        setIsLoading(false);
      }
      abortControllerRef.current = null;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 p-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="w-8 h-8 text-blue-500" />
            <div>
              <h1 className="text-xl font-bold text-white">Daagent</h1>
              <p className="text-sm text-gray-400">AI Agent with Dynamic Tools</p>
            </div>
          </div>

          {/* Model Selector */}
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs text-gray-500">Active Model</p>
              <p className="text-sm text-white font-medium">{activeModel}</p>
            </div>
            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger className="w-[200px] bg-gray-900 border-gray-800 text-white">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent className="bg-gray-900 border-gray-800">
                <SelectItem value="auto" className="text-white">
                  <div className="flex items-center gap-2">
                    <span>🎯 Auto (Smart)</span>
                  </div>
                </SelectItem>
                <SelectItem value="deepseek-r1-free" className="text-white">
                  <div className="flex items-center gap-2">
                    <span>🆓 DeepSeek R1 Chimera (Free)</span>
                  </div>
                </SelectItem>
                <SelectItem value="deepseek-v3-hf" className="text-white">
                  <div className="flex items-center gap-2">
                    <span>🤗 DeepSeek V3.2 (HuggingFace)</span>
                  </div>
                </SelectItem>
                <SelectItem value="grok-4-fast" className="text-white">
                  <div className="flex items-center gap-2">
                    <span>⚡ Grok 4 Fast (Code)</span>
                  </div>
                </SelectItem>
                <SelectItem value="claude-sonnet" className="text-white">
                  <div className="flex items-center gap-2">
                    <span>🧠 Claude Sonnet (Reasoning)</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <Bot className="w-16 h-16 mx-auto text-gray-600 mb-4" />
              <h2 className="text-xl font-semibold text-gray-300 mb-2">
                Welcome to Daagent
              </h2>
              <p className="text-gray-500">
                Ask me anything. I can search the web, execute code, and more.
              </p>
            </div>
          )}

          {/* Conversation truncation indicator */}
          {messages.length > MAX_MESSAGES_DISPLAY && (
            <div className="text-center py-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-gray-800 rounded-full text-xs text-gray-400">
                <MessageSquare className="w-3 h-3" />
                Showing last {MAX_MESSAGES_DISPLAY} of {messages.length} messages
              </div>
            </div>
          )}

          {/* Display only the last MAX_MESSAGES_DISPLAY messages */}
          {messages.slice(-MAX_MESSAGES_DISPLAY).map((message, idx) => (
            <div key={messages.length - MAX_MESSAGES_DISPLAY + idx}>
              {message.role === 'user' ? (
                <UserMessage content={message.content} />
              ) : (
                <AssistantMessage content={message.content} toolCalls={message.toolCalls} />
              )}
            </div>
          ))}

          {/* Current streaming response */}
          {isLoading && currentResponse && (
            <StreamingResponse content={currentResponse} />
          )}

          {/* Loading indicator */}
          {isLoading && !currentResponse && (
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-full bg-green-600 flex items-center justify-center flex-shrink-0">
                <Loader2 className="w-5 h-5 animate-spin" />
              </div>
              <div className="flex-1">
                <p className="text-gray-400">Agent is thinking...</p>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t border-gray-800 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-2">
            <Textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything... (Shift+Enter for newline)"
              className="flex-1 min-h-[60px] max-h-[200px] bg-gray-900 border-gray-800 text-white resize-none"
              disabled={isLoading}
            />
            <Button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <Send className="w-5 h-5" />
            </Button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Press Enter to send, Shift+Enter for newline
          </p>
        </div>
      </div>

      {/* Toast notifications */}
      <Toaster position="top-right" />
    </div>
  );
}
