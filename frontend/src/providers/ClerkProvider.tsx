import { ClerkProvider as BaseClerkProvider } from '@clerk/clerk-react';
import { ReactNode } from 'react';
import { CLERK_PUBLISHABLE_KEY } from '../lib/clerk';

interface ClerkProviderProps {
  children: ReactNode;
}

export function ClerkProvider({ children }: ClerkProviderProps) {
  return (
    <BaseClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY || ''}>
      {children}
    </BaseClerkProvider>
  );
}
