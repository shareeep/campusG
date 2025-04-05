import { useState, useEffect } from 'react';
import { Bell } from 'lucide-react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { Button } from '@/components/ui/button';
import { getNotifications, markNotificationAsRead } from '@/lib/api';
import { useUser } from '@/lib/hooks/use-user';
import type { Notification } from '@/lib/types';

export function NotificationDropdown() {
  const { id: userId } = useUser();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const fetchNotifications = async () => {
      if (!userId) return;
      const userNotifications = await getNotifications(userId);
      setNotifications(userNotifications.sort((a, b) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ));
    };

    fetchNotifications();
    const interval = setInterval(fetchNotifications, 5000);
    return () => clearInterval(interval);
  }, [userId]);

  const unreadCount = notifications.filter(n => !n.read).length;

  const handleNotificationClick = async (notificationId: string) => {
    await markNotificationAsRead(notificationId);
    setNotifications(notifications.map(n =>
      n.id === notificationId ? { ...n, read: true } : n
    ));
  };

  return (
    <DropdownMenu.Root open={open} onOpenChange={setOpen}>
      <DropdownMenu.Trigger asChild>
        <Button variant="ghost" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center">
              {unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="w-80 bg-white rounded-lg shadow-lg border p-2 z-50"
          align="end"
        >
          <div className="px-4 py-2 border-b">
            <h3 className="font-semibold">Notifications</h3>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                No notifications
              </div>
            ) : (
              notifications.map((notification) => (
                <DropdownMenu.Item
                  key={notification.id}
                  className={`
                    px-4 py-3 cursor-pointer hover:bg-gray-50
                    ${notification.read ? 'opacity-70' : 'bg-blue-50'}
                  `}
                  onClick={() => handleNotificationClick(notification.id)}
                >
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{notification.title}</span>
                      <span className="text-xs text-gray-500">
                        {new Date(notification.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{notification.message}</p>
                  </div>
                </DropdownMenu.Item>
              ))
            )}
          </div>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}