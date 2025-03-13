import { SignUp } from '@clerk/clerk-react';

export function SignUpPage() {
  return (
    <div className="flex flex-col items-center">
      <h1 className="text-2xl font-bold mb-8">Create Your CampusEats Account</h1>
      <SignUp
        routing="path"
        path="/sign-up"
        afterSignUpUrl="/restaurants"
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