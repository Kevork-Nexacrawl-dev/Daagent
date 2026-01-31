import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export const runtime = 'nodejs';

interface RouteParams {
  params: Promise<{
    model_id: string;
  }>;
}

// GET /api/models/{model_id}/capabilities - Get specific model info
export async function GET(request: NextRequest, { params }: RouteParams): Promise<Response> {
  try {
    const resolvedParams = await params;
    const modelId = decodeURIComponent(resolvedParams.model_id);

    // Get model capabilities from Python config
    const pythonProcess = spawn('python', [
      '-c',
      `
import sys
sys.path.insert(0, '${path.join(process.cwd(), '..')}')
from agent.config import Config
import json

model_id = '${modelId.replace(/'/g, "\\'")}'

# Check all model registries
all_models = {}
all_models.update(Config.FREE_TOOL_MODELS)
all_models.update(Config.FREE_REASONING_MODELS)
all_models.update(Config.PAID_MODELS)

if model_id in all_models:
    capabilities = all_models[model_id].copy()
    capabilities['id'] = model_id
    print(json.dumps(capabilities))
else:
    # Default fallback
    print(json.dumps({
        'id': model_id,
        'display_name': model_id,
        'supports_tools': True,
        'supports_streaming': True,
        'context_window': 65536,
        'best_for': 'General purpose',
        'cost_per_1m': 0.0,
        'tier': 'unknown'
    }))
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
            const capabilities = JSON.parse(stdout.trim());
            resolve(NextResponse.json(capabilities));
          } catch (parseError) {
            resolve(NextResponse.json(
              { error: 'Failed to parse capabilities data' },
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
      { error: 'Failed to load model capabilities' },
      { status: 500 }
    );
  }
}