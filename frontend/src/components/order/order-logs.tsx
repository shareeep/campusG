import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getOrderLogs } from '@/lib/api';
import type { OrderLog } from '@/lib/types';

interface OrderLogsProps {
  orderId: string;
}

export function OrderLogs({ orderId }: OrderLogsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [logs, setLogs] = useState<OrderLog[]>([]);

  useEffect(() => {
    const fetchLogs = async () => {
      const orderLogs = await getOrderLogs(orderId);
      setLogs(orderLogs.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ));
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [orderId]);

  return (
    <div className="mt-6 rounded-lg border bg-gray-50">
      <Button
        variant="ghost"
        className="flex w-full items-center justify-between p-4"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="font-medium">Order Logs</span>
        {isExpanded ? (
          <ChevronUp className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
      </Button>

      {isExpanded && (
        <div className="border-t p-4">
          <div className="space-y-2">
            {logs.map((log) => (
              <div
                key={log.id}
                className={`rounded-md p-2 text-sm ${
                  log.type === 'error'
                    ? 'bg-red-50 text-red-700'
                    : log.type === 'success'
                    ? 'bg-green-50 text-green-700'
                    : log.type === 'warning'
                    ? 'bg-yellow-50 text-yellow-700'
                    : 'bg-blue-50 text-blue-700'
                }`}
              >
                <time className="mr-2 font-mono text-xs opacity-70">
                  {new Date(log.created_at).toLocaleTimeString()}
                </time>
                {log.message}
              </div>
            ))}

            {logs.length === 0 && (
              <div className="text-center py-4 text-gray-500">
                No logs available
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}