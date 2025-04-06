import { CreditCard, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SavedCardDisplayProps {
  last4?: string;
  brand?: string;
  expiryMonth?: string;
  expiryYear?: string;
  onDelete?: () => void;
  isDeleting?: boolean;
}

export function SavedCardDisplay({ 
  last4 = '••••', 
  brand = 'Card', 
  expiryMonth = '••', 
  expiryYear = '••',
  onDelete,
  isDeleting = false
}: SavedCardDisplayProps) {
  return (
    <div className="flex items-center justify-between p-4 border rounded-md">
      <div className="flex items-center gap-3">
        <CreditCard className="h-6 w-6 text-blue-600" />
        <div>
          <p className="font-medium">
            {brand} •••• {last4}
          </p>
          <p className="text-sm text-gray-500">
            Expires {expiryMonth}/{expiryYear}
          </p>
        </div>
      </div>
      
      {onDelete && (
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={onDelete}
          disabled={isDeleting}
          className="text-gray-500 hover:text-red-600"
        >
          {isDeleting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Trash2 className="h-4 w-4" />
          )}
          <span className="sr-only">Delete Card</span>
        </Button>
      )}
    </div>
  );
}
