import { Bike, DollarSign, Clock, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function BecomeRunnerPage() {
  return (
    <div>
      <div className="relative h-[300px] bg-gradient-to-r from-blue-600 to-blue-800">
        <div className="container mx-auto px-4 h-full flex items-center">
          <div className="max-w-2xl text-white">
            <h1 className="text-4xl font-bold mb-4">Become a Campus Runner</h1>
            <p className="text-xl opacity-90">
              Earn money on your schedule. Deliver food to fellow students and be part of our growing community.
            </p>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-16">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
          {[
            {
              icon: <Clock className="h-8 w-8" />,
              title: "Flexible Schedule",
              description: "Work whenever you want. Perfect for busy students."
            },
            {
              icon: <DollarSign className="h-8 w-8" />,
              title: "Earn More",
              description: "Keep 100% of your delivery fees plus tips."
            },
            {
              icon: <Bike className="h-8 w-8" />,
              title: "Stay Active",
              description: "Get paid to exercise and explore campus."
            },
            {
              icon: <Star className="h-8 w-8" />,
              title: "Build Rating",
              description: "Earn rewards through great service."
            }
          ].map((feature, index) => (
            <div key={index} className="text-center p-6 bg-white rounded-lg shadow-sm">
              <div className="inline-flex items-center justify-center w-16 h-16 mb-4 bg-blue-100 text-blue-600 rounded-full">
                {feature.icon}
              </div>
              <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
              <p className="text-gray-600">{feature.description}</p>
            </div>
          ))}
        </div>

        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-8">Ready to Start?</h2>
          <div className="space-y-4">
            <Button size="lg" className="w-full md:w-auto md:px-12">
              Sign Up as Runner
            </Button>
            <p className="text-sm text-gray-600">
              Already registered? <a href="/runner/login" className="text-blue-600 hover:underline">Log in here</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}