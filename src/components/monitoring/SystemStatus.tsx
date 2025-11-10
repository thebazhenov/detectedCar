import { Activity, Wifi } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const SystemStatus = () => {
  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Статус системы
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between p-3 rounded-lg bg-success/10 border border-success/20">
          <div className="flex items-center gap-2">
            <Wifi className="h-4 w-4 text-success" />
            <span className="text-sm font-medium">Подключение к системе</span>
          </div>
          <span className="text-xs font-semibold text-success">Активно</span>
        </div>
        
        <div className="flex items-center justify-between p-3 rounded-lg bg-primary/10 border border-primary/20">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">AI распознавание</span>
          </div>
          <span className="text-xs font-semibold text-primary">Готово</span>
        </div>
      </CardContent>
    </Card>
  );
};