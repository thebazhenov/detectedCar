import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { KeyRound } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

export const OneTimeAccessDialog = () => {
  const [open, setOpen] = useState(false);
  const [licensePlate, setLicensePlate] = useState("");
  const queryClient = useQueryClient();

  const createPassMutation = useMutation({
    mutationFn: async (plate: string) => {
      const { data: { user } } = await supabase.auth.getUser();
      
      const expiresAt = new Date();
      expiresAt.setHours(expiresAt.getHours() + 24);

      const { error } = await supabase.from("temporary_passes").insert({
        license_plate: plate.toUpperCase(),
        expires_at: expiresAt.toISOString(),
        created_by: user?.id,
      });
      
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["temporary_passes"] });
      toast.success("Разовый пропуск создан", {
        description: "Номер действует 24 часа и 2 проезда",
        icon: <KeyRound className="h-4 w-4" />,
      });
      setLicensePlate("");
      setOpen(false);
    },
    onError: (error) => {
      toast.error("Ошибка создания пропуска", {
        description: error.message,
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!licensePlate.trim()) {
      toast.error("Введите номер автомобиля");
      return;
    }
    createPassMutation.mutate(licensePlate.trim());
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className="w-full">
          <KeyRound className="h-4 w-4 mr-2" />
          Разовый въезд
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Разовый въезд</DialogTitle>
            <DialogDescription>
              Введите номер автомобиля для временного доступа. Пропуск действует 24 часа и позволяет 2 проезда (въезд и выезд).
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="license-plate">Номер автомобиля</Label>
              <Input
                id="license-plate"
                value={licensePlate}
                onChange={(e) => setLicensePlate(e.target.value)}
                placeholder="А123БВ777"
                className="uppercase"
              />
            </div>
          </div>
          <DialogFooter>
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => setOpen(false)}
            >
              Отмена
            </Button>
            <Button 
              type="submit" 
              disabled={createPassMutation.isPending}
            >
              {createPassMutation.isPending ? "Создание..." : "Создать пропуск"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
