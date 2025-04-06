import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRole } from '@/lib/hooks/use-role';
import type { UserRole } from '@/lib/types';

interface RoleGuardProps {
  children: React.ReactNode;
  allowedRole: UserRole;
}

export function RoleGuard({ children, allowedRole }: RoleGuardProps) {
  const navigate = useNavigate();
  const { role } = useRole();

  useEffect(() => {
    if (!role) {
      navigate('/role-select');
    } else if (role !== allowedRole) {
      navigate(role === 'customer' ? '/customer/order' : '/runner/available-orders');
    }
  }, [role, allowedRole, navigate]);

  return role === allowedRole ? <>{children}</> : null;
}