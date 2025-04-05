import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { SavedOrder } from '@/lib/types';

interface SavedOrdersDialogProps {
  savedOrders: SavedOrder[];
  onSelect: (order: SavedOrder) => void;
}

export function SavedOrdersDialog({ savedOrders, onSelect }: SavedOrdersDialogProps) {
  const [open, setOpen] = useState(false);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button variant="outline">Load Saved Order</Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-lg">
          <Dialog.Title className="text-xl font-semibold">Saved Orders</Dialog.Title>
          <Dialog.Description className="mt-2 text-gray-600">
            Select a saved order to load its items
          </Dialog.Description>

          <div className="mt-4 space-y-2">
            {savedOrders.map((order) => (
              <button
                key={order.id}
                className="w-full rounded-lg border p-4 text-left hover:bg-gray-50"
                onClick={() => {
                  onSelect(order);
                  setOpen(false);
                }}
              >
                <h3 className="font-medium">{order.name}</h3>
                <p className="mt-1 text-sm text-gray-600">
                  {order.items.length} items • Created{' '}
                  {new Date(order.created_at).toLocaleDateString()}
                </p>
              </button>
            ))}
          </div>

          <Dialog.Close asChild>
            <button
              className="absolute right-4 top-4 rounded-sm opacity-70 hover:opacity-100"
              aria-label="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}