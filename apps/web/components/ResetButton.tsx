'use client';

import { useState } from 'react';

export function ResetButton(): React.ReactElement {
  const [isResetting, setIsResetting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleReset = async (): Promise<void> => {
    setIsResetting(true);
    setShowConfirm(false);

    try {
      const response = await fetch('/api/archivist-reset', {
        method: 'POST',
      });

      const data = await response.json();

      if (data.success) {
        alert('✅ All Archivist data cleared successfully!');
        window.location.reload();
      } else {
        alert('❌ Failed to clear data: ' + data.error);
      }
    } catch (error) {
      console.error('Error resetting data:', error);
      alert('❌ Error resetting data');
    } finally {
      setIsResetting(false);
    }
  };

  if (showConfirm) {
    return (
      <div className="flex gap-2">
        <button
          onClick={handleReset}
          disabled={isResetting}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isResetting ? 'Resetting...' : 'Confirm Reset'}
        </button>
        <button
          onClick={() => setShowConfirm(false)}
          disabled={isResetting}
          className="px-4 py-2 bg-gray-300 text-gray-800 rounded hover:bg-gray-400 disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => setShowConfirm(true)}
      className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
    >
      Reset All Data
    </button>
  );
}
