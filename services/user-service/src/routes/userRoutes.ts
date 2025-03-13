import express from 'express';
import userController from '../controllers/userController';
import authMiddleware from '../middleware/authMiddleware';

const router = express.Router();

// Public routes
router.post('/register', userController.registerUser);
router.post('/login', userController.loginUser);

// Protected routes
router.get('/profile', authMiddleware.requireAuth, userController.getUserProfile);
router.put('/profile', authMiddleware.requireAuth, userController.updateUserProfile);
router.get('/payment-details', authMiddleware.requireAuth, userController.getPaymentDetails);
router.put('/payment-details', authMiddleware.requireAuth, userController.updatePaymentDetails);

// Admin routes
router.get('/', authMiddleware.requireAuth, authMiddleware.requireAdmin, userController.getAllUsers);
router.get('/:id', authMiddleware.requireAuth, authMiddleware.requireAdmin, userController.getUserById);
router.delete('/:id', authMiddleware.requireAuth, authMiddleware.requireAdmin, userController.deleteUser);

export default router;
