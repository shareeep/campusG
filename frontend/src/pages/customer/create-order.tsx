import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Plus, ShoppingBag, Building, DoorClosed, School, MapPin } from 'lucide-react'; // Added icons
import { useAuth } from '@clerk/clerk-react';
import { useUserSync } from '@/providers/UserSyncProvider';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import 'leaflet/dist/leaflet.css'; // Keep if needed elsewhere, though map is removed

// Define the structure for an item, including price
interface OrderItem {
  name: string;
  quantity: number;
  price: number;
}

// Define structure for store details
interface StoreDetails {
  name: string;
  postalCode: string;
}

// Define structure for delivery details
interface DeliveryDetails {
  school: string;
  building: string;
  level: string;
  roomNumber: string;
  meetingPoint?: string; // Optional meeting point
}

export function CreateOrderPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { userId, getToken, isLoaded, isSignedIn } = useAuth();
  const { syncState } = useUserSync();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // State for form fields based on order-form.tsx structure
  const [items, setItems] = useState<Array<OrderItem>>([{ name: '', quantity: 1, price: 0 }]);
  const [storeDetails, setStoreDetails] = useState<StoreDetails>({ name: '', postalCode: '' });
  const [deliveryDetails, setDeliveryDetails] = useState<DeliveryDetails>({
    school: '',
    building: '',
    level: '',
    roomNumber: '',
    meetingPoint: '',
  });
  const [useMeetingPoint, setUseMeetingPoint] = useState(false);
  const [instructions, setInstructions] = useState('');
  const [deliveryFee, setDeliveryFee] = useState<number>(5); // Add delivery fee state

  const addItem = () => {
    setItems([...items, { name: '', quantity: 1, price: 0 }]);
  };

  const updateItem = (index: number, field: keyof OrderItem, value: string | number) => {
    const newItems = [...items];
    const processedValue = (field === 'quantity' || field === 'price') ? Number(value) || 0 : value;
    newItems[index] = { ...newItems[index], [field]: processedValue };
    setItems(newItems);
  };

  const removeItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    } else {
       setItems([{ name: '', quantity: 1, price: 0 }]);
       toast({ title: "Cannot remove the last item", variant: "destructive" });
    }
  };

  const handleStoreChange = (field: keyof StoreDetails, value: string) => {
    setStoreDetails(prev => ({ ...prev, [field]: value }));
  };

  const handleDeliveryChange = (field: keyof DeliveryDetails, value: string) => {
    setDeliveryDetails(prev => ({ ...prev, [field]: value }));
  };

  const calculateTotal = () => {
    const itemsTotal = items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    // Ensure deliveryFee is treated as a number
    const fee = Number(deliveryFee) || 0;
    return itemsTotal + fee;
  };

  // Updated onSubmit to use new state and structure
  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); // Prevent default form submission

    console.log("[onSubmit] State Check:", { isLoaded, isSignedIn, userId, syncState });

    if (!isLoaded || !isSignedIn || !userId) {
       toast({ title: "Authentication Error", description: "Please ensure you are logged in.", variant: "destructive" });
       console.error("[onSubmit] Auth check failed:", { isLoaded, isSignedIn, userId });
       return;
    }
    if (syncState !== 'synced') {
       toast({ title: "Sync Error", description: `User data not synced (${syncState}). Please wait or refresh.`, variant: "destructive" });
       console.error(`[onSubmit] Sync check failed: ${syncState}`);
       return;
    }

    // --- Form Validation ---
    if (!storeDetails.name || !storeDetails.postalCode) {
      toast({ title: "Store Details Required", description: "Please enter store name and postal code.", variant: "destructive" });
      return;
    }
    const validItems = items.filter(item => item.name.trim() !== '' && item.quantity > 0 && item.price >= 0);
    if (validItems.length === 0) {
       toast({ title: "Valid Items Required", description: "Add at least one item with name, quantity > 0, and price >= 0.", variant: "destructive" });
       return;
    }
    if (!useMeetingPoint && (!deliveryDetails.school || !deliveryDetails.building || !deliveryDetails.level || !deliveryDetails.roomNumber)) {
      toast({ title: "Delivery Details Required", description: "Please fill in School, Building, Level, and Room Number.", variant: "destructive" });
      return;
    }
     if (useMeetingPoint && !deliveryDetails.meetingPoint) {
      toast({ title: "Meeting Point Required", description: "Please specify the alternate meeting point.", variant: "destructive" });
      return;
    }
    // --- End Validation ---


    setIsSubmitting(true);

    try {
      const token = await getToken();
      // const total = calculateTotal(); // Total amount seems calculated backend-side

      // Calculate food fee
      const foodFee = validItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);

      // Construct delivery location string
      let deliveryLocationString = '';
      if (useMeetingPoint && deliveryDetails.meetingPoint) {
        deliveryLocationString = `Meeting Point: ${deliveryDetails.meetingPoint}`;
      } else {
        deliveryLocationString = `${deliveryDetails.school}, ${deliveryDetails.building}, Level ${deliveryDetails.level}, Room ${deliveryDetails.roomNumber}`;
      }

      // Construct payload matching the structure expected by the /orders endpoint (based on curl example)
      const payload = {
        customer_id: userId,
        order_details: {
          foodItems: validItems.map(item => ({
            item_name: item.name, // Use item_name as per curl example
            quantity: item.quantity,
            price: item.price,
          })),
          storeLocation: `${storeDetails.name} (${storeDetails.postalCode})`, // Add store location string
          deliveryLocation: deliveryLocationString,
          // Including fees here as they might be expected within order_details
          foodFee: foodFee,
          deliveryFee: Number(deliveryFee) || 0,
          // Include instructions if needed by backend inside order_details
          // instructions: instructions,
        }
      };

      console.log("Submitting Payload:", JSON.stringify(payload, null, 2)); // Log the corrected payload structure

      // Ensure API endpoint and method are correct for Create Order Saga
      const response = await fetch('http://localhost:3101/orders', { // Verify this endpoint triggers the saga
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      console.log("API Response:", result); // Log response

      if (!response.ok || !result.success) { // Check for success flag if backend sends one
        throw new Error(result.error || result.message || `HTTP error! status: ${response.status}`);
      }

      // --- Navigation Logic ---
      // Always navigate to history page after a delay upon successful initiation
      toast({
        title: "Order Creation Initiated",
        description: `Your order is being processed (Saga ID: ${result.saga_id}). Redirecting...`,
      });
      // Add a short delay before navigating to allow backend processing
      setTimeout(() => {
        navigate('/customer/history');
      }, 2000); // 2-second delay

    } catch (error) {
      console.error("Order creation failed:", error);
      const errorMessage = error instanceof Error ? error.message : "An unexpected error occurred. Please try again.";
      toast({
        title: "Order Creation Failed",
        description: errorMessage,
        variant: "destructive"
      });
      // Ensure isSubmitting is set back to false even after errors
      setIsSubmitting(false);
    }
    // Note: We intentionally don't set isSubmitting back to false in the finally block here
    // because we want the button to remain disabled during the setTimeout delay.
    // It will be re-enabled when the component unmounts or if an error occurs before the timeout.
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-2xl mx-auto"> {/* Adjusted max-width */}
        <h1 className="text-2xl font-bold mb-6">Place Your Order</h1> {/* Adjusted heading size */}

        <form onSubmit={onSubmit} className="space-y-6"> {/* Use onSubmit directly */}

          {/* Store Details Section */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Store Details</h2>
            <div className="space-y-4">
              <div>
                <Label>Store Name</Label>
                <Input
                  value={storeDetails.name}
                  onChange={(e) => handleStoreChange('name', e.target.value)}
                  placeholder="Enter exact store name"
                  required
                />
              </div>
              <div>
                <Label>Postal Code</Label>
                <Input
                  value={storeDetails.postalCode}
                  onChange={(e) => handleStoreChange('postalCode', e.target.value)}
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
                      onChange={(e) => updateItem(index, 'quantity', e.target.value)}
                      required
                    />
                  </div>
                  <div className="w-32"> {/* Adjusted width */}
                    <Label>Price ($)</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01"
                      value={item.price}
                      onChange={(e) => updateItem(index, 'price', e.target.value)}
                      required
                    />
                  </div>
                  <Button
                    type="button"
                    variant="secondary" // Changed from destructive
                    size="sm"
                    className="mt-6"
                    onClick={() => removeItem(index)}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
            <Button
              type="button"
              variant="ghost" // Changed from outline
              size="sm"
              className="mt-4 w-full" // Make Add Item button full width
              onClick={addItem}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Item
            </Button>
             {/* Calculation Display */}
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
                      onChange={(e) => setDeliveryFee(parseFloat(e.target.value) || 0)}
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

          {/* Delivery Details Section (Input Fields) */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-lg font-semibold mb-4">Delivery Details</h2>
            <div className="space-y-4">
              <div>
                <Label>School/Campus</Label>
                <div className="relative">
                  <School className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                  <Input
                    value={deliveryDetails.school}
                    onChange={(e) => handleDeliveryChange('school', e.target.value)}
                    placeholder="Enter school name"
                    className="pl-10"
                    required={!useMeetingPoint} // Required only if not using meeting point
                  />
                </div>
              </div>
              <div>
                <Label>Building Name</Label>
                <div className="relative">
                  <Building className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                  <Input
                    value={deliveryDetails.building}
                    onChange={(e) => handleDeliveryChange('building', e.target.value)}
                    placeholder="Enter building name"
                    className="pl-10"
                    required={!useMeetingPoint}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Level/Floor</Label>
                  <Input
                    value={deliveryDetails.level}
                    onChange={(e) => handleDeliveryChange('level', e.target.value)}
                    placeholder="Enter level number"
                    required={!useMeetingPoint} // Required only if not using meeting point
                  />
                </div>
                <div>
                  <Label>Room Number</Label>
                  <div className="relative">
                    <DoorClosed className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                    <Input
                      value={deliveryDetails.roomNumber}
                      onChange={(e) => handleDeliveryChange('roomNumber', e.target.value)}
                      placeholder="Enter room number"
                      className="pl-10"
                      required={!useMeetingPoint}
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
                        value={deliveryDetails.meetingPoint || ''}
                        onChange={(e) => handleDeliveryChange('meetingPoint', e.target.value)}
                        placeholder="e.g., Library Entrance, Canteen Bench"
                        className="pl-10"
                        required={useMeetingPoint} // Required only if checkbox is checked
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Instructions Section */}
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <h2 className="text-lg font-semibold mb-4">Special Instructions (Optional)</h2>
            <Textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Add any special instructions for the runner..."
              className="min-h-[100px]"
            />
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            disabled={isSubmitting || !isLoaded || syncState !== 'synced'} // Disable based on auth, sync, and submission state
          >
             {!isLoaded ? (
              <> <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading Auth... </>
            ) : syncState !== 'synced' ? (
               <> <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Syncing User ({syncState})... </>
            ) : isSubmitting ? (
              <> <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Creating Order... </>
            ) : (
              <> <ShoppingBag className="mr-2 h-4 w-4" /> Place Order (${calculateTotal().toFixed(2)}) </>
            )}
          </Button>
      </form>
    </div> {/* Closing div for max-w-2xl */}
    </div> // Add missing closing div for container
  );
}
