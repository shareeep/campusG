import { Request, Response } from 'express';
import { PrismaClient } from '@prisma/client';
import { clerkClient } from '@clerk/clerk-sdk-node';
import { AuthenticatedRequest } from '../middleware/authMiddleware';
import kafkaClient from '../services/kafkaService';

const prisma = new PrismaClient();

// Register a new user - primarily handled by Clerk, we just sync our database
const registerUser = async (req: Request, res: Response) => {
  try {
    const { email, firstName, lastName, role, paymentDetails } = req.body;

    // Validate input
    if (!email) {
      return res.status(400).json({ error: 'Email is required' });
    }

    // Create a user record in our database
    const user = await prisma.user.create({
      data: {
        email,
        firstName,
        lastName,
        role: role || 'CUSTOMER', // Default to customer
        paymentDetails: paymentDetails || {},
        preferences: {}
      }
    });

    // Publish a user creation event to Kafka
    await kafkaClient.publish('user-events', {
      type: 'USER_CREATED',
      payload: {
        userId: user.id,
        email: user.email,
        role: user.role
      }
    });

    res.status(201).json({ 
      message: 'User registered successfully',
      userId: user.id
    });
  } catch (error) {
    console.error('Error registering user:', error);
    res.status(500).json({ error: 'Failed to register user' });
  }
};

// Login is handled by Clerk, this is just a placeholder that would
// normally verify credentials and return a token
const loginUser = async (req: Request, res: Response) => {
  // Authentication is handled by Clerk, this endpoint would just
  // return user information after successful authentication
  res.status(200).json({ message: 'Login is handled by Clerk authentication' });
};

// Get the authenticated user's profile
const getUserProfile = async (req: Request, res: Response) => {
  try {
    const authReq = req as AuthenticatedRequest;
    const userId = authReq.auth.userId;

    // Get user from database
    const user = await prisma.user.findUnique({
      where: { id: userId }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Return user information (excluding sensitive data)
    res.status(200).json({
      id: user.id,
      email: user.email,
      firstName: user.firstName,
      lastName: user.lastName,
      role: user.role,
      preferences: user.preferences
    });
  } catch (error) {
    console.error('Error getting user profile:', error);
    res.status(500).json({ error: 'Failed to get user profile' });
  }
};

// Update the authenticated user's profile
const updateUserProfile = async (req: Request, res: Response) => {
  try {
    const authReq = req as AuthenticatedRequest;
    const userId = authReq.auth.userId;
    const { firstName, lastName, preferences } = req.body;

    // Update user in database
    const updatedUser = await prisma.user.update({
      where: { id: userId },
      data: {
        firstName,
        lastName,
        preferences: preferences || undefined
      }
    });

    // Publish a user update event to Kafka
    await kafkaClient.publish('user-events', {
      type: 'USER_UPDATED',
      payload: {
        userId: updatedUser.id,
        firstName: updatedUser.firstName,
        lastName: updatedUser.lastName
      }
    });

    res.status(200).json({
      message: 'Profile updated successfully',
      user: {
        id: updatedUser.id,
        email: updatedUser.email,
        firstName: updatedUser.firstName,
        lastName: updatedUser.lastName,
        role: updatedUser.role,
        preferences: updatedUser.preferences
      }
    });
  } catch (error) {
    console.error('Error updating user profile:', error);
    res.status(500).json({ error: 'Failed to update profile' });
  }
};

// Get the authenticated user's payment details
const getPaymentDetails = async (req: Request, res: Response) => {
  try {
    const authReq = req as AuthenticatedRequest;
    const userId = authReq.auth.userId;

    // Get user from database
    const user = await prisma.user.findUnique({
      where: { id: userId }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Return payment details
    res.status(200).json({
      paymentDetails: user.paymentDetails
    });
  } catch (error) {
    console.error('Error getting payment details:', error);
    res.status(500).json({ error: 'Failed to get payment details' });
  }
};

// Update the authenticated user's payment details
const updatePaymentDetails = async (req: Request, res: Response) => {
  try {
    const authReq = req as AuthenticatedRequest;
    const userId = authReq.auth.userId;
    const { paymentDetails } = req.body;

    if (!paymentDetails) {
      return res.status(400).json({ error: 'Payment details are required' });
    }

    // Update user in database
    const updatedUser = await prisma.user.update({
      where: { id: userId },
      data: {
        paymentDetails
      }
    });

    // Publish a payment details update event to Kafka
    await kafkaClient.publish('user-events', {
      type: 'PAYMENT_DETAILS_UPDATED',
      payload: {
        userId: updatedUser.id
      }
    });

    res.status(200).json({
      message: 'Payment details updated successfully'
    });
  } catch (error) {
    console.error('Error updating payment details:', error);
    res.status(500).json({ error: 'Failed to update payment details' });
  }
};

// ---- Admin functions ----

// Get all users (admin only)
const getAllUsers = async (req: Request, res: Response) => {
  try {
    // Get all users from database
    const users = await prisma.user.findMany({
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        role: true,
        createdAt: true,
        updatedAt: true
      }
    });

    res.status(200).json(users);
  } catch (error) {
    console.error('Error getting all users:', error);
    res.status(500).json({ error: 'Failed to get users' });
  }
};

// Get user by ID (admin only)
const getUserById = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    // Get user from database
    const user = await prisma.user.findUnique({
      where: { id }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Return user information (excluding sensitive data)
    res.status(200).json({
      id: user.id,
      email: user.email,
      firstName: user.firstName,
      lastName: user.lastName,
      role: user.role,
      createdAt: user.createdAt,
      updatedAt: user.updatedAt
    });
  } catch (error) {
    console.error('Error getting user by ID:', error);
    res.status(500).json({ error: 'Failed to get user' });
  }
};

// Delete a user (admin only)
const deleteUser = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;

    // Check if user exists
    const user = await prisma.user.findUnique({
      where: { id }
    });

    if (!user) {
      return res.status(404).json({ error: 'User not found' });
    }

    // Delete user from database
    await prisma.user.delete({
      where: { id }
    });

    // Publish a user deletion event to Kafka
    await kafkaClient.publish('user-events', {
      type: 'USER_DELETED',
      payload: {
        userId: id
      }
    });

    res.status(200).json({
      message: 'User deleted successfully'
    });
  } catch (error) {
    console.error('Error deleting user:', error);
    res.status(500).json({ error: 'Failed to delete user' });
  }
};

export default {
  registerUser,
  loginUser,
  getUserProfile,
  updateUserProfile,
  getPaymentDetails,
  updatePaymentDetails,
  getAllUsers,
  getUserById,
  deleteUser
};
