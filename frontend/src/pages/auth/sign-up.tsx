import { SignUp } from '@clerk/clerk-react';

export function SignUpPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-gray-50">
      <h1 className="text-2xl font-bold mb-8">Create Your CampusG Account</h1>
      <div className="w-full max-w-md">
        <SignUp
          routing="path"
          path="/sign-up"
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
