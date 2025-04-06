import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function initializeStorage() {
  // Initialize orders if not present
  if (!localStorage.getItem('orders')) {
    localStorage.setItem('orders', '[]');
  }
  
  // Initialize notifications if not present
  if (!localStorage.getItem('notifications')) {
    localStorage.setItem('notifications', '[]');
  }
}