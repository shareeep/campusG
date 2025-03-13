import { ClerkProvider } from '@clerk/clerk-react';
import { BrowserRouter as Router } from 'react-router-dom';
import { AppRoutes } from '@/routes';

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;


if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error("Missing Clerk Publishable Key! Check your .env file.");
}

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