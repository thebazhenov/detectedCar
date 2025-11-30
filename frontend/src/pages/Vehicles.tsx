import { Plus, Search, Edit, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getVehicles, createVehicle, VehicleCreate } from "@/integrations/api/vehicles";
import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

const Vehicles = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const queryClient = useQueryClient();

  const { data: vehicles, isLoading } = useQuery({
    queryKey: ["vehicles"],
    queryFn: () => getVehicles(),
  });

  const addVehicleMutation = useMutation({
    mutationFn: async (data: VehicleCreate) => {
      return createVehicle(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vehicles"] });
      toast.success("Номер успешно добавлен");
      setIsDialogOpen(false);
    },
    onError: (error) => {
      toast.error("Ошибка при добавлении номера: " + error.message);
    },
  });

  const handleAddVehicle = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    addVehicleMutation.mutate({
      license_plate: formData.get("license_plate") as string,
      owner_name: formData.get("owner_name") as string,
      notes: formData.get("notes") as string || undefined,
    });
  };

  const filteredVehicles = vehicles?.filter(
    (vehicle) =>
      vehicle.license_plate.toLowerCase().includes(searchQuery.toLowerCase()) ||
      vehicle.owner_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold mb-2">Разрешенные номера</h2>
          <p className="text-muted-foreground">
            Управление базой данных авторизованных транспортных средств
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-primary hover:bg-primary/90">
              <Plus className="h-4 w-4 mr-2" />
              Добавить номер
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Добавить номер</DialogTitle>
              <DialogDescription>
                Добавьте новый номер в базу разрешенных транспортных средств
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddVehicle} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="license_plate">Номерной знак *</Label>
                <Input
                  id="license_plate"
                  name="license_plate"
                  placeholder="А123БВ777"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="owner_name">Владелец *</Label>
                <Input
                  id="owner_name"
                  name="owner_name"
                  placeholder="Иван Иванов"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Примечание</Label>
                <Textarea
                  id="notes"
                  name="notes"
                  placeholder="Дополнительная информация..."
                  rows={3}
                />
              </div>
              <Button type="submit" className="w-full" disabled={addVehicleMutation.isPending}>
                {addVehicleMutation.isPending ? "Добавление..." : "Добавить"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <div className="flex items-center gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Поиск по номеру или владельцу..."
                className="pl-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Номер</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Владелец</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Примечание</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Статус</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold">Действия</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                      Загрузка...
                    </td>
                  </tr>
                ) : filteredVehicles?.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                      Нет добавленных номеров
                    </td>
                  </tr>
                ) : (
                  filteredVehicles?.map((vehicle) => (
                    <tr key={vehicle.id} className="border-t border-border hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-mono font-bold text-primary">
                        {vehicle.license_plate}
                      </td>
                      <td className="px-4 py-3">{vehicle.owner_name}</td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {vehicle.notes || "—"}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={vehicle.is_active ? "default" : "secondary"}
                          className={vehicle.is_active ? "bg-success" : ""}
                        >
                          {vehicle.is_active ? "Активен" : "Неактивен"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm">
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Vehicles;