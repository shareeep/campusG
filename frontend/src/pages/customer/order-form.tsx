import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Plus, ShoppingBag, Loader2, Building, DoorClosed, School } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import { createOrder } from '@/lib/api';
import { useUser } from '@/lib/hooks/use-user';
import type { OrderItem } from '@/lib/types';

export function OrderFormPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { id: userId } = useUser();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [items, setItems] = useState<OrderItem[]>([]);
  const [store, setStore] = useState({ name: '', postalCode: '' });
  const [deliveryFee, setDeliveryFee] = useState<number>(5);
  const [deliveryDetails, setDeliveryDetails] = useState({
    building: '',
    level: '',
    roomNumber: '',
    school: '',
    meetingPoint: '',
  });
  const [useMeetingPoint, setUseMeetingPoint] = useState(false);
  const [instructions, setInstructions] = useState('');

  const addItem = () => {
    setItems([...items, { name: '', quantity: 1, price: 0 }]);
  };

  const updateItem = (index: number, field: keyof OrderItem, value: string | number) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
  };

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const calculateTotal = () => {
    const itemsTotal = items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    return itemsTotal + deliveryFee;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!userId) {
      toast({
        title: "Error",
        description: "You must be logged in to place an order.",
        variant: "destructive"
      });
      return;
    }

    if (!store.name || !store.postalCode) {
      toast({
        title: "Store Details Required",
        description: "Please enter both store name and postal code.",
        variant: "destructive"
      });
      return;
    }

    if (items.length === 0) {
      toast({
        title: "Items Required",
        description: "Please add at least one item to your order.",
        variant: "destructive"
      });
      return;
    }

    if (!deliveryDetails.building || !deliveryDetails.level || !deliveryDetails.roomNumber || !deliveryDetails.school) {
      toast({
        title: "Delivery Details Required",
        description: "Please fill in all required delivery location details.",
        variant: "destructive"
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const total = calculateTotal();
      
      // Create order directly without payment authorization
      const order = await createOrder({
        user_id: userId,
        store,
        items,
        deliveryDetails: {
          ...deliveryDetails,
          meetingPoint: useMeetingPoint ? deliveryDetails.meetingPoint : undefined
        },
        deliveryFee,
        total,
        instructions
      });

      toast({
        title: "Order Created",
        description: `Order ${order.order_id} created successfully.`
      });

      navigate(`/customer/order/${order.order_id}/tracking`);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create order. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Place Your Order</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Store Details */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Store Details</h2>
            <div className="space-y-4">
              <div>
                <Label>Store Name</Label>
                <Input
                  value={store.name}
                  onChange={(e) => setStore({ ...store, name: e.target.value })}
                  placeholder="Enter exact store name"
                  required
                />
              </div>
              <div>
                <Label>Postal Code</Label>
                <Input
                  value={store.postalCode}
                  onChange={(e) => setStore({ ...store, postalCode: e.target.value })}
                  placeholder="Enter store postal code"
                  required
                />
              </div>
            </div>
          </div>

          {/* Items Section */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Order Items</h2>
            
            <div className="space-y-4">
              {items.map((item, index) => (
                <div key={index} className="flex gap-4 items-start">
                  <div className="flex-1">
                    <Label>Item Name</Label>
                    <Input
                      value={item.name}
                      onChange={(e) => updateItem(index, 'name', e.target.value)}
                      placeholder="Enter item name"
                      required
                    />
                  </div>
                  <div className="w-24">
                    <Label>Quantity</Label>
                    <Input
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => updateItem(index, 'quantity', parseInt(e.target.value))}
                      required
                    />
                  </div>
                  <div className="w-32">
                    <Label>Price ($)</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={item.price}
                      onChange={(e) => updateItem(index, 'price', parseFloat(e.target.value))}
                      required
                    />
                  </div>
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    className="mt-6"
                    onClick={() => removeItem(index)}
                  >
                    Remove
                  </Button>
                </div>
              ))}

              <Button
                type="button"
                variant="outline"
                onClick={addItem}
                className="w-full"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Item
              </Button>

              {items.length > 0 && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <div className="flex justify-between text-sm">
                    <span>Items Subtotal:</span>
                    <span>${items.reduce((sum, item) => sum + (item.price * item.quantity), 0).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm mt-2">
                    <Label>Delivery Fee ($):</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={deliveryFee}
                      onChange={(e) => setDeliveryFee(parseFloat(e.target.value))}
                      className="w-24 text-right"
                      required
                    />
                  </div>
                  <div className="flex justify-between font-semibold mt-2 pt-2 border-t">
                    <span>Total:</span>
                    <span>${calculateTotal().toFixed(2)}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Delivery Details Section */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Delivery Details</h2>
            
            <div className="space-y-4">
              <div>
                <Label>School/Campus</Label>
                <div className="relative">
                  <School className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                  <Input
                    value={deliveryDetails.school}
                    onChange={(e) => setDeliveryDetails({...deliveryDetails, school: e.target.value})}
                    placeholder="Enter school name"
                    className="pl-10"
                    required
                  />
                </div>
              </div>

              <div>
                <Label>Building Name</Label>
                <div className="relative">
                  <Building className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                  <Input
                    value={deliveryDetails.building}
                    onChange={(e) => setDeliveryDetails({...deliveryDetails, building: e.target.value})}
                    placeholder="Enter building name"
                    className="pl-10"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Level/Floor</Label>
                  <Input
                    value={deliveryDetails.level}
                    onChange={(e) => setDeliveryDetails({...deliveryDetails, level: e.target.value})}
                    placeholder="Enter level number"
                    required
                  />
                </div>
                <div>
                  <Label>Room Number</Label>
                  <div className="relative">
                    <DoorClosed className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                    <Input
                      value={deliveryDetails.roomNumber}
                      onChange={(e) => setDeliveryDetails({...deliveryDetails, roomNumber: e.target.value})}
                      placeholder="Enter room number"
                      className="pl-10"
                      required
                    />
                  </div>
                </div>
              </div>

              <div className="border-t pt-4 mt-4">
                <label className="flex items-center space-x-2 mb-4">
                  <input
                    type="checkbox"
                    checked={useMeetingPoint}
                    onChange={(e) => setUseMeetingPoint(e.target.checked)}
                    className="rounded border-gray-300"
                  />
                  <span>Specify alternate meeting point</span>
                </label>

                {useMeetingPoint && (
                  <div>
                    <Label>Meeting Point</Label>
                    <div className="relative">
                      <MapPin className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                      <Input
                        value={deliveryDetails.meetingPoint}
                        onChange={(e) => setDeliveryDetails({...deliveryDetails, meetingPoint: e.target.value})}
                        placeholder="e.g., Student Lounge Walkway, Main Entrance"
                        className="pl-10"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div>
                <Label>Special Instructions (Optional)</Label>
                <Textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="Add any special instructions for delivery..."
                  className="min-h-[100px]"
                />
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing Order...
              </>
            ) : (
              <>
                <ShoppingBag className="mr-2 h-4 w-4" />
                Place Order (${calculateTotal().toFixed(2)})
              </>
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}