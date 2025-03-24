import { ReactNode } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';

// Replace with your Stripe publishable key - this should be in an environment variable in production
const stripePromise = loadStripe('pk_test_51R3w7tQR8BO665MwdItLEUCpoGtnkeSyXbD2yiyGs7BpkLREWVqndrcJD9XVetcGMJLjdcm5YZ5yP3Zf06x3WW4w00pzCEey01');

interface StripeProviderProps {
  children: ReactNode;
}

export function StripeProvider({ children }: StripeProviderProps) {
  return (
    <Elements stripe={stripePromise}>
      {children}
    </Elements>
  );
}
