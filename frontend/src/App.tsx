import { ClerkProvider } from '@clerk/clerk-react';
import { BrowserRouter as Router } from 'react-router-dom';
import { AppRoutes } from '@/routes';

const CLERK_PUBLISHABLE_KEY = 'pk_test_aW1tb3J0YWwtYmVkYnVnLTc2LmNsZXJrLmFjY291bnRzLmRldiQ';

function App() {
  return (
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      <Router>
        <AppRoutes />
      </Router>
    </ClerkProvider>
  );
}

export default App;