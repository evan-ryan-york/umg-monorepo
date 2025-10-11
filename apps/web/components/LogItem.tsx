'use client';

import { useState } from 'react';
import type { ArchivistLogEntry } from '@repo/db';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, FileText, CheckCircle, ArrowRight, TrendingUp, Clock, Sparkles, Trash2 } from 'lucide-react';

interface LogItemProps {
  log: ArchivistLogEntry;
  onDelete?: (id: string) => void;
}

export function LogItem({ log, onDelete }: LogItemProps): React.ReactElement {
  const { rawEvent, createdEntities, createdEdges, summary, signals } = log;
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm('Delete this entry and all related data? This cannot be undone.')) {
      return;
    }

    setIsDeleting(true);
    try {
      const response = await fetch(`/api/events/${rawEvent.id}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.success) {
        onDelete?.(rawEvent.id);
      } else {
        alert(`Failed to delete: ${data.error}`);
        setIsDeleting(false);
      }
    } catch (error) {
      console.error('Delete error:', error);
      alert('Failed to delete entry');
      setIsDeleting(false);
    }
  };

  return (
    <Card className={isDeleting ? 'opacity-50 pointer-events-none' : ''}>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-sm font-mono text-muted-foreground">
                {rawEvent.id.slice(0, 8)}...
              </CardTitle>
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {new Date(rawEvent.created_at).toLocaleString()}
              </div>
              <Badge variant="outline" className="text-xs">
                {rawEvent.source}
              </Badge>
              <Badge variant={rawEvent.status === 'processed' ? 'default' : 'secondary'} className="text-xs">
                <CheckCircle className="h-3 w-3 mr-1" />
                {rawEvent.status}
              </Badge>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDelete}
            disabled={isDeleting}
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Raw Event Content */}
        <blockquote className="border-l-2 border-primary pl-4 italic text-sm">
          {rawEvent.payload.content}
        </blockquote>

        {/* Archivist Actions */}
        <div className="pt-4 space-y-4">
          <h4 className="font-semibold flex items-center gap-2 text-sm">
            <Sparkles className="h-4 w-4 text-primary" />
            Archivist&apos;s Analysis
          </h4>

          {/* Entities */}
          {createdEntities.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm font-medium flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5" />
                Entities Extracted ({createdEntities.length})
              </p>
              <div className="space-y-3">
                {createdEntities.map((entity) => {
                  const entitySignal = signals.find((s) => s.entity_id === entity.id);
                  return (
                    <div key={entity.id} className="bg-muted/50 rounded-lg p-3 space-y-2">
                      <div className="flex items-start gap-2">
                        <span className="text-lg">{getEntityEmoji(entity.type)}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="secondary" className="text-xs">
                              {entity.type}
                            </Badge>
                            <span className="font-medium text-sm truncate">
                              {entity.title}
                            </span>
                          </div>
                          {entity.summary && (
                            <p className="text-xs text-muted-foreground mt-1.5">
                              {entity.summary}
                            </p>
                          )}
                          {entitySignal && (
                            <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                              <div className="flex items-center gap-1">
                                <TrendingUp className="h-3 w-3 text-primary" />
                                <span className="font-medium">I:</span>
                                <span>{entitySignal.importance.toFixed(2)}</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3 text-blue-500" />
                                <span className="font-medium">R:</span>
                                <span>{entitySignal.recency.toFixed(2)}</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Sparkles className="h-3 w-3 text-purple-500" />
                                <span className="font-medium">N:</span>
                                <span>{entitySignal.novelty.toFixed(2)}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Edges */}
          {createdEdges.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm font-medium flex items-center gap-2">
                <ArrowRight className="h-3.5 w-3.5" />
                Relationships Mapped ({createdEdges.length})
              </p>
              <div className="space-y-2">
                {createdEdges.map((edge) => {
                  // Detect hub-spoke relationships
                  const isHubSpoke =
                    edge.kind === 'relates_to' &&
                    (edge.fromEntity.type === 'meeting_note' ||
                      edge.fromEntity.type === 'reflection' ||
                      edge.toEntity.type === 'project' ||
                      edge.toEntity.type === 'feature' ||
                      edge.toEntity.type === 'decision');

                  return (
                    <div key={edge.id} className="flex items-center gap-2 text-xs bg-muted/30 rounded px-3 py-2">
                      <span className="font-medium truncate max-w-[40%]">
                        {edge.fromEntity.title}
                      </span>
                      <div className="flex items-center gap-1 shrink-0">
                        <ArrowRight className="h-3 w-3 text-muted-foreground" />
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                          {edge.kind}
                        </Badge>
                        <ArrowRight className="h-3 w-3 text-muted-foreground" />
                      </div>
                      <span className="font-medium truncate max-w-[40%]">
                        {edge.toEntity.title}
                      </span>
                      {isHubSpoke && (
                        <Badge variant="secondary" className="text-[10px] ml-auto">
                          HUB
                        </Badge>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Summary */}
          <div className="bg-muted/30 p-3 rounded-lg border">
            <p className="text-xs font-medium mb-2 text-muted-foreground">Processing Summary</p>
            <div className="grid grid-cols-3 gap-3 text-xs">
              <div>
                <div className="font-semibold">{summary.chunkCount}</div>
                <div className="text-muted-foreground">Chunks</div>
              </div>
              <div>
                <div className="font-semibold">{summary.embeddingCount}</div>
                <div className="text-muted-foreground">Embeddings</div>
              </div>
              <div>
                <div className="font-semibold">{summary.signalCount}</div>
                <div className="text-muted-foreground">Signals</div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function getEntityEmoji(type: string): string {
  const emojiMap: Record<string, string> = {
    // Work-related
    feature: '🚀',
    project: '📂',
    task: '✅',
    // Relationship
    person: '👤',
    company: '🏢',
    // Thought entities
    meeting_note: '📝',
    reflection: '💭',
    decision: '🎯',
    // Knowledge
    core_identity: '⭐',
    reference_document: '📄',
  };
  return emojiMap[type] || '📌';
}
