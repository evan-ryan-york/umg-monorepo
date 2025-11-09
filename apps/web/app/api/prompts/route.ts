import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import yaml from 'yaml';

const PROMPTS_DIR = path.join(process.cwd(), '..', '..', 'apps', 'ai-core', 'prompts');

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const promptName = searchParams.get('name');

    if (!promptName) {
      // List all prompts
      const files = fs.readdirSync(PROMPTS_DIR).filter(f => f.endsWith('.yaml'));
      const prompts = files.map(f => ({
        name: f.replace('.yaml', ''),
        filename: f
      }));

      return NextResponse.json({ prompts });
    }

    // Get specific prompt
    const filePath = path.join(PROMPTS_DIR, `${promptName}.yaml`);

    if (!fs.existsSync(filePath)) {
      return NextResponse.json(
        { error: 'Prompt not found' },
        { status: 404 }
      );
    }

    const content = fs.readFileSync(filePath, 'utf-8');

    return NextResponse.json({
      name: promptName,
      content
    });
  } catch (error) {
    console.error('Error reading prompt:', error);
    return NextResponse.json(
      { error: 'Failed to read prompt' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const { name, content } = await request.json();

    if (!name || !content) {
      return NextResponse.json(
        { error: 'Name and content are required' },
        { status: 400 }
      );
    }

    // Validate YAML by trying to parse it
    try {
      yaml.parse(content);
    } catch (e) {
      const errorMessage = e instanceof Error ? e.message : String(e);
      return NextResponse.json(
        { error: `Invalid YAML: ${errorMessage}` },
        { status: 400 }
      );
    }

    const filePath = path.join(PROMPTS_DIR, `${name}.yaml`);
    fs.writeFileSync(filePath, content, 'utf-8');

    return NextResponse.json({
      success: true,
      message: 'Prompt saved successfully'
    });
  } catch (error) {
    console.error('Error saving prompt:', error);
    return NextResponse.json(
      { error: 'Failed to save prompt' },
      { status: 500 }
    );
  }
}
