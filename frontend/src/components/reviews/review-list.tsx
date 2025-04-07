import { Star, User } from 'lucide-react';
import type { Review } from '@/lib/types';

interface ReviewListProps {
  reviews: Review[];
}

export function ReviewList({ reviews }: ReviewListProps) {
  return (
    <div className="space-y-4">
      {reviews.map((review) => (
        <div key={review.id} className="bg-white rounded-lg border p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                <User className="h-4 w-4 text-blue-600" />
              </div>
              <span className="font-medium">{review.customer_name}</span>
            </div>
            <span className="text-sm text-gray-600">
              {new Date(review.created_at).toLocaleDateString()}
            </span>
          </div>
          <div className="flex items-center gap-2 mb-2">
            {[1, 2, 3, 4, 5].map((value) => (
              <Star
                key={value}
                className={`h-4 w-4 ${
                  value <= review.rating
                    ? 'fill-yellow-400 text-yellow-400'
                    : 'text-gray-300'
                }`}
              />
            ))}
          </div>
          <p className="text-gray-700">{review.comment}</p>
        </div>
      ))}

      {reviews.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No reviews yet</p>
        </div>
      )}
    </div>
  );
}