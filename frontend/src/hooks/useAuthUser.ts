import { useEffect, useState } from "react";
import { getCurrentUser, subscribeAuth, UserRead } from "@/integrations/api/auth";

export const useAuthUser = () => {
  const [user, setUser] = useState<UserRead | null>(() => getCurrentUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setUser(getCurrentUser());
    setLoading(false);
    const unsubscribe = subscribeAuth((u) => setUser(u));
    return () => unsubscribe();
  }, []);

  return { user, loading };
};


