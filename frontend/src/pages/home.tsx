import { ArrowRight, ShoppingBag } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export function HomePage() {
  const reviews = [
    {
      name: "Wei Ling T.",
      role: "Student",
      rating: 5,
      comment: "Saved me during exam week! No need to queue at the food court anymore.",
      date: "2 days ago"
    },
    {
      name: "Jun Kai L.",
      role: "Runner",
      rating: 5,
      comment: "Made $150 last month without breaking a sweat. Perfect for students!",
      date: "1 week ago"
    },
    {
      name: "Hui Min C.",
      role: "Student",
      rating: 5,
      comment: "No more walking to Parkway Parade in the rain. This app is a lifesaver!",
      date: "3 days ago"
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Fixed white navbar for landing page */}
      <div className="fixed top-0 left-0 right-0 z-50 bg-white border-b">
        <div className="container mx-auto px-4">
          <div className="h-16 flex items-center">
            <Link to="/" className="flex items-center space-x-2">
              <ShoppingBag className="h-6 w-6 text-blue-600" />
              <span className="text-xl font-bold text-gray-900">CampusG</span>
            </Link>
            <div className="ml-auto">
              <Link to="/user-select">
                <Button variant="ghost" className="text-gray-600 hover:text-gray-900">
                  Sign In
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Hero Section with floating food emojis */}
      <div className="relative min-h-[600px] flex items-center pt-16">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-green-500 animate-gradient-x overflow-hidden">
          {/* Floating food emojis positioned around the content */}
          <div className="absolute inset-0 pointer-events-none">
            <span className="absolute text-6xl animate-float" style={{ top: '10%', left: '5%', animationDelay: '0s' }}>🍕</span>
            <span className="absolute text-6xl animate-float" style={{ top: '15%', right: '10%', animationDelay: '1s' }}>🍔</span>
            <span className="absolute text-6xl animate-float" style={{ bottom: '15%', left: '8%', animationDelay: '2s' }}>🍜</span>
            <span className="absolute text-6xl animate-float" style={{ top: '60%', right: '15%', animationDelay: '3s' }}>☕️</span>
            <span className="absolute text-6xl animate-float" style={{ bottom: '20%', right: '20%', animationDelay: '4s' }}>🥤</span>
            <span className="absolute text-6xl animate-float" style={{ top: '40%', left: '15%', animationDelay: '5s' }}>🍱</span>
            <span className="absolute text-6xl animate-float" style={{ bottom: '30%', left: '30%', animationDelay: '6s' }}>🥪</span>
          </div>
        </div>

        <div className="relative container mx-auto px-4">
          <div className="max-w-3xl mx-auto text-center text-white">
            <h1 className="text-5xl md:text-6xl font-bold mb-6 [text-shadow:_0_2px_10px_rgba(0,0,0,0.15)]">
              Campus Food Delivery Made Simple
            </h1>
            <p className="text-xl md:text-2xl mb-8 opacity-90">
              Order from any store near campus and get it delivered by fellow students
            </p>
            <Link to="/user-select">
              <Button size="lg" className="min-w-[200px] bg-white text-blue-600 hover:bg-gray-100">
                Get Started
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="py-16 bg-white">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-4">1</div>
              <div className="text-4xl mb-4">📝</div>
              <h3 className="text-lg font-semibold mb-2">Place Your Order</h3>
              <p className="text-gray-600">Choose any store near campus and add items to your order</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-4">2</div>
              <div className="text-4xl mb-4">🛵</div>
              <h3 className="text-lg font-semibold mb-2">Runner Accepts</h3>
              <p className="text-gray-600">A student runner will accept your order and pick it up</p>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600 mb-4">3</div>
              <div className="text-4xl mb-4">✨</div>
              <h3 className="text-lg font-semibold mb-2">Quick Delivery</h3>
              <p className="text-gray-600">Get your order delivered to your location on campus</p>
            </div>
          </div>
        </div>
      </div>

      {/* Reviews Section */}
      <div className="py-16 bg-gray-50">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">What Our Users Say</h2>
          <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {reviews.map((review, index) => (
              <div key={index} className="bg-white p-6 rounded-lg shadow-sm">
                <div className="flex items-center mb-4">
                  <div className="flex-1">
                    <h3 className="font-semibold">{review.name}</h3>
                    <p className="text-sm text-gray-600">{review.role}</p>
                  </div>
                  <span className="text-sm text-gray-500">{review.date}</span>
                </div>
                <div className="flex mb-3">
                  {[...Array(5)].map((_, i) => (
                    <span key={i} className="text-yellow-400">★</span>
                  ))}
                </div>
                <p className="text-gray-700">{review.comment}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Runner Earnings Section */}
      <div className="py-16 bg-white">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-3xl font-bold mb-6">Earn Money As A Runner</h2>
            <p className="text-xl text-gray-600 mb-8">
              Make up to $200/month delivering food to fellow students between classes
            </p>
            <Link to="/user-select">
              <Button size="lg" className="bg-green-600 hover:bg-green-700 text-white">
                Start Earning Today
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="py-4 bg-gray-50 border-t">
        <div className="container mx-auto px-4">
          <p className="text-center text-sm text-gray-500">
            © {new Date().getFullYear()} CampusG. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}