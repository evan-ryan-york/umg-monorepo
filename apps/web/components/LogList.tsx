'use client';

import { useState } from 'react';
import type { ArchivistLogEntry } from '@repo/db';
import { LogItem } from './LogItem';
import { Card, CardContent } from '@/components/ui/card';
import { Inbox } from 'lucide-react';

interface LogListProps {
  initialLogs: ArchivistLogEntry[];
}

export function LogList({ initialLogs }: LogListProps): React.ReactElement {
  const [logs, setLogs] = useState(initialLogs);

  const handleDelete = (deletedId: string) => {
    // Optimistically remove from UI
    setLogs(prevLogs => prevLogs.filter(log => log.rawEvent.id !== deletedId));
  };

  if (logs.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Inbox className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-lg font-medium">No processed events yet</p>
          <p className="text-sm text-muted-foreground mt-1">
            The Archivist is waiting for your first capture...
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {logs.map((log) => (
        <LogItem key={log.rawEvent.id} log={log} onDelete={handleDelete} />
      ))}
    </div>
  );
}
