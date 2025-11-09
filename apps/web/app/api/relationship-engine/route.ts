/**
 * Relationship Engine API Endpoint
 *
 * Provides on-demand triggering of the RelationshipEngine for:
 * - Manual graph analysis
 * - Testing new strategies
 * - Re-analyzing specific entities
 *
 * POST /api/relationship-engine
 *
 * Body:
 * {
 *   "mode": "on-demand" | "nightly",
 *   "entityIds": string[] (optional - if provided, only analyze these entities),
 *   "fullScan": boolean (optional - for nightly mode, default false)
 * }
 *
 * Returns:
 * {
 *   "success": boolean,
 *   "result": {
 *     "edges_created": number,
 *     "edges_updated": number,
 *     "edges_pruned": number (nightly mode only),
 *     "entities_analyzed": number,
 *     "processing_time": number
 *   }
 * }
 */

import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { mode = 'on-demand', entityIds, fullScan = false } = body;

    console.log('[RelationshipEngine API] Request:', { mode, entityIds: entityIds?.length, fullScan });

    // Validate mode
    if (!['on-demand', 'nightly'].includes(mode)) {
      return NextResponse.json(
        { success: false, error: 'Invalid mode. Must be "on-demand" or "nightly"' },
        { status: 400 }
      );
    }

    // Build Python command to run RelationshipEngine
    let pythonScript = '';

    if (mode === 'on-demand') {
      if (entityIds && entityIds.length > 0) {
        // Analyze specific entities
        const entityIdsJson = JSON.stringify(entityIds);
        pythonScript = `
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ai-core'))

from engines.relationship_engine import RelationshipEngine

engine = RelationshipEngine()
entity_ids = ${entityIdsJson}
result = engine.run_on_demand(entity_ids=entity_ids)
print(json.dumps(result))
`;
      } else {
        // Analyze entire graph
        pythonScript = `
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ai-core'))

from engines.relationship_engine import RelationshipEngine

engine = RelationshipEngine()
result = engine.run_on_demand()
print(json.dumps(result))
`;
      }
    } else if (mode === 'nightly') {
      // Run nightly mode
      pythonScript = `
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ai-core'))

from engines.relationship_engine import RelationshipEngine

engine = RelationshipEngine()
result = engine.run_nightly(full_scan=${fullScan ? 'True' : 'False'})
print(json.dumps(result))
`;
    }

    // Execute Python script
    const pythonPath = process.env.PYTHON_PATH || 'python3';
    const { stdout, stderr } = await execAsync(`${pythonPath} -c "${pythonScript.replace(/"/g, '\\"').replace(/\n/g, ' ')}"`, {
      timeout: 300000, // 5 minute timeout
      cwd: process.cwd()
    });

    if (stderr) {
      console.warn('[RelationshipEngine API] stderr:', stderr);
    }

    // Parse result
    let result;
    try {
      result = JSON.parse(stdout.trim());
    } catch {
      console.error('[RelationshipEngine API] Failed to parse output:', stdout);
      return NextResponse.json(
        { success: false, error: 'Failed to parse engine output', output: stdout },
        { status: 500 }
      );
    }

    console.log('[RelationshipEngine API] Success:', result);

    return NextResponse.json({
      success: true,
      mode,
      result
    });

  } catch (error) {
    console.error('[RelationshipEngine API] Error:', error);

    const errorMessage = error instanceof Error ? error.message : 'Failed to run relationship engine';
    const errorDetails = typeof error === 'object' && error !== null &&
      ('stderr' in error || 'stdout' in error)
      ? (error as { stderr?: string; stdout?: string }).stderr ||
        (error as { stderr?: string; stdout?: string }).stdout
      : undefined;

    return NextResponse.json(
      {
        success: false,
        error: errorMessage,
        details: errorDetails
      },
      { status: 500 }
    );
  }
}

// GET endpoint for status/health check
export async function GET() {
  return NextResponse.json({
    service: 'RelationshipEngine API',
    status: 'active',
    modes: ['on-demand', 'nightly'],
    description: 'Triggers RelationshipEngine for manual graph analysis',
    usage: {
      method: 'POST',
      body: {
        mode: 'on-demand | nightly',
        entityIds: 'string[] (optional)',
        fullScan: 'boolean (optional, for nightly mode)'
      }
    }
  });
}
