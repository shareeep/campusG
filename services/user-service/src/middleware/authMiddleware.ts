import { Request, Response, NextFunction } from 'express';
import { clerkClient, ClerkExpressRequireAuth } from '@clerk/clerk-sdk-node';
import config from '../config';

// Define extended request interface with user information
export interface AuthenticatedRequest extends Request {
  auth: {
    userId: string;
    sessionId: string;
    role?: string;
  };
}

// Clerk authentication middleware
const requireAuth = ClerkExpressRequireAuth({
  // Optional configuration
  onError: (err, req, res) => {
    console.error('Authentication error:', err);
    res.status(401).json({ error: 'Unauthorized' });
  },
});

// Check if user has admin role
const requireAdmin = async (req: Request, res: Response, next: NextFunction) => {
  try {
    // Cast to our authenticated request interface
    const authReq = req as AuthenticatedRequest;
    
    if (!authReq.auth?.userId) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    // Fetch user from Clerk
    const user = await clerkClient.users.getUser(authReq.auth.userId);
    
    // Check if user has admin role (using public metadata in Clerk)
    // Note: You'll need to set this in Clerk for admin users
    if (user.publicMetadata.role !== 'ADMIN') {
      return res.status(403).json({ error: 'Forbidden' });
    }
    
    // Store role in auth object for later use
    authReq.auth.role = 'ADMIN';
    
    next();
  } catch (error) {
    console.error('Admin authorization error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
};

export default {
  requireAuth,
  requireAdmin
};
