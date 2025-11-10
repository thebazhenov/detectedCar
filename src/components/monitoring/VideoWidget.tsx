import { Camera, Video, VideoOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const VideoWidget = () => {
  // В реальной версии здесь будет видеопоток
  return (
    <Card className="glass-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5 text-primary" />
            Видеотрансляция
          </CardTitle>
          <Badge variant="outline" className="bg-success/20 text-success border-success/50">
            <span className="w-2 h-2 bg-success rounded-full mr-2 animate-pulse" />
            Онлайн
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="aspect-video bg-muted/20 rounded-lg flex items-center justify-center relative overflow-hidden border border-primary/20">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent" />
          <div className="relative z-10 text-center">
            <Video className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <p className="text-sm text-muted-foreground">
              Подключение к камере...
            </p>
            <p className="text-xs text-muted-foreground mt-2">
              Видеопоток будет доступен после настройки камеры
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};