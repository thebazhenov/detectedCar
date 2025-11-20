import { Calendar, Filter, Image as ImageIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { format } from "date-fns";
import { ru } from "date-fns/locale";

const Events = () => {
  const { data: events, isLoading } = useQuery({
    queryKey: ["access_events"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("access_events")
        .select(`
          *,
          profiles:created_by (
            full_name
          ),
          vehicles:vehicle_id (
            owner_name
          )
        `)
        .order("timestamp", { ascending: false })
        .limit(50);
      
      if (error) throw error;
      return data;
    },
  });

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold mb-2">Журнал событий</h2>
          <p className="text-muted-foreground">
            История всех попыток проезда через шлагбаум
          </p>
        </div>
        <Button variant="outline" className="glass-button">
          <Filter className="h-4 w-4 mr-2" />
          Фильтры
        </Button>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary" />
            Последние события
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {isLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                Загрузка...
              </div>
            ) : events?.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                Пока нет записей в журнале
              </div>
            ) : (
              events?.map((event) => (
                <div
                  key={event.id}
                  className="flex items-center justify-between p-4 rounded-lg border border-border hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div className="flex flex-col">
                      <span className="font-mono font-bold text-lg">
                        {event.license_plate}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {format(new Date(event.timestamp), "dd MMMM yyyy, HH:mm:ss", {
                          locale: ru,
                        })}
                      </span>
                      <span className="text-xs text-muted-foreground mt-1">
                        Автор: {
                          event.profiles?.full_name || 
                          event.vehicles?.owner_name || 
                          "Автоматическая система"
                        }
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <Badge
                      variant={event.status === "granted" ? "default" : "destructive"}
                      className={event.status === "granted" ? "bg-success" : ""}
                    >
                      {event.status === "granted" ? "✓ Разрешен" : "✗ Запрещен"}
                    </Badge>
                    
                    {event.snapshot_url && (
                      <Button variant="ghost" size="sm">
                        <ImageIcon className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Events;