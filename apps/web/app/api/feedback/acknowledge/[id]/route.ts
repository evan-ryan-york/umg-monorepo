import { NextResponse } from 'next/server';

const AI_CORE_URL = process.env.AI_CORE_URL || 'http://localhost:8000';

/**
 * POST /api/feedback/acknowledge/[id]
 * User acknowledged an insight as valuable
 *
 * Actions:
 * - Boost importance scores for driver entities (+0.1)
 * - Refresh recency scores to 1.0
 * - Update insight status to 'acknowledged'
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const insightId = id;

    if (!insightId) {
      return NextResponse.json(
        { success: false, error: 'Insight ID is required' },
        { status: 400 }
      );
    }

    // Call AI Core to process feedback
    const response = await fetch(`${AI_CORE_URL}/feedback/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ insight_id: insightId }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      console.error('AI Core feedback processing failed:', errorData);
      return NextResponse.json(
        { success: false, error: errorData.detail || 'Failed to process feedback' },
        { status: response.status }
      );
    }

    const result = await response.json();

    return NextResponse.json({
      success: true,
      action: 'acknowledged',
      ...result,
    });
  } catch (error) {
    console.error('Error processing acknowledge feedback:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
