import type { ArchivistLogEntry } from '@repo/db';
import { LogItem } from './LogItem';

interface LogListProps {
  logs: ArchivistLogEntry[];
}

export function LogList({ logs }: LogListProps): React.ReactElement {
  if (logs.length === 0) {
    return (
      <div className="text-center py-12 bg-gray-50 border border-gray-200 rounded-lg">
        <p className="text-gray-600 text-lg">
          No processed events yet. The Archivist is waiting...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {logs.map((log) => (
        <LogItem key={log.rawEvent.id} log={log} />
      ))}
    </div>
  );
}
