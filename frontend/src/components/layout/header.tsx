import { ShoppingBag, CreditCard } from 'lucide-react';
import { Link } from 'react-router-dom';
import { SignedIn, SignedOut, UserButton } from '@clerk/clerk-react';
import { Button } from '@/components/ui/button';

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <Link to="/" className="flex items-center space-x-2">
          <ShoppingBag className="h-6 w-6 text-blue-600" />
          <span className="text-xl font-bold">CampusG</span>
        </Link>
        
        <nav className="flex items-center space-x-6">
          <SignedIn>
            <Link to="/restaurants" className="text-sm font-medium hover:text-blue-600">
              Restaurants
            </Link>
            <Link to="/customer/order-form" className="text-sm font-medium hover:text-blue-600">
              Place Order
            </Link>
            <Link to="/runner/available-orders" className="text-sm font-medium hover:text-blue-600">
              Runner Dashboard
            </Link>
            <Link to="/payment-settings" className="text-sm font-medium hover:text-blue-600">
              <div className="flex items-center gap-1">
                <CreditCard className="h-4 w-4" />
                <span>Payment Settings</span>
              </div>
            </Link>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
          <SignedOut>
            <Link to="/sign-in">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link to="/sign-up">
              <Button size="sm">
                Sign Up
              </Button>
            </Link>
          </SignedOut>
        </nav>
      </div>
    </header>
  );
}
