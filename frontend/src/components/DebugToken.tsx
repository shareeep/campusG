import { useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";

export function DebugToken() {
  const { getToken } = useAuth();

  useEffect(() => {
    async function fetchToken() {
      // Request the token using your custom template
      const token = await getToken({ template: "api-gateway" });
      console.log("JWT Token:", token);
    }
    fetchToken();
  }, [getToken]);

  return null; // This component doesn't render anything visible
}
