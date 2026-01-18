import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';
import yaml from 'js-yaml';
import { spawn } from 'child_process';

const PROMPTS_DIR = path.join(process.cwd(), '..', 'prompts');

async function findYamlFiles(dir: string): Promise<string[]> {
  const files: string[] = [];
  const items = await fs.readdir(dir, { withFileTypes: true });
  for (const item of items) {
    const fullPath = path.join(dir, item.name);
    if (item.isDirectory()) {
      files.push(...await findYamlFiles(fullPath));
    } else if (item.name.endsWith('.yaml') || item.name.endsWith('.yml')) {
      files.push(fullPath);
    }
  }
  return files;
}

export async function GET() {
  try {
    const files = await findYamlFiles(PROMPTS_DIR);
    const layers = await Promise.all(
      files.map(async (filePath) => {
        const content = await fs.readFile(filePath, 'utf-8');
        const data = yaml.load(content) as any;
        return { ...data, filePath, enabled: true };
      })
    );
    return NextResponse.json({ layers });
  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  try {
    const contentType = req.headers.get('content-type') || '';
    if (contentType.includes('multipart/form-data')) {
      // Handle file upload
      const formData = await req.formData();
      const files = formData.getAll('files') as File[];
      const uploaded: string[] = [];
      for (const file of files) {
        if (file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
          const customDir = path.join(PROMPTS_DIR, 'custom');
          await fs.mkdir(customDir, { recursive: true });
          const filePath = path.join(customDir, file.name);
          const buffer = Buffer.from(await file.arrayBuffer());
          await fs.writeFile(filePath, buffer);
          uploaded.push(filePath);
        }
      }
      return NextResponse.json({ uploaded });
    } else {
      // Handle other actions
      const { action, enabledLayers, filePath, newPriority } = await req.json();
      if (action === 'compose') {
        // Load enabled layers and compose
        const layers = [];
        for (const fp of enabledLayers) {
          const content = await fs.readFile(fp, 'utf-8');
          const data = yaml.load(content) as any;
          layers.push(data);
        }
        // Now, call Python to compose, but since we have the data, perhaps compose in JS
        // But to use the backend logic, better to serialize and pass to Python
        // For simplicity, implement compose in JS based on the Python code
        const composed = composePrompt(layers);
        return NextResponse.json({ composed });
      }
    }
    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}

export async function PUT(req: NextRequest) {
  try {
    const { filePath, newPriority } = await req.json();
    const content = await fs.readFile(filePath, 'utf-8');
    const data = yaml.load(content) as any;
    data.priority = newPriority;
    const newContent = yaml.dump(data);
    await fs.writeFile(filePath, newContent);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}

export async function DELETE(req: NextRequest) {
  try {
    const { filePath } = await req.json();
    await fs.unlink(filePath);
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}

// Simple compose function in JS, mimicking Python
function composePrompt(layers: any[]): string {
  if (!layers.length) return '';
  // Sort by priority
  layers.sort((a, b) => a.priority - b.priority);
  // Group by priority_group
  const groups: { [key: string]: any[] } = {};
  for (const layer of layers) {
    const group = layer.priority_group || 'default';
    if (!groups[group]) groups[group] = [];
    groups[group].push(layer);
  }
  // Process groups
  const finalParts: string[] = [];
  for (const group of Object.values(groups)) {
    if (group[0].mode === 'stackable') {
      for (const layer of group) {
        finalParts.push(layer.content);
      }
    } else {
      const highest = group.reduce((prev, curr) => prev.priority > curr.priority ? prev : curr);
      finalParts.push(highest.content);
    }
  }
  return finalParts.join('\n\n');
}