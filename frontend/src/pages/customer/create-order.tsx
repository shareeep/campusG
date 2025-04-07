import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import { useNavigate } from 'react-router-dom';
import { Loader2, MapPin, Plus, ShoppingBag } from 'lucide-react';
import { useAuth } from '@clerk/clerk-react'; // Revert back to useAuth
import { useUserSync } from '@/providers/UserSyncProvider'; // Also import useUserSync
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/use-toast';
import 'leaflet/dist/leaflet.css';

// Define the structure for an item, including price
interface OrderItem {
  name: string;
  quantity: number;
  price: number; // Added price field
}

// Removed unused OrderFormData interface

function LocationPicker({ onLocationSelect }: { onLocationSelect: (lat: number, lng: number) => void }) {
  // Removed unused 'map' variable assignment
  useMapEvents({
    click(e) {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });

  return null;
}

export function CreateOrderPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  // Get auth state from useAuth
  const { userId, getToken, isLoaded, isSignedIn } = useAuth();
  // Get sync state from useUserSync
  const { syncState } = useUserSync();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState<[number, number] | null>(null);
  // Update items state to include price, defaulting to 0
  const [items, setItems] = useState<Array<OrderItem>>([{ name: '', quantity: 1, price: 0 }]);

  // Removed items and unused 'errors' from useForm
  const { register, handleSubmit } = useForm<{ instructions?: string }>();

  const handleLocationSelect = (lat: number, lng: number) => {
    setSelectedLocation([lat, lng]);
  };

  const addItem = () => {
    // Add new item with default price 0
    setItems([...items, { name: '', quantity: 1, price: 0 }]);
  };

  // Update updateItem to handle name, quantity, and price
  const updateItem = (index: number, field: keyof OrderItem, value: string | number) => {
    const newItems = [...items];
    // Ensure quantity and price are numbers
    const processedValue = (field === 'quantity' || field === 'price') ? Number(value) || 0 : value;
    newItems[index] = { ...newItems[index], [field]: processedValue };
    setItems(newItems);
  };

  const removeItem = (index: number) => {
    // Prevent removing the last item if desired, or handle accordingly
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    } else {
      // Optionally reset the single item instead of removing
       setItems([{ name: '', quantity: 1, price: 0 }]);
       toast({ title: "Cannot remove the last item", variant: "destructive" });
    }
  };

  // Update onSubmit to use component state for items and call the API
  const onSubmit = async (formData: { instructions?: string }) => {
    // Log state values at the moment of submission - BEFORE AUTH CHECK
    console.log("[onSubmit] Before auth check:", { isLoaded, isSignedIn, userId, syncState });

    // Log state values at the moment of submission - AFTER AUTH CHECK
    console.log(`[onSubmit] State Check: isLoaded=${isLoaded}, isSignedIn=${isSignedIn}, userId=${userId}, syncState=${syncState}`);

    // Check Clerk auth state AND backend sync state (Log errors but don't return immediately)
    if (!isLoaded || !isSignedIn || !userId) {
       console.error("[onSubmit] Authentication check failed (will still attempt submission):", { isLoaded, isSignedIn, userId });
       // return; // Removed return to allow submission attempt
    }
    // Reinstate syncState check (Log errors but don't return immediately)
    if (syncState !== 'synced') {
       console.error(`[onSubmit] User sync check failed (will still attempt submission): syncState is ${syncState}`);
       // return; // Removed return to allow submission attempt
    }

    if (!selectedLocation) {
      toast({
        title: "Location Required",
        description: "Please select a delivery location on the map.",
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

    // Validate items
    const validItems = items.filter(item => item.name.trim() !== '' && item.quantity > 0 && item.price >= 0);
    if (validItems.length === 0) {
       toast({
        title: "Valid Items Required",
        description: "Please add at least one item with a name, quantity, and valid price.",
        variant: "destructive"
      });
      return;
    }

    // Redundant check for userId removed as it's checked above with isSignedIn

    setIsSubmitting(true);

    try {
      const token = await getToken(); // Get auth token from useAuth
      const payload = {
        customer_id: userId, // Use userId from useAuth
        order_details: {
          // Map frontend items state to backend expected format
          foodItems: validItems.map(item => ({
            name: item.name,
            quantity: item.quantity,
            price: item.price.toString(), // Send price as string if backend expects it
          })),
          // Assuming location is just lat/lng for now, adjust if address needed
          deliveryLocation: {
            latitude: selectedLocation[0],
            longitude: selectedLocation[1],
            // address: "Needs to be captured or derived" // Add address if needed
          },
          instructions: formData.instructions || "",
        }
      };

      const response = await fetch('http://localhost:3101/orders', { // Use the correct API endpoint
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` // Include auth token
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error || `HTTP error! status: ${response.status}`);
      }

      toast({
        title: "Order Creation Initiated",
        description: `Saga started successfully (ID: ${result.saga_id}). You will be notified upon completion.`,
      });

      // Navigate to order history or tracking page after successful initiation
      navigate('/customer/history'); // Or '/customer/order-tracking/' + result.order_id if available

    } catch (error) { // Use default error type
      console.error("Order creation failed:", error);
      // Check if error is an instance of Error before accessing message
      const errorMessage = error instanceof Error ? error.message : "An unexpected error occurred. Please try again.";
      toast({
        title: "Order Creation Failed",
        description: errorMessage,
        variant: "destructive"
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Create New Order</h1>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
          {/* Items Section */}
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <h2 className="text-xl font-semibold mb-4">Order Items</h2>
            
            <div className="space-y-4">
              {items.map((item, index) => (
                <div key={index} className="flex gap-4 items-start">
                  <div className="flex-1">
                    <Label>Item Name</Label>
                    <Input
                      value={item.name}
                      onChange={(e) => updateItem(index, 'name', e.target.value)}
                      placeholder="Enter item name"
                    />
                  </div>
                  <div className="w-24">
                    <Label>Quantity</Label>
                    <Input
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => updateItem(index, 'quantity', e.target.value)} // Pass string value
                    />
                  </div>
                   {/* Add Price Input */}
                  <div className="w-24">
                    <Label>Price ($)</Label>
                    <Input
                      type="number"
                      min="0"
                      step="0.01" // Allow decimals
                      value={item.price}
                      onChange={(e) => updateItem(index, 'price', e.target.value)} // Pass string value
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
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={addItem}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Item
            </Button>
          </div>

          {/* Delivery Location Section */}
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <h2 className="text-xl font-semibold mb-4">Delivery Location</h2>
            
            <div className="h-[400px] mb-4 rounded-lg overflow-hidden">
              <MapContainer
                center={[51.505, -0.09]}
                zoom={13}
                className="h-full w-full"
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />
                <LocationPicker onLocationSelect={handleLocationSelect} />
                {selectedLocation && (
                  <Marker position={selectedLocation} />
                )}
              </MapContainer>
            </div>

            <div className="flex items-center gap-2 text-sm text-gray-600">
              <MapPin className="h-4 w-4" />
              {selectedLocation ? (
                <span>Location selected: {selectedLocation[0].toFixed(6)}, {selectedLocation[1].toFixed(6)}</span>
              ) : (
                <span>Click on the map to select delivery location</span>
              )}
            </div>
          </div>

          {/* Instructions Section - Use register from useForm */}
          <div className="bg-white p-6 rounded-lg shadow-sm">
            <h2 className="text-xl font-semibold mb-4">Additional Instructions</h2>

            <Textarea
              {...register('instructions')} // Register instructions field
              placeholder="Add any special instructions for the runner..."
              className="min-h-[100px]"
            />
          </div>

          {/* Submit Button - Disable while Clerk is loading or submitting (Temporarily ignoring syncState) */}
          <Button
            type="submit"
            className="w-full"
          >
             {/* Show detailed loading/sync state */}
             {/* Keep loading state indicators for visual feedback even if button is clickable */}
             {!isLoaded ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading Auth...
              </>
            ) : syncState === 'syncing' ? ( // Explicitly show syncing
               <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Syncing User...
              </>
            ) : syncState === 'error' ? ( // Explicitly show error
               'Sync Error - Try Refresh'
            ) : syncState === 'idle' ? ( // Explicitly show idle (shouldn't happen long)
               'Initializing...'
            ) : isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating Order...
              </>
            ) : (
              <>
                <ShoppingBag className="mr-2 h-4 w-4" />
                Place Order
              </>
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
