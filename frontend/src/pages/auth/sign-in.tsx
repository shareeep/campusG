import { SignIn } from '@clerk/clerk-react';

export function SignInPage() {
  return (
    <div className="flex flex-col items-center">
      <h1 className="text-2xl font-bold mb-8">Sign In to CampusEats</h1>
      <SignIn
        routing="path"
        path="/sign-in"
        afterSignInUrl="/restaurants"
        appearance={{
          elements: {
            rootBox: "mx-auto w-full",
            card: "bg-white shadow-md rounded-lg p-8"
          }
        }}
      />
    </div>
  );
}