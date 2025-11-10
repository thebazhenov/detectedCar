import { Shield, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { supabase } from "@/integrations/supabase/client";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

export const Header = () => {
  const navigate = useNavigate();

  const handleLogout = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      toast.error("Ошибка при выходе");
    } else {
      toast.success("Выход выполнен");
      navigate("/auth");
    }
  };

  return (
    <header className="glass-card border-b sticky top-0 z-50">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-primary to-blue-600">
              <Shield className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-blue-400 bg-clip-text text-transparent">
                BarrierGuard AI
              </h1>
              <p className="text-xs text-muted-foreground">
                Система управления шлагбаумом
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="glass-button"
          >
            <LogOut className="h-4 w-4 mr-2" />
            Выход
          </Button>
        </div>
      </div>
    </header>
  );
};