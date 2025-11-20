import { Shield, UserPlus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createUser, getUsers, UserRole } from "@/integrations/api/auth";
import { FormEvent, useState } from "react";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Navigate } from "react-router-dom";
import { useAuthUser } from "@/hooks/useAuthUser";

const USERS_PER_PAGE = 50;

const Users = () => {
  const [page, setPage] = useState(0);
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState<UserRole>("operator");
  const limit = USERS_PER_PAGE;
  const offset = page * limit;
  const queryClient = useQueryClient();
  const { user, loading: authLoading } = useAuthUser();

  const { data: users, isLoading, error } = useQuery({
    queryKey: ["users", page, limit, offset],
    queryFn: () => getUsers({ limit, offset }),
    enabled: user?.role === "admin",
  });

  const createUserMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      toast.success("Пользователь успешно создан");
      setNewEmail("");
      setNewPassword("");
      setNewRole("operator");
      queryClient.invalidateQueries({ queryKey: ["users"], exact: false });
    },
    onError: (err: any) => {
      const status = err?.status;
      if (status === 401) {
        toast.error("Необходимо войти в систему");
      } else if (status === 403) {
        toast.error("Доступ запрещен");
      } else if (status === 409) {
        toast.error("Пользователь с таким email уже существует");
      } else {
        const message = err instanceof Error ? err.message : "Ошибка создания пользователя";
        toast.error(message);
      }
    },
  });

  const handleCreateUser = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    createUserMutation.mutate({ email: newEmail, password: newPassword, role: newRole });
  };

  const hasMore = users && users.length === limit;
  const canGoNext = hasMore;
  const canGoPrevious = page > 0;

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (user?.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold mb-2">Пользователи</h2>
        <p className="text-muted-foreground">
          Список пользователей системы
        </p>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            Список пользователей
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-8 rounded-lg border border-dashed p-4 space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <UserPlus className="h-4 w-4 text-primary" />
              Добавить пользователя
            </div>
            <form onSubmit={handleCreateUser} className="grid gap-4 md:grid-cols-4 items-end">
              <div className="space-y-2">
                <Label htmlFor="new-email">Email</Label>
                <Input
                  id="new-email"
                  type="email"
                  placeholder="user@example.com"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new-password">Пароль</Label>
                <Input
                  id="new-password"
                  type="password"
                  placeholder="••••••••"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={6}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="new-role">Роль</Label>
                <select
                  id="new-role"
                  className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm"
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as UserRole)}
                >
                  <option value="operator">Оператор</option>
                  <option value="admin">Администратор</option>
                </select>
              </div>
              <Button type="submit" disabled={createUserMutation.isLoading}>
                {createUserMutation.isLoading ? "Создание..." : "Создать"}
              </Button>
            </form>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-destructive/10 text-destructive rounded-lg">
              Ошибка при загрузке пользователей: {error instanceof Error ? error.message : "Неизвестная ошибка"}
            </div>
          )}
          
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Email</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Роль</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-muted-foreground">
                      Загрузка...
                    </td>
                  </tr>
                ) : users?.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-muted-foreground">
                      Нет пользователей
                    </td>
                  </tr>
                ) : (
                  users?.map((user) => (
                    <tr key={user.id} className="border-t border-border hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-medium">{user.id}</td>
                      <td className="px-4 py-3 text-muted-foreground">{user.email}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {user.role === "admin" ? "Администратор" : "Оператор"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              Страница {page + 1} • Показано {users?.length || 0} пользователей
            </div>
            {(canGoPrevious || canGoNext) && (
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        if (canGoPrevious) {
                          setPage(page - 1);
                        }
                      }}
                      className={!canGoPrevious ? "pointer-events-none opacity-50" : "cursor-pointer"}
                      aria-disabled={!canGoPrevious}
                      aria-label="Предыдущая страница"
                    />
                  </PaginationItem>
                  <PaginationItem>
                    <PaginationLink href="#" onClick={(e) => e.preventDefault()} isActive>
                      {page + 1}
                    </PaginationLink>
                  </PaginationItem>
                  <PaginationItem>
                    <PaginationNext
                      href="#"
                      onClick={(e) => {
                        e.preventDefault();
                        if (canGoNext) {
                          setPage(page + 1);
                        }
                      }}
                      className={!canGoNext ? "pointer-events-none opacity-50" : "cursor-pointer"}
                      aria-disabled={!canGoNext}
                      aria-label="Следующая страница"
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Users;