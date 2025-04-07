import { Search, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function RestaurantsPage() {
  const restaurants = [
    {
      id: 1,
      name: "Campus Café",
      image: "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&q=80",
      rating: 4.5,
      deliveryTime: "15-25",
      cuisine: "American",
      priceRange: "$$"
    },
    {
      id: 2,
      name: "Sushi Station",
      image: "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?auto=format&fit=crop&q=80",
      rating: 4.8,
      deliveryTime: "20-30",
      cuisine: "Japanese",
      priceRange: "$$$"
    },
    {
      id: 3,
      name: "Pizza Corner",
      image: "https://images.unsplash.com/photo-1604382355076-af4b0eb60143?auto=format&fit=crop&q=80",
      rating: 4.3,
      deliveryTime: "25-35",
      cuisine: "Italian",
      priceRange: "$$"
    }
  ];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Campus Restaurants</h1>
        <div className="flex gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
            <input
              type="text"
              placeholder="Search restaurants..."
              className="pl-10 pr-4 py-2 border rounded-md w-64 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <Button variant="secondary">
            <Filter className="h-5 w-5 mr-2" />
            Filters
          </Button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {restaurants.map((restaurant) => (
          <div key={restaurant.id} className="bg-white rounded-lg shadow-md overflow-hidden">
            <div className="h-48 overflow-hidden">
              <img
                src={restaurant.image}
                alt={restaurant.name}
                className="w-full h-full object-cover"
              />
            </div>
            <div className="p-4">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-xl font-semibold">{restaurant.name}</h3>
                <span className="bg-green-100 text-green-800 text-sm px-2 py-1 rounded">
                  ★ {restaurant.rating}
                </span>
              </div>
              <div className="text-gray-600 text-sm mb-4">
                <span>{restaurant.cuisine}</span>
                <span className="mx-2">•</span>
                <span>{restaurant.priceRange}</span>
                <span className="mx-2">•</span>
                <span>{restaurant.deliveryTime} mins</span>
              </div>
              <Button className="w-full">View Menu</Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}