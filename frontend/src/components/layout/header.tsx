import { ShoppingBag, Bike, History, LogOut, User, ShoppingCart, ClipboardList, Clock } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useRole } from '@/lib/hooks/use-role';
import { useAuth, useUser as useClerkUser } from '@clerk/clerk-react';
import { useState } from 'react';

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const { role } = useRole();
  const { signOut } = useAuth();
  const { user } = useClerkUser();

  const handleLogout = async () => {
    await signOut();
    navigate('/');
  };

  const isCustomer = role === 'customer';
  const bgColor = isCustomer ? 'bg-blue-100' : 'bg-green-100';
  const borderColor = isCustomer ? 'border-blue-200' : 'border-green-200';
  const textColor = isCustomer ? 'text-blue-600' : 'text-green-600';
  const hoverColor = isCustomer ? 'hover:text-blue-700' : 'hover:text-green-700';

  return (
    <header className={`sticky top-0 z-50 w-full border-b ${bgColor} ${borderColor}`}>
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <div className="flex items-center">
          <Link to="/" className="flex items-center space-x-2">
            <ShoppingBag className={`h-6 w-6 ${textColor}`} />
            <span className="text-xl font-bold">CampusG</span>
          </Link>
        </div>
        
        {/* Mobile menu button - visible on small and medium screens (up to 768px) */}
        <div className="md:hidden">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className={`p-2 focus:outline-none ${textColor}`}
            aria-label="Toggle mobile menu"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
        
        {/* Desktop navigation - hidden on mobile and tablet */}
        <nav className="hidden md:flex items-center space-x-6">
          {isCustomer ? (
            <>
              <Link to="/customer/order" className={`text-sm font-medium ${hoverColor} flex items-center`}>
                <ShoppingCart className="h-4 w-4 inline-block mr-1" />
                Place Order
              </Link>
              <Link to="/customer/history" className={`text-sm font-medium ${hoverColor}`}>
                <History className="h-4 w-4 inline-block mr-1" />
                Order History
              </Link>
            </>
          ) : (
            <>
              <Link to="/runner/available-orders" className={`text-sm font-medium ${hoverColor} flex items-center`}>
                <ClipboardList className="h-4 w-4 inline-block mr-1" />
                Available Orders
              </Link>
              <Link to="/runner/active-orders" className={`text-sm font-medium ${hoverColor} flex items-center`}>
                <Clock className="h-4 w-4 inline-block mr-1" />
                Active Orders
              </Link>
            </>
          )}
          
          <Link 
            to="/role-select" 
            className={`flex items-center space-x-1 text-sm font-medium ${
              isCustomer ? 'hover:text-green-700' : 'hover:text-blue-700'
            }`}
          >
            {isCustomer ? (
              <>
                <Bike className="h-4 w-4" />
                <span>Switch to Runner</span>
              </>
            ) : (
              <>
                <ShoppingBag className="h-4 w-4" />
                <span>Switch to Customer</span>
              </>
            )}
          </Link>
          
          {/* Profile Link */}
          <Link to="/profile" className={`flex items-center text-sm font-medium ${hoverColor}`}>
            <User className="h-4 w-4 mr-1" /> 
            {user?.firstName || 'Profile'}
          </Link>

          {/* Logout Button */}
          <button 
            onClick={handleLogout} 
            title="Sign Out" 
            className={`flex items-center text-sm font-medium ${hoverColor} p-0 bg-transparent border-none cursor-pointer`}
          >
            <LogOut className="h-4 w-4" />
          </button>
        </nav>
      </div>
      
      {/* Mobile menu dropdown - visible on mobile and tablet */}
      {mobileMenuOpen && (
        <div className={`md:hidden w-full ${bgColor} border-t ${borderColor}`}>
          <div className="container mx-auto px-4 py-2 flex flex-col space-y-2">
            {isCustomer ? (
              <>
                <Link 
                  to="/customer/order" 
                  className={`text-sm font-medium p-2 ${hoverColor} flex items-center`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <ShoppingCart className="h-4 w-4 inline-block mr-1" />
                  Place Order
                </Link>
                <Link 
                  to="/customer/history" 
                  className={`text-sm font-medium p-2 ${hoverColor} flex items-center`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <History className="h-4 w-4 inline-block mr-1" />
                  Order History
                </Link>
              </>
            ) : (
              <>
                <Link 
                  to="/runner/available-orders" 
                  className={`text-sm font-medium p-2 ${hoverColor} flex items-center`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <ClipboardList className="h-4 w-4 inline-block mr-1" />
                  Available Orders
                </Link>
                <Link 
                  to="/runner/active-orders" 
                  className={`text-sm font-medium p-2 ${hoverColor} flex items-center`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <Clock className="h-4 w-4 inline-block mr-1" />
                  Active Orders
                </Link>
              </>
            )}
            
            <Link 
              to="/role-select" 
              className={`text-sm font-medium p-2 flex items-center ${
                isCustomer ? 'hover:text-green-700' : 'hover:text-blue-700'
              }`}
              onClick={() => setMobileMenuOpen(false)}
            >
              {isCustomer ? (
                <>
                  <Bike className="h-4 w-4 mr-1" />
                  <span>Switch to Runner</span>
                </>
              ) : (
                <>
                  <ShoppingBag className="h-4 w-4 mr-1" />
                  <span>Switch to Customer</span>
                </>
              )}
            </Link>
            
            <Link 
              to="/profile" 
              className={`text-sm font-medium p-2 flex items-center ${hoverColor}`}
              onClick={() => setMobileMenuOpen(false)}
            >
              <User className="h-4 w-4 mr-1" />
              {user?.firstName || 'Profile'}
            </Link>
            
            <button 
              onClick={() => {
                setMobileMenuOpen(false);
                handleLogout();
              }} 
              className={`text-sm font-medium p-2 flex items-center ${hoverColor} text-left w-full bg-transparent border-none`}
            >
              <LogOut className="h-4 w-4 mr-1" />
              Sign Out
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
