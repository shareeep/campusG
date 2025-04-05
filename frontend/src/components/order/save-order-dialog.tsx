import { useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { OrderItem } from '@/lib/types';

interface SaveOrderDialogProps {
  items: OrderItem[];
  onSave: (name: string) => void;
}

export function SaveOrderDialog({ items, onSave }: SaveOrderDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');

  const handleSave = () => {
    if (name.trim()) {
      onSave(name.trim());
      setOpen(false);
      setName('');
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button variant="outline">Save Order</Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white p-6 shadow-lg">
          <Dialog.Title className="text-xl font-semibold">Save Order</Dialog.Title>
          <Dialog.Description className="mt-2 text-gray-600">
            Give your order a name to save it for later
          </Dialog.Description>

          <div className="mt-4">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Order name"
              className="mb-4"
            />
            <Button onClick={handleSave} className="w-full" disabled={!name.trim()}>
              Save Order
            </Button>
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