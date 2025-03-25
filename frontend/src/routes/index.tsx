import { Routes, Route } from 'react-router-dom';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/clerk-react';
import { RootLayout } from '@/components/layout/root-layout';
import { AuthLayout } from '@/components/layout/auth-layout';
import { SignInPage } from '@/pages/auth/sign-in';
import { SignUpPage } from '@/pages/auth/sign-up';
import { HomePage } from '@/pages/home';
import { RestaurantsPage } from '@/pages/restaurants';
import { BecomeRunnerPage } from '@/pages/become-runner';
import { OrderFormPage } from '@/pages/customer/order-form';
import { AvailableOrdersPage } from '@/pages/runner/available-orders';
import PaymentSettingsPage from '@/pages/payment-settings';

export function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route element={<RootLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/sign-in/*" element={<AuthLayout><SignInPage /></AuthLayout>} />
        <Route path="/sign-up/*" element={<AuthLayout><SignUpPage /></AuthLayout>} />
      </Route>

      {/* Protected routes */}
      <Route element={<RootLayout />}>
        <Route
          path="/restaurants"
          element={
            <>
              <SignedIn>
                <RestaurantsPage />
              </SignedIn>
              <SignedOut>
                <RedirectToSignIn />
              </SignedOut>
            </>
          }
        />
        <Route
          path="/become-runner"
          element={
            <>
              <SignedIn>
                <BecomeRunnerPage />
              </SignedIn>
              <SignedOut>
                <RedirectToSignIn />
              </SignedOut>
            </>
          }
        />
        <Route
          path="/customer/order-form"
          element={
            <>
              <SignedIn>
                <OrderFormPage />
              </SignedIn>
              <SignedOut>
                <RedirectToSignIn />
              </SignedOut>
            </>
          }
        />
        <Route
          path="/runner/available-orders"
          element={
            <>
              <SignedIn>
                <AvailableOrdersPage />
              </SignedIn>
              <SignedOut>
                <RedirectToSignIn />
              </SignedOut>
            </>
          }
        />
        <Route
          path="/payment-settings"
          element={
            <>
              <SignedIn>
                <PaymentSettingsPage />
              </SignedIn>
              <SignedOut>
                <RedirectToSignIn />
              </SignedOut>
            </>
          }
        />
      </Route>
    </Routes>
  );
}
