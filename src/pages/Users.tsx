import { UserPlus, Shield, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
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
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

const Users = () => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<"admin" | "operator">("operator");
  const queryClient = useQueryClient();
  const [currentUserRole, setCurrentUserRole] = useState<string | null>(null);

  // Check current user's role
  useQuery({
    queryKey: ["currentUserRole"],
    queryFn: async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return null;
      
      const { data, error } = await supabase
        .from("user_roles")
        .select("role")
        .eq("user_id", user.id)
        .single();
      
      if (error) throw error;
      setCurrentUserRole(data.role);
      return data.role;
    },
  });

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("profiles")
        .select(`
          *,
          user_roles (role)
        `)
        .order("created_at", { ascending: false });
      
      if (error) throw error;
      return data;
    },
  });

  const addUserMutation = useMutation({
    mutationFn: async (data: { email: string; password: string; full_name: string; role: "admin" | "operator" }) => {
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email: data.email,
        password: data.password,
        options: {
          data: {
            full_name: data.full_name,
          },
        },
      });

      if (authError) throw authError;
      
      if (authData.user) {
        const { error: roleError } = await supabase
          .from("user_roles")
          .update({ role: data.role })
          .eq("user_id", authData.user.id);
        
        if (roleError) throw roleError;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("Пользователь успешно добавлен");
      setIsDialogOpen(false);
    },
    onError: (error) => {
      toast.error("Ошибка при добавлении пользователя: " + error.message);
    },
  });

  const updateRoleMutation = useMutation({
    mutationFn: async ({ userId, newRole }: { userId: string; newRole: "admin" | "operator" }) => {
      const { error } = await supabase
        .from("user_roles")
        .update({ role: newRole })
        .eq("user_id", userId);
      
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("Роль пользователя обновлена");
    },
    onError: (error) => {
      toast.error("Ошибка при обновлении роли: " + error.message);
    },
  });

  const deleteUserMutation = useMutation({
    mutationFn: async (userId: string) => {
      // First delete from user_roles
      const { error: roleError } = await supabase
        .from("user_roles")
        .delete()
        .eq("user_id", userId);
      
      if (roleError) throw roleError;

      // Then delete from profiles
      const { error: profileError } = await supabase
        .from("profiles")
        .delete()
        .eq("id", userId);
      
      if (profileError) throw profileError;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("Пользователь удалён");
    },
    onError: (error) => {
      toast.error("Ошибка при удалении пользователя: " + error.message);
    },
  });

  const handleAddUser = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    addUserMutation.mutate({
      email: formData.get("email") as string,
      password: formData.get("password") as string,
      full_name: formData.get("full_name") as string,
      role: selectedRole,
    });
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold mb-2">Пользователи</h2>
          <p className="text-muted-foreground">
            Управление пользователями и правами доступа
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-primary hover:bg-primary/90">
              <UserPlus className="h-4 w-4 mr-2" />
              Добавить пользователя
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Добавить пользователя</DialogTitle>
              <DialogDescription>
                Создайте нового пользователя системы
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleAddUser} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="full_name">Полное имя *</Label>
                <Input
                  id="full_name"
                  name="full_name"
                  placeholder="Иван Иванов"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email *</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="user@example.com"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Пароль *</Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  placeholder="••••••••"
                  required
                  minLength={6}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Роль *</Label>
                <Select value={selectedRole} onValueChange={(value) => setSelectedRole(value as "admin" | "operator")}>
                  <SelectTrigger>
                    <SelectValue placeholder="Выберите роль" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">Администратор</SelectItem>
                    <SelectItem value="operator">Оператор</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button type="submit" className="w-full" disabled={addUserMutation.isPending}>
                {addUserMutation.isPending ? "Добавление..." : "Добавить"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Список пользователей
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Имя</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Email</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Роль</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Дата регистрации</th>
                  {currentUserRole === "admin" && (
                    <th className="px-4 py-3 text-left text-sm font-semibold">Действия</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={currentUserRole === "admin" ? 5 : 4} className="px-4 py-8 text-center text-muted-foreground">
                      Загрузка...
                    </td>
                  </tr>
                ) : users?.length === 0 ? (
                  <tr>
                    <td colSpan={currentUserRole === "admin" ? 5 : 4} className="px-4 py-8 text-center text-muted-foreground">
                      Нет пользователей
                    </td>
                  </tr>
                ) : (
                  users?.map((user) => (
                    <tr key={user.id} className="border-t border-border hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-medium">{user.full_name}</td>
                      <td className="px-4 py-3 text-muted-foreground">{user.email}</td>
                      <td className="px-4 py-3">
                        {currentUserRole === "admin" ? (
                          <Select
                            value={user.user_roles?.[0]?.role || "operator"}
                            onValueChange={(value) => updateRoleMutation.mutate({ 
                              userId: user.id, 
                              newRole: value as "admin" | "operator" 
                            })}
                          >
                            <SelectTrigger className="w-[160px]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="admin">Администратор</SelectItem>
                              <SelectItem value="operator">Оператор</SelectItem>
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge
                            variant={user.user_roles?.[0]?.role === "admin" ? "default" : "secondary"}
                            className={user.user_roles?.[0]?.role === "admin" ? "bg-primary" : ""}
                          >
                            {user.user_roles?.[0]?.role === "admin" ? "Администратор" : "Оператор"}
                          </Badge>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {format(new Date(user.created_at), "dd MMMM yyyy", {
                          locale: ru,
                        })}
                      </td>
                      {currentUserRole === "admin" && (
                        <td className="px-4 py-3">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => {
                              if (confirm(`Вы уверены, что хотите удалить пользователя ${user.full_name}?`)) {
                                deleteUserMutation.mutate(user.id);
                              }
                            }}
                            className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </td>
                      )}
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

export default Users;