import { BrowserRouter as Router } from 'react-router-dom';
import { AppRoutes } from '@/routes';
import { ToastProvider } from '@/components/ui/toast-provider';
import { ClerkProvider } from './providers/ClerkProvider';
import { UserSyncProvider } from './providers/UserSyncProvider';
import { StripeProvider } from './providers/StripeProvider';

function App() {
  return (
    <ClerkProvider>
      <UserSyncProvider>
        <StripeProvider>
          <ToastProvider>
            <Router>
              <AppRoutes />
            </Router>
          </ToastProvider>
        </StripeProvider>
      </UserSyncProvider>
    </ClerkProvider>
  );
}

export default App;
