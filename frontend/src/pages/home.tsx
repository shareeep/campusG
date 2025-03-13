import { ArrowRight, UtensilsCrossed } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

export function HomePage() {
  return (
    <div className="relative">
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage: 'url(https://images.unsplash.com/photo-1484723091739-30a097e8f929?auto=format&fit=crop&q=80)',
          filter: 'brightness(0.7)'
        }}
      />
      
      <div className="relative container mx-auto px-4 py-32">
        <div className="max-w-2xl">
          <h1 className="text-5xl font-bold text-white mb-6">
            Campus Food Delivery Made Easy
          </h1>
          <p className="text-xl text-gray-100 mb-8">
            Order from your favorite campus restaurants and get it delivered by fellow students.
            Fast, convenient, and reliable.
          </p>
          
          <div className="flex gap-4">
            <Link to="/restaurants" className="inline-flex">
              <Button size="lg">
                Order Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link to="/become-runner" className="inline-flex">
              <Button size="lg" variant="secondary">
                Become a Runner
                <UtensilsCrossed className="ml-2 h-5 w-5" />
              </Button>
            </Link>
          </div>
        </div>
      </div>
      
      <div className="bg-white py-24">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            How It Works
          </h2>
          
          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                title: 'Browse & Order',
                description: 'Choose from a variety of campus restaurants and place your order in minutes.'
              },
              {
                title: 'Track in Real-time',
                description: 'Follow your order status and track your runner in real-time.'
              },
              {
                title: 'Enjoy Your Food',
                description: 'Get your food delivered right to your campus location.'
              }
            ].map((step, index) => (
              <div key={index} className="text-center">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl font-bold text-blue-600">{index + 1}</span>
                </div>
                <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
                <p className="text-gray-600">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}