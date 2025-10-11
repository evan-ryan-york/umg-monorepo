import { NextRequest, NextResponse } from 'next/server';

const AI_CORE_URL = process.env.AI_CORE_URL || 'http://localhost:8000';

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    // Call Python backend's smart undo service
    const response = await fetch(`${AI_CORE_URL}/events/${id}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json();
      console.error('Error from AI Core:', error);
      return NextResponse.json(
        { success: false, error: error.detail || 'Failed to delete event' },
        { status: response.status }
      );
    }

    const result = await response.json();

    return NextResponse.json({
      success: true,
      message: 'Event deleted with smart undo logic',
      ...result
    });

  } catch (error) {
    console.error('Delete error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
