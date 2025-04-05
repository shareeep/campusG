import { BrowserRouter as Router } from 'react-router-dom';
import { AppRoutes } from '@/routes';
import { ToastProvider } from '@/components/ui/toast-provider';

function App() {
  return (
    <ToastProvider>
      <Router>
        <AppRoutes />
      </Router>
    </ToastProvider>
  );
}

export default App;