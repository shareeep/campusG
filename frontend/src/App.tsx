import { BrowserRouter as Router } from 'react-router-dom';
import { AppRoutes } from '@/routes';
import { ToastProvider } from '@/components/ui/toast-provider';
import { ClerkProvider } from './providers/ClerkProvider';
import { UserSyncProvider } from './providers/UserSyncProvider';

function App() {
  return (
    <ClerkProvider>
      <UserSyncProvider>
        <ToastProvider>
          <Router>
            <AppRoutes />
          </Router>
        </ToastProvider>
      </UserSyncProvider>
    </ClerkProvider>
  );
}

export default App;
