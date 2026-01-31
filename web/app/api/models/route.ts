import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export const runtime = 'nodejs';

// GET /api/models - List all models categorized
export async function GET(request: NextRequest): Promise<Response> {
  try {
    // Get models from Python config
    const pythonProcess = spawn('python', [
      '-c',
      `
import sys
sys.path.insert(0, '${path.join(process.cwd(), '..')}')
from agent.config import Config
import json

models = {
  'free_tool_models': [
    {'id': k, **v} for k, v in Config.FREE_TOOL_MODELS.items()
  ],
  'free_reasoning_models': [
    {'id': k, **v} for k, v in Config.FREE_REASONING_MODELS.items()
  ],
  'paid_models': [
    {'id': k, **v} for k, v in Config.PAID_MODELS.items()
  ]
}
print(json.dumps(models))
      `
    ], {
      cwd: process.cwd(),
      env: { ...process.env, PYTHONPATH: path.join(process.cwd(), '..') }
    });

    return new Promise((resolve) => {
      let stdout = '';
      let stderr = '';

      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      pythonProcess.on('close', (code) => {
        if (code === 0) {
          try {
            const models = JSON.parse(stdout.trim());
            resolve(NextResponse.json(models));
          } catch (parseError) {
            resolve(NextResponse.json(
              { error: 'Failed to parse model data' },
              { status: 500 }
            ));
          }
        } else {
          resolve(NextResponse.json(
            { error: `Python process failed: ${stderr}` },
            { status: 500 }
          ));
        }
      });
    });

  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to load models' },
      { status: 500 }
    );
  }
}