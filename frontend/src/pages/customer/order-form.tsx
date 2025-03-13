import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';

type OrderFormData = {
  deliveryAddress: string;
  buildingName: string;
  roomNumber: string;
  specialInstructions: string;
  scheduleTime?: string;
  isScheduled: boolean;
};

export function OrderFormPage() {
  const navigate = useNavigate();
  const { register, handleSubmit, watch, formState: { errors } } = useForm<OrderFormData>();
  const isScheduled = watch('isScheduled');

  const onSubmit = async (data: OrderFormData) => {
    try {
      // TODO: Implement order creation
      console.log('Order data:', data);
      navigate('/customer/orders');
    } catch (error) {
      console.error('Error creating order:', error);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-6">Place Your Order</h1>
      
      <form onSubmit={handleSubmit(onSubmit)} className="bg-white p-6 rounded-lg shadow-md max-w-2xl mx-auto">
        <h2 className="text-xl font-semibold mb-4">Delivery Details</h2>
        
        <div className="mb-4">
          <label className="block text-gray-700 mb-2">Delivery Address</label>
          <input
            {...register('deliveryAddress', { required: 'Delivery address is required' })}
            className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
            placeholder="Enter your delivery address"
          />
          {errors.deliveryAddress && (
            <p className="text-red-500 text-sm mt-1">{errors.deliveryAddress.message}</p>
          )}
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-gray-700 mb-2">Building Name</label>
            <input
              {...register('buildingName', { required: 'Building name is required' })}
              className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
              placeholder="Enter building name"
            />
            {errors.buildingName && (
              <p className="text-red-500 text-sm mt-1">{errors.buildingName.message}</p>
            )}
          </div>
          
          <div>
            <label className="block text-gray-700 mb-2">Room Number</label>
            <input
              {...register('roomNumber', { required: 'Room number is required' })}
              className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
              placeholder="Enter room number"
            />
            {errors.roomNumber && (
              <p className="text-red-500 text-sm mt-1">{errors.roomNumber.message}</p>
            )}
          </div>
        </div>
        
        <div className="mb-4">
          <label className="block text-gray-700 mb-2">Special Instructions</label>
          <textarea
            {...register('specialInstructions')}
            className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
            placeholder="Any special instructions for the runner"
            rows={3}
          />
        </div>
        
        <div className="mb-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              {...register('isScheduled')}
              className="mr-2"
            />
            <span>Schedule for later</span>
          </label>
        </div>
        
        {isScheduled && (
          <div className="mb-4">
            <label className="block text-gray-700 mb-2">Delivery Time</label>
            <input
              type="datetime-local"
              {...register('scheduleTime', {
                required: isScheduled ? 'Please select a delivery time' : false
              })}
              className="w-full p-2 border rounded focus:ring-2 focus:ring-blue-500"
            />
            {errors.scheduleTime && (
              <p className="text-red-500 text-sm mt-1">{errors.scheduleTime.message}</p>
            )}
          </div>
        )}
        
        <div className="mt-6">
          <Button type="submit" className="w-full">
            Place Order
          </Button>
        </div>
      </form>
    </div>
  );
}