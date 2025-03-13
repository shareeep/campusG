import { ClerkProvider } from '@clerk/clerk-react';
import { BrowserRouter as Router } from 'react-router-dom';
import { AppRoutes } from '@/routes';

const CLERK_PUBLISHABLE_KEY = 'your_clerk_publishable_key';

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