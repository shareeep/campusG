import { PrismaClient } from '@prisma/client';
import axios from 'axios';
import config from '../config';
import kafkaClient from '../services/kafkaService';

const prisma = new PrismaClient();

/**
 * Create Order Saga
 * 
 * This saga orchestrates the process of creating a new order:
 * 1. Validate customer details
 * 2. Create order record
 * 3. Authorize payment
 * 4. Hold funds in escrow
 * 5. Start order timeout timer
 * 6. Send notifications
 */
export class CreateOrderSaga {
  private orderId: string;
  private customerId: string;
  private orderDetails: any;
  private paymentAmount: number;

  constructor(customerId: string, orderDetails: any) {
    this.customerId = customerId;
    this.orderDetails = orderDetails;
    this.paymentAmount = this.calculateTotal(orderDetails);
    this.orderId = '';
  }

  /**
   * Start the create order saga
   */
  async execute(): Promise<{ success: boolean; orderId?: string; error?: string }> {
    try {
      // Step 1: Validate customer
      const customerValid = await this.validateCustomer();
      if (!customerValid.success) {
        return { success: false, error: customerValid.error };
      }

      // Step 2: Create order record
      const orderCreated = await this.createOrder();
      if (!orderCreated.success) {
        return { success: false, error: orderCreated.error };
      }

      // Step 3: Authorize payment
      const paymentAuthorized = await this.authorizePayment();
      if (!paymentAuthorized.success) {
        // Compensating transaction: update order status to failed
        await this.updateOrderStatus('CANCELLED');
        return { success: false, error: paymentAuthorized.error };
      }

      // Step 4: Hold funds in escrow
      const fundsHeld = await this.holdFundsInEscrow();
      if (!fundsHeld.success) {
        // Compensating transaction: release payment authorization
        await this.releasePaymentAuthorization();
        await this.updateOrderStatus('CANCELLED');
        return { success: false, error: fundsHeld.error };
      }

      // Step 5: Start order timeout timer
      await this.startOrderTimeoutTimer();

      // Step 6: Send notifications
      await this.sendNotifications();

      // Update order status to ready for pickup
      await this.updateOrderStatus('READY_FOR_PICKUP');

      // Success
      return {
        success: true,
        orderId: this.orderId
      };
    } catch (error) {
      console.error('Error executing Create Order saga:', error);
      
      // Attempt to clean up if possible
      if (this.orderId) {
        await this.updateOrderStatus('CANCELLED');
      }
      
      return { 
        success: false, 
        error: `Unexpected error: ${error instanceof Error ? error.message : String(error)}` 
      };
    }
  }

  /**
   * Validate the customer exists and has valid payment method
   */
  private async validateCustomer(): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await axios.get(`${config.services.userService}/api/users/${this.customerId}`);
      const customer = response.data;

      if (!customer) {
        return { success: false, error: 'Customer not found' };
      }

      if (!customer.paymentDetails) {
        return { success: false, error: 'Customer has no payment method' };
      }

      return { success: true };
    } catch (error) {
      console.error('Error validating customer:', error);
      return { 
        success: false, 
        error: `Failed to validate customer: ${error instanceof Error ? error.message : String(error)}` 
      };
    }
  }

  /**
   * Create the order record in the database
   */
  private async createOrder(): Promise<{ success: boolean; error?: string }> {
    try {
      const { foodItems, deliveryLocation } = this.orderDetails;
      
      const foodFee = this.calculateFoodTotal(foodItems);
      const deliveryFee = this.calculateDeliveryFee(deliveryLocation);

      const order = await prisma.order.create({
        data: {
          custId: this.customerId,
          orderDescription: JSON.stringify(foodItems),
          foodFee,
          deliveryFee,
          deliveryLocation,
          paymentStatus: 'PENDING',
          orderStatus: 'CREATED',
          startTime: new Date(),
        }
      });

      this.orderId = order.id;

      // Publish order created event
      await kafkaClient.publish('order-events', {
        type: 'ORDER_CREATED',
        payload: {
          orderId: order.id,
          customerId: this.customerId,
          amount: foodFee + deliveryFee
        }
      });

      return { success: true };
    } catch (error) {
      console.error('Error creating order:', error);
      return { 
        success: false, 
        error: `Failed to create order: ${error instanceof Error ? error.message : String(error)}` 
      };
    }
  }

  /**
   * Authorize payment with payment service
   */
  private async authorizePayment(): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await axios.post(`${config.services.paymentService}/api/payments/authorize`, {
        orderId: this.orderId,
        customerId: this.customerId,
        amount: this.paymentAmount
      });

      if (!response.data.success) {
        return { success: false, error: response.data.message || 'Payment authorization failed' };
      }

      // Update order payment status
      await prisma.order.update({
        where: { id: this.orderId },
        data: { paymentStatus: 'AUTHORIZED' }
      });

      return { success: true };
    } catch (error) {
      console.error('Error authorizing payment:', error);
      return { 
        success: false, 
        error: `Failed to authorize payment: ${error instanceof Error ? error.message : String(error)}` 
      };
    }
  }

  /**
   * Hold funds in escrow
   */
  private async holdFundsInEscrow(): Promise<{ success: boolean; error?: string }> {
    try {
      const order = await prisma.order.findUnique({
        where: { id: this.orderId }
      });

      if (!order) {
        return { success: false, error: 'Order not found' };
      }

      const response = await axios.post(`${config.services.escrowService}/api/escrow/hold`, {
        orderId: this.orderId,
        customerId: this.customerId,
        amount: this.paymentAmount,
        foodFee: order.foodFee,
        deliveryFee: order.deliveryFee
      });

      if (!response.data.success) {
        return { success: false, error: response.data.message || 'Failed to hold funds in escrow' };
      }

      return { success: true };
    } catch (error) {
      console.error('Error holding funds in escrow:', error);
      return { 
        success: false, 
        error: `Failed to hold funds in escrow: ${error instanceof Error ? error.message : String(error)}` 
      };
    }
  }

  /**
   * Release payment authorization (compensating transaction)
   */
  private async releasePaymentAuthorization(): Promise<void> {
    try {
      await axios.post(`${config.services.paymentService}/api/payments/release`, {
        orderId: this.orderId
      });
    } catch (error) {
      console.error('Error releasing payment authorization:', error);
      // We log but don't rethrow as this is a compensating transaction
    }
  }

  /**
   * Start order timeout timer
   */
  private async startOrderTimeoutTimer(): Promise<void> {
    try {
      // Schedule an event 30 minutes in the future
      const timeoutAt = new Date();
      timeoutAt.setMinutes(timeoutAt.getMinutes() + 30);

      await axios.post(`${config.services.schedulerService}/api/schedule`, {
        eventType: 'ORDER_TIMEOUT',
        entityId: this.orderId,
        scheduledTime: timeoutAt.toISOString(),
        payload: {
          orderId: this.orderId,
          customerId: this.customerId
        }
      });
    } catch (error) {
      console.error('Error scheduling order timeout:', error);
      // We continue despite errors here, as the order can still be processed
    }
  }

  /**
   * Send notifications about order creation
   */
  private async sendNotifications(): Promise<void> {
    try {
      await axios.post(`${config.services.notificationService}/api/notifications`, {
        recipientId: this.customerId,
        recipientType: 'CUSTOMER',
        notificationType: 'ORDER_CREATED',
        title: 'Order Created',
        message: `Your order #${this.orderId} has been created and is being processed.`,
        data: {
          orderId: this.orderId
        },
        channel: 'APP'
      });
    } catch (error) {
      console.error('Error sending notification:', error);
      // We continue despite notification errors
    }
  }

  /**
   * Update order status
   */
  private async updateOrderStatus(status: string): Promise<void> {
    try {
      await prisma.order.update({
        where: { id: this.orderId },
        data: { orderStatus: status }
      });

      // Publish order status updated event
      await kafkaClient.publish('order-events', {
        type: 'ORDER_STATUS_UPDATED',
        payload: {
          orderId: this.orderId,
          status
        }
      });
    } catch (error) {
      console.error(`Error updating order status to ${status}:`, error);
      // Status update failure should not stop the flow
    }
  }

  /**
   * Calculate the total amount for the order
   */
  private calculateTotal(orderDetails: any): number {
    const foodTotal = this.calculateFoodTotal(orderDetails.foodItems);
    const deliveryFee = this.calculateDeliveryFee(orderDetails.deliveryLocation);
    return foodTotal + deliveryFee;
  }

  /**
   * Calculate the food total
   */
  private calculateFoodTotal(foodItems: any[]): number {
    return foodItems.reduce((total, item) => {
      return total + (item.price * item.quantity);
    }, 0);
  }

  /**
   * Calculate delivery fee based on location
   */
  private calculateDeliveryFee(location: string): number {
    // In a real implementation, this would use distance or zones
    return 3.99;
  }
}

export default CreateOrderSaga;
