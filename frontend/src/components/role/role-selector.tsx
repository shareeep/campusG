import { useNavigate } from 'react-router-dom';
import { Bike, ShoppingBag } from 'lucide-react';
import { useRole } from '@/lib/hooks/use-role';
import type { UserRole } from '@/lib/types';
import { useState, useEffect } from 'react';

interface RoleOption {
  id: UserRole;
  title: string;
  description: string;
  icon: typeof Bike | typeof ShoppingBag;
  path: string;
  color: {
    bg: string;
    text: string;
    hover: string;
  };
}

const roles: RoleOption[] = [
  {
    id: "customer",
    title: "Order Food",
    description: "Easily order from on-campus restaurants and stores near you!",
    icon: ShoppingBag,
    path: "/customer/order",
    color: {
      bg: "bg-blue-50",
      text: "text-blue-600",
      hover: "hover:border-blue-500",
    },
  },
  {
    id: "runner",
    title: "Deliver Food",
    description: "Maximize your earnings: Deliver food when it works for you.",
    icon: Bike,
    path: "/runner/available-orders",
    color: {
      bg: "bg-green-50",
      text: "text-green-600",
      hover: "hover:border-green-500",
    },
  },
];

export function RoleSelector() {
  const navigate = useNavigate();
  const { role, setRole } = useRole();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // This simulates waiting for any necessary data to load
    // You can replace this with actual data loading if needed
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 300);
    
    return () => clearTimeout(timer);
  }, []);

  const handleRoleSelect = (selectedRole: RoleOption) => {
    setRole(selectedRole.id);
    navigate(selectedRole.path);
  };

  if (isLoading) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Preparing your options...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 flex items-center justify-center overflow-hidden">
      <div className="max-w-md w-full px-4">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold mb-1">
            {role ? 'Switch Roles' : 'Welcome to CampusG!'}
          </h1>
          <p className="text-gray-600">
            {role ? 'Choose a different role' : 'Choose how you\'d like to use CampusG today'}
          </p>
        </div>

        <div className="space-y-3">
          {roles.map((roleOption) => (
            <button
              key={roleOption.id}
              onClick={() => handleRoleSelect(roleOption)}
              className={`w-full bg-white rounded-lg border p-5 transition-all duration-200 ${
                role === roleOption.id
                  ? `border-2 ${roleOption.color.hover.replace('hover:', '')} ${roleOption.color.bg}`
                  : `hover:shadow-md ${roleOption.color.hover}`
              }`}
            >
              <div className="flex items-start">
                <div className={`flex-shrink-0 p-3 rounded-lg ${roleOption.color.bg}`}>
                  <roleOption.icon className={`h-6 w-6 ${roleOption.color.text}`} />
                </div>
                <div className="ml-4 text-left">
                  <h3 className="text-xl font-semibold mb-1">{roleOption.title}</h3>
                  <p className="text-gray-600">{roleOption.description}</p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <p className="text-center text-sm text-gray-500 mt-6">
          You can switch roles anytime from the menu
        </p>
      </div>
    </div>
  );
}