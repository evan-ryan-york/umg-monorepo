'use client';

import { useState } from 'react';

interface Insight {
  id: string;
  title: string;
  body: string;
  drivers: {
    entity_ids: string[];
    edge_ids: string[];
  };
  status: string;
  created_at: string;
}

interface InsightCardProps {
  insight: Insight;
  onFeedbackComplete?: () => void;
}

export function InsightCard({ insight, onFeedbackComplete }: InsightCardProps): React.JSX.Element | null {
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDismissed, setIsDismissed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Determine card icon and style based on insight type
  const getInsightStyle = () => {
    if (insight.title.includes('Delta Watch')) {
      return {
        icon: '📊',
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200',
        accentColor: 'text-blue-700',
      };
    }
    if (insight.title.includes('Connection')) {
      return {
        icon: '🔗',
        bgColor: 'bg-purple-50',
        borderColor: 'border-purple-200',
        accentColor: 'text-purple-700',
      };
    }
    if (insight.title.includes('Prompt')) {
      return {
        icon: '❓',
        bgColor: 'bg-green-50',
        borderColor: 'border-green-200',
        accentColor: 'text-green-700',
      };
    }
    return {
      icon: '💡',
      bgColor: 'bg-gray-50',
      borderColor: 'border-gray-200',
      accentColor: 'text-gray-700',
    };
  };

  const style = getInsightStyle();

  const handleAcknowledge = async () => {
    setIsProcessing(true);
    setError(null);

    try {
      const response = await fetch(`/api/feedback/acknowledge/${insight.id}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to acknowledge insight');
      }

      // Insight acknowledged - remove from view with a brief delay
      setTimeout(() => {
        setIsDismissed(true);
        onFeedbackComplete?.();
      }, 500);
    } catch (err) {
      console.error('Error acknowledging insight:', err);
      setError(err instanceof Error ? err.message : 'Failed to acknowledge insight');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDismiss = async () => {
    setIsProcessing(true);
    setError(null);

    try {
      const response = await fetch(`/api/feedback/dismiss/${insight.id}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to dismiss insight');
      }

      // Insight dismissed - remove from view with a brief delay
      setTimeout(() => {
        setIsDismissed(true);
        onFeedbackComplete?.();
      }, 500);
    } catch (err) {
      console.error('Error dismissing insight:', err);
      setError(err instanceof Error ? err.message : 'Failed to dismiss insight');
    } finally {
      setIsProcessing(false);
    }
  };

  if (isDismissed) {
    return null; // Hide dismissed cards
  }

  return (
    <div
      className={`border-2 rounded-lg p-6 transition-all ${style.bgColor} ${style.borderColor} ${
        isProcessing ? 'opacity-60' : ''
      }`}
    >
      <div className="flex items-start gap-3 mb-4">
        <span className="text-3xl">{style.icon}</span>
        <div className="flex-1">
          <h3 className={`text-lg font-semibold mb-2 ${style.accentColor}`}>
            {insight.title}
          </h3>
          <p className="text-gray-700 whitespace-pre-wrap">{insight.body}</p>
        </div>
      </div>

      {/* Metadata */}
      <div className="text-xs text-gray-500 mb-4">
        <p>
          {new Date(insight.created_at).toLocaleDateString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
        {insight.drivers.entity_ids.length > 0 && (
          <p className="mt-1">
            Based on {insight.drivers.entity_ids.length} entit
            {insight.drivers.entity_ids.length === 1 ? 'y' : 'ies'}
          </p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={handleAcknowledge}
          disabled={isProcessing}
          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          👍 Acknowledge
        </button>
        <button
          onClick={handleDismiss}
          disabled={isProcessing}
          className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
        >
          👎 Dismiss
        </button>
      </div>

      {/* Processing/Error State */}
      {isProcessing && (
        <p className="text-sm text-gray-500 mt-3 text-center">Processing feedback...</p>
      )}
      {error && (
        <p className="text-sm text-red-600 mt-3 text-center bg-red-50 p-2 rounded">
          {error}
        </p>
      )}
    </div>
  );
}
