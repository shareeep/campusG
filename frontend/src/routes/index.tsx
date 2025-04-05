import { Routes, Route, Navigate } from 'react-router-dom';
import { RootLayout } from '@/components/layout/root-layout';
import { RoleGuard } from '@/components/role/role-guard';
import { RoleSelector } from '@/components/role/role-selector';
import { UserSelectPage } from '@/pages/user-select';
import { HomePage } from '@/pages/home';
import { ProfilePage } from '@/pages/profile';
import { OrderFormPage } from '@/pages/customer/order-form';
import { PaymentAuthorizationPage } from '@/pages/customer/payment-authorization';
import { OrderTrackingPage } from '@/pages/customer/order-tracking';
import { OrderHistoryPage } from '@/pages/customer/order-history';
import { AvailableOrdersPage } from '@/pages/runner/available-orders';
import { ActiveOrdersPage } from '@/pages/runner/active-orders';
import { useUser } from '@/lib/hooks/use-user';

function RequireUser({ children }: { children: React.ReactNode }) {
  const { id } = useUser();
  if (!id) return <Navigate to="/user-select" replace />;
  return <>{children}</>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/user-select" element={<UserSelectPage />} />
      
      <Route element={<RequireUser><RootLayout /></RequireUser>}>
        <Route path="/" element={<HomePage />} />
        <Route path="/role-select" element={<RoleSelector />} />
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