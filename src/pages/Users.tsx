import { Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { getUsers } from "@/integrations/api/auth";
import { useState } from "react";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";

const USERS_PER_PAGE = 50;

const Users = () => {
  const [page, setPage] = useState(0);
  const limit = USERS_PER_PAGE;
  const offset = page * limit;

  const { data: users, isLoading, error } = useQuery({
    queryKey: ["users", page, limit, offset],
    queryFn: () => getUsers({ limit, offset }),
  });

  const hasMore = users && users.length === limit;
  const canGoNext = hasMore;
  const canGoPrevious = page > 0;

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
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={2} className="px-4 py-8 text-center text-muted-foreground">
                      Загрузка...
                    </td>
                  </tr>
                ) : users?.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="px-4 py-8 text-center text-muted-foreground">
                      Нет пользователей
                    </td>
                  </tr>
                ) : (
                  users?.map((user) => (
                    <tr key={user.id} className="border-t border-border hover:bg-muted/30 transition-colors">
                      <td className="px-4 py-3 font-medium">{user.id}</td>
                      <td className="px-4 py-3 text-muted-foreground">{user.email}</td>
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