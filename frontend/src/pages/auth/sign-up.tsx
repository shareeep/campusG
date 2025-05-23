import { SignUp } from '@clerk/clerk-react';

export function SignUpPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-gray-50">
      <div className="w-full max-w-md">
        <SignUp
          routing="path"
          path="/sign-up"
          fallbackRedirectUrl="/role-select"
          appearance={{
            elements: {
              rootBox: "w-full",
              card: "bg-white shadow-md rounded-lg p-6 md:p-8"
            }
          }}
        />
      </div>
    </div>
  );
}
