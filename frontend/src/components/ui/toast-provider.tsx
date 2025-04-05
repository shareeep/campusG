import { ToastProvider as Provider } from '@/components/ui/toast';
import { Toaster } from '@/components/ui/toaster';

export function ToastProvider({ children }: { children: React.ReactNode }) {
  return (
    <Provider>
      {children}
      <Toaster />
    </Provider>
  );
}