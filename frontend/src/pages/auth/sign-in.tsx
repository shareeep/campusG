import { SignIn } from '@clerk/clerk-react';

export function SignInPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-gray-50">
      <h1 className="text-2xl font-bold mb-8">Sign In to CampusG</h1>
      <div className="w-full max-w-md">
        <SignIn
          routing="path"
          path="/sign-in"
          redirectUrl="/"
          appearance={{
            elements: {
              rootBox: "mx-auto w-full",
              card: "bg-white shadow-md rounded-lg p-8"
            }
          }}
        />
      </div>
    </div>
  );
}
