import { spawn } from 'child_process';
import { NextRequest } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface RequestBody {
  messages: ChatMessage[];
  selectedModel?: string;  // ADD THIS
}

export async function POST(req: NextRequest) {
  try {
    const body: RequestBody = await req.json();
    const { messages } = body;

    if (!messages || messages.length === 0) {
      return new Response('No messages provided', { status: 400 });
    }

    // Get the latest user message
    const userMessage = messages[messages.length - 1].content;
    const selectedModel = body.selectedModel || 'auto';  // ADD THIS

    // Set up SSE stream
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        // Spawn Python agent process
        const pythonProcess = spawn('python', [
          '-u', 
          '-m', 
          'agent', 
          userMessage,
          '--model', selectedModel  // ADD THIS ARG
        ], {
          cwd: process.cwd() + '/../',  // Go up to daagent/ root
          env: { ...process.env, PYTHONUNBUFFERED: '1' }
        });

        let buffer = '';

        pythonProcess.stdout.on('data', (data) => {
          const text = data.toString();
          buffer += text;

          // Split by newlines to get complete JSON objects
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.trim()) {
              try {
                // Try to parse as JSON event
                const event = JSON.parse(line);

                // Send SSE event
                const sseData = `data: ${JSON.stringify(event)}\n\n`;
                controller.enqueue(encoder.encode(sseData));
              } catch (e) {
                // Not JSON, send as raw text
                const event = { type: 'text', content: line };
                const sseData = `data: ${JSON.stringify(event)}\n\n`;
                controller.enqueue(encoder.encode(sseData));
              }
            }
          }
        });

        pythonProcess.stderr.on('data', (data) => {
          console.error('Python stderr:', data.toString());
        });

        pythonProcess.on('close', (code) => {
          // Send done event
          const doneEvent = { type: 'done', code };
          const sseData = `data: ${JSON.stringify(doneEvent)}\n\n`;
          controller.enqueue(encoder.encode(sseData));
          controller.close();
        });

        pythonProcess.on('error', (error) => {
          console.error('Process error:', error);
          const errorEvent = { type: 'error', message: error.message };
          const sseData = `data: ${JSON.stringify(errorEvent)}\n\n`;
          controller.enqueue(encoder.encode(sseData));
          controller.close();
        });
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('API error:', error);
    return new Response('Internal server error', { status: 500 });
  }
}