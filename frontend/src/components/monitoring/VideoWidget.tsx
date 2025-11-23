import { useState } from "react";
import { Camera, Info, VideoOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { apiBaseUrl } from "@/integrations/api/client";
import { usePublicDetectionSettings } from "@/hooks/useDetectionSettings";
import { useDemoVideo } from "@/hooks/useDemoVideo";

const TARGET_LABELS: Record<string, string> = {
  vehicles: "Транспорт",
  people: "Люди",
};

export const VideoWidget = () => {
  const { data: settings } = usePublicDetectionSettings();
  const { data: demoVideo } = useDemoVideo();
  const sourceType = settings?.sourceType;
  const status = buildStatus(sourceType);
  const detectionTarget = settings?.detectionTarget ?? "vehicles";
  const detectionModel = settings?.detectionModel ?? "yolo11l.pt";
  const [streamError, setStreamError] = useState(false);
  
  // Используем новый endpoint из Redis стрима
  // camera_id можно сделать настраиваемым, пока используем дефолтное значение "1"
  const cameraId = "1";
  // Всегда пытаемся показывать стрим из Redis (обработанные кадры с YOLO)
  const streamUrl = `${apiBaseUrl}/video_feed/${cameraId}`;

  const fallbackVideoUrl = buildVideoUrl(demoVideo?.file_url ?? settings?.videoPath);

  return (
    <Card className="glass-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5 text-primary" />
            Видеотрансляция
          </CardTitle>
          <Badge variant="outline" className={cn("flex items-center gap-2", status.className)}>
            <span className={cn("h-2 w-2 rounded-full", status.indicator)} />
            {status.label}
          </Badge>
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
          <span className="rounded-full border border-border px-3 py-1">
            Объект: {TARGET_LABELS[detectionTarget] ?? detectionTarget}
          </span>
          <span className="rounded-full border border-border px-3 py-1">Модель: {detectionModel}</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative aspect-video overflow-hidden rounded-lg border border-primary/20 bg-muted/20">
          {/* Используем обработанный MJPEG стрим из Redis с YOLO overlays.
              Если стрим недоступен, показываем демо видео файл как fallback. */}
          {!streamError ? (
            <img 
              key={streamUrl}
              src={streamUrl} 
              alt="YOLO stream" 
              className="h-full w-full object-cover"
              onError={() => {
                // Если стрим не загружается, переключаемся на fallback
                console.warn("Stream error, falling back to video", streamUrl);
                setStreamError(true);
              }}
              onLoad={() => {
                // Стрим успешно загрузился
                setStreamError(false);
              }}
            />
          ) : fallbackVideoUrl ? (
            <video
              src={fallbackVideoUrl}
              controls
              loop
              muted
              playsInline
              className="h-full w-full object-cover"
            />
          ) : (
            <NoSourceMessage sourceType={sourceType} />
          )}
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent" />
        </div>
      </CardContent>
    </Card>
  );
};

const buildStatus = (
  sourceType: string | null | undefined,
): { label: string; className: string; indicator: string } => {
  if (sourceType === "file") {
    return {
      label: "Локальное видео",
      className: "bg-primary/15 text-primary border-primary/40",
      indicator: "bg-success animate-pulse",
    };
  }
  if (sourceType === "rtsp") {
    return {
      label: "RTSP поток",
      className: "bg-success/20 text-success border-success/40",
      indicator: "bg-success animate-pulse",
    };
  }
  return {
    label: "Сигнал обнаружен",
    className: "bg-destructive/10 text-destructive border-destructive/30",
    indicator: "bg-destructive",
  };
};

const buildVideoUrl = (path?: string | null) => {
  if (!path) {
    return undefined;
  }
  if (path.startsWith("http")) {
    return path;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${apiBaseUrl}${normalized}`;
};

const NoSourceMessage = ({ sourceType }: { sourceType?: string | null }) => {
  if (!sourceType) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-center">
        <VideoOff className="mb-4 h-16 w-16 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Источник видео не настроен</p>
        <p className="text-xs text-muted-foreground">Обратитесь к администратору для конфигурации</p>
      </div>
    );
  }
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center text-muted-foreground">
      <Info className="h-10 w-10 text-primary" />
      <p className="text-sm">Не удалось получить поток. Проверьте подключение или обновите страницу.</p>
    </div>
  );
};