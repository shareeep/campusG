import { useNavigate } from 'react-router-dom';
import { Bike, ShoppingBag } from 'lucide-react';
import { useRole } from '@/lib/hooks/use-role';
import type { UserRole } from '@/lib/types';

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
    id: 'customer',
    title: 'Order Food',
    description: 'Browse restaurants and place orders for delivery',
    icon: ShoppingBag,
    path: '/customer/order',
    color: {
      bg: 'bg-blue-50',
      text: 'text-blue-600',
      hover: 'hover:border-blue-500'
    }
  },
  {
    id: 'runner',
    title: 'Deliver Food',
    description: 'Accept orders and earn money delivering food',
    icon: Bike,
    path: '/runner/available-orders',
    color: {
      bg: 'bg-green-50',
      text: 'text-green-600',
      hover: 'hover:border-green-500'
    }
  }
];

export function RoleSelector() {
  const navigate = useNavigate();
  const { role, setRole } = useRole();

  const handleRoleSelect = (selectedRole: RoleOption) => {
    setRole(selectedRole.id);
    navigate(selectedRole.path);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold mb-2">
            {role ? 'Switch Roles' : 'Welcome to CampusG!'}
          </h1>
          <p className="text-gray-600">
            {role ? 'Choose a different role' : 'Choose how you\'d like to use CampusG today'}
          </p>
        </div>

        <div className="space-y-4">
          {roles.map((roleOption) => (
            <button
              key={roleOption.id}
              onClick={() => handleRoleSelect(roleOption)}
              className={`w-full bg-white rounded-lg border p-6 transition-all duration-200 ${
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

        <p className="text-center text-sm text-gray-500 mt-8">
          You can switch roles anytime from the menu
        </p>
      </div>
    </div>
  );
}