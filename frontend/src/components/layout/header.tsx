import { ShoppingBag, Bike, History, LogOut, User } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useRole } from '@/lib/hooks/use-role';
import { useUser } from '@/lib/hooks/use-user';
import { NotificationDropdown } from '@/components/notifications/notification-dropdown';

export function Header() {
  const navigate = useNavigate();
  const { role, switchRole } = useRole();
  const { name, clearUser } = useUser();

  const handleLogout = () => {
    clearUser();
    navigate('/user-select');
  };

  const isCustomer = role === 'customer';
  const bgColor = isCustomer ? 'bg-blue-100' : 'bg-green-100';
  const borderColor = isCustomer ? 'border-blue-200' : 'border-green-200';
  const textColor = isCustomer ? 'text-blue-600' : 'text-green-600';
  const badgeBg = isCustomer ? 'bg-blue-200' : 'bg-green-200';
  const badgeText = isCustomer ? 'text-blue-800' : 'text-green-800';
  const hoverColor = isCustomer ? 'hover:text-blue-700' : 'hover:text-green-700';

  return (
    <header className={`sticky top-0 z-50 w-full border-b ${bgColor} ${borderColor}`}>
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <div className="flex items-center space-x-4">
          <Link to="/" className="flex items-center space-x-2">
            <ShoppingBag className={`h-6 w-6 ${textColor}`} />
            <span className="text-xl font-bold">CampusG</span>
          </Link>
          <div className={`px-3 py-1 rounded-full text-sm font-medium ${badgeBg} ${badgeText}`}>
            {isCustomer ? (
              <>
                <ShoppingBag className="h-4 w-4 inline-block mr-1" />
                Customer
              </>
            ) : (
              <>
                <Bike className="h-4 w-4 inline-block mr-1" />
                Runner
              </>
            )}
          </div>
        </div>
        
        <nav className="flex items-center space-x-6">
          {isCustomer ? (
            <>
              <Link to="/customer/order" className={`text-sm font-medium ${hoverColor}`}>
                Place Order
              </Link>
              <Link to="/customer/history" className={`text-sm font-medium ${hoverColor}`}>
                <History className="h-4 w-4 inline-block mr-1" />
                Order History
              </Link>
            </>
          ) : (
            <>
              <Link to="/runner/available-orders" className={`text-sm font-medium ${hoverColor}`}>
                Available Orders
              </Link>
              <Link to="/runner/active-orders" className={`text-sm font-medium ${hoverColor}`}>
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
          
          <div className="flex items-center space-x-4">
            <NotificationDropdown />
            <Link to="/profile" className={`text-sm font-medium ${hoverColor}`}>
              <User className="h-4 w-4" />
            </Link>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </nav>
      </div>
    </header>
  );
}