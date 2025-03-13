'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@clerk/nextjs'

export default function Home() {
  const { isSignedIn, userId } = useAuth()

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-b from-white to-gray-100 px-4">
      <div className="w-full max-w-5xl mx-auto text-center">
        <h1 className="text-5xl font-bold mb-6 text-primary">
          CampusG Food Delivery
        </h1>
        <p className="text-xl mb-8 text-gray-600 max-w-3xl mx-auto">
          The fastest way to get food delivered on campus.
          Order your favorite meals and have them delivered right to your campus location.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-12 max-w-4xl mx-auto">
          <div className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow">
            <h2 className="text-2xl font-bold mb-4">I&apos;m Hungry</h2>
            <p className="text-gray-600 mb-6">
              Browse restaurants, place orders, and get food delivered to your campus location.
            </p>
            <Link 
              href={isSignedIn ? "/customer/dashboard" : "/sign-in?redirect=/customer/dashboard"} 
              className="inline-block bg-primary text-white px-6 py-3 rounded-md font-medium hover:bg-primary/90 transition-colors"
            >
              Order Food
            </Link>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow">
            <h2 className="text-2xl font-bold mb-4">I&apos;m a Runner</h2>
            <p className="text-gray-600 mb-6">
              Help deliver food on campus, earn money, and set your own schedule.
            </p>
            <Link 
              href={isSignedIn ? "/runner/dashboard" : "/sign-in?redirect=/runner/dashboard"} 
              className="inline-block bg-primary text-white px-6 py-3 rounded-md font-medium hover:bg-primary/90 transition-colors"
            >
              Deliver Food
            </Link>
          </div>
        </div>

        <div className="mt-16">
          <h2 className="text-2xl font-bold mb-6">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-3xl font-bold text-primary mb-3">1</div>
              <h3 className="font-semibold text-lg mb-2">Place Your Order</h3>
              <p className="text-gray-600">Browse restaurants and select your favorite meals.</p>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-3xl font-bold text-primary mb-3">2</div>
              <h3 className="font-semibold text-lg mb-2">Runner Accepts</h3>
              <p className="text-gray-600">A nearby runner will accept your order and pick it up.</p>
            </div>
            
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-3xl font-bold text-primary mb-3">3</div>
              <h3 className="font-semibold text-lg mb-2">Delivery</h3>
              <p className="text-gray-600">Get your food delivered to your campus location.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
