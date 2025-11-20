import { ArrowUp, ArrowDown, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export const BarrierControls = () => {
  const [barrierState, setBarrierState] = useState<"up" | "down">("down");
  const queryClient = useQueryClient();

  const logEventMutation = useMutation({
    mutationFn: async (action: "up" | "down") => {
      const actionText = action === "up" ? "Поднятие шлагбаума" : "Опускание шлагбаума";
      const { data: { user } } = await supabase.auth.getUser();
      
      const { error } = await supabase.from("access_events").insert({
        license_plate: actionText,
        status: "granted",
        created_by: user?.id,
      });
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access_events"] });
    },
  });

  const handleBarrierControl = (action: "up" | "down") => {
    setBarrierState(action);
    logEventMutation.mutate(action);
    
    if (action === "up") {
      toast.success("Шлагбаум поднят", {
        icon: <ArrowUp className="h-4 w-4" />,
      });
    } else {
      toast.info("Шлагбаум опущен", {
        icon: <ArrowDown className="h-4 w-4" />,
      });
    }
  };

  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lock className="h-5 w-5 text-primary" />
          Управление шлагбаумом
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="p-4 rounded-lg border border-primary/20 bg-primary/5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-muted-foreground">Текущий статус:</span>
            <span className={`font-semibold ${barrierState === "up" ? "text-success" : "text-muted-foreground"}`}>
              {barrierState === "up" ? "🔺 Поднят" : "🔻 Опущен"}
            </span>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          <Button
            variant="default"
            onClick={() => handleBarrierControl("up")}
            disabled={barrierState === "up"}
            className="bg-success hover:bg-success/90"
          >
            <ArrowUp className="h-4 w-4 mr-2" />
            Поднять
          </Button>
          <Button
            variant="secondary"
            onClick={() => handleBarrierControl("down")}
            disabled={barrierState === "down"}
          >
            <ArrowDown className="h-4 w-4 mr-2" />
            Опустить
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};