import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { getCurrentUser, subscribeAuth, UserRead } from "@/integrations/api/auth";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const [user, setUser] = useState<UserRead | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // initial load
    setUser(getCurrentUser());
    setLoading(false);
    // subscribe to auth changes (across tabs)
    const unsubscribe = subscribeAuth((u) => setUser(u));
    return () => unsubscribe();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  return <>{children}</>;
};