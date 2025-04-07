import { Routes, Route, Navigate } from 'react-router-dom';
import { SignInPage } from '@/pages/auth/sign-in';
import { SignUpPage } from '@/pages/auth/sign-up';
import { useAuth } from '@clerk/clerk-react';
import { RootLayout } from '@/components/layout/root-layout';
import { RoleGuard } from '@/components/role/role-guard';
import { RoleSelector } from '@/components/role/role-selector';
import { HomePage } from '@/pages/home';
import { ProfilePage } from '@/pages/profile';
import { OrderFormPage } from '@/pages/customer/order-form';
import { PaymentAuthorizationPage } from '@/pages/customer/payment-authorization';
import { OrderTrackingPage } from '@/pages/customer/order-tracking';
import { OrderHistoryPage } from '@/pages/customer/order-history';
import { AvailableOrdersPage } from '@/pages/runner/available-orders';
import { ActiveOrdersPage } from '@/pages/runner/active-orders';

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { isSignedIn, isLoaded } = useAuth();
  
  if (!isLoaded) {
    return <LoadingScreen />;
  }
  
  if (!isSignedIn) {
    return <Navigate to="/sign-in" replace />;
  }
  
  return <>{children}</>;
}

function LoadingScreen() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Loading CampusG...</p>
      </div>
    </div>
  );
}

function PublicHome() {
  const { isSignedIn, isLoaded } = useAuth();
  
  if (!isLoaded) {
    return <LoadingScreen />;
  }
  
  if (isSignedIn) {
    return <Navigate to="/role-select" replace />;
  }
  
  return <HomePage />;
}

export function AppRoutes() {
  return (
    <Routes>
      {/* Public auth routes with SSO callback handling */}
      <Route path="/sign-in/*" element={<SignInPage />} />
      <Route path="/sign-up/*" element={<SignUpPage />} />
      
      {/* Public home page */}
      <Route path="/" element={<PublicHome />} />
      
      {/* Role selector - moved outside of RootLayout */}
      <Route path="/role-select" element={
        <RequireAuth>
          <RoleSelector />
        </RequireAuth>
      } />
      
      {/* Protected routes with layout */}
      <Route element={<RequireAuth><RootLayout /></RequireAuth>}>
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/profile/:id" element={<ProfilePage />} />

        {/* Customer routes */}
        <Route
          path="/customer/order"
          element={
            <RoleGuard allowedRole="customer">
              <OrderFormPage />
            </RoleGuard>
          }
        />
        <Route
          path="/customer/history"
          element={
            <RoleGuard allowedRole="customer">
              <OrderHistoryPage />
            </RoleGuard>
          }
        />
        <Route
          path="/customer/order/:orderId/payment"
          element={
            <RoleGuard allowedRole="customer">
              <PaymentAuthorizationPage />
            </RoleGuard>
          }
        />
        <Route
          path="/customer/order/:orderId/tracking"
          element={
            <RoleGuard allowedRole="customer">
              <OrderTrackingPage />
            </RoleGuard>
          }
        />

        {/* Runner routes */}
        <Route
          path="/runner/available-orders"
          element={
            <RoleGuard allowedRole="runner">
              <AvailableOrdersPage />
            </RoleGuard>
          }
        />
        <Route
          path="/runner/active-orders"
          element={
            <RoleGuard allowedRole="runner">
              <ActiveOrdersPage />
            </RoleGuard>
          }
        />
      </Route>
    </Routes>
  );
}
