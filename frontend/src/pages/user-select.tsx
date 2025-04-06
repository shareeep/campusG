import { useNavigate } from 'react-router-dom';
import { User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useRole } from '@/lib/hooks/use-role';
import { useUser } from '@/lib/hooks/use-user';

const users = [
  { id: 'alice', name: 'Alice', defaultRole: 'customer' },
  { id: 'ray', name: 'Ray', defaultRole: 'runner' }
];

export function UserSelectPage() {
  const navigate = useNavigate();
  const { setRole } = useRole();
  const { setUser } = useUser();

  const handleUserSelect = (userId: string, defaultRole: string) => {
    const user = users.find(u => u.id === userId);
    if (!user) return;
    
    // Set user info using the hook
    setUser(user.id, user.name);
    
    // Set initial role
    setRole(defaultRole as 'customer' | 'runner');
    
    // Navigate based on the default role
    if (defaultRole === 'customer') {
      navigate('/customer/order');
    } else {
      navigate('/runner/available-orders');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold mb-2">Welcome to CampusG</h1>
          <p className="text-gray-600">Choose a user to continue</p>
        </div>

        <div className="space-y-4">
          {users.map((user) => (
            <Button
              key={user.id}
              onClick={() => handleUserSelect(user.id, user.defaultRole)}
              variant="outline"
              className="w-full h-auto p-4 flex items-center justify-start hover:border-blue-500 hover:bg-blue-50"
            >
              <div className="flex items-center w-full">
                <div className="flex-shrink-0 p-2 bg-blue-50 rounded-lg">
                  <User className="h-6 w-6 text-blue-600" />
                </div>
                <div className="ml-4 text-left">
                  <h3 className="font-semibold">{user.name}</h3>
                  <p className="text-sm text-gray-600">
                    Default role: {user.defaultRole.charAt(0).toUpperCase() + user.defaultRole.slice(1)}
                  </p>
                </div>
              </div>
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}