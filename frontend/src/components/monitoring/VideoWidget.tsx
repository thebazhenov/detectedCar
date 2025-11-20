import { Camera, Info, VideoOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { apiBaseUrl } from "@/integrations/api/client";
import { getAuthToken } from "@/integrations/api/auth";
import { usePublicDetectionSettings } from "@/hooks/useDetectionSettings";

const TARGET_LABELS: Record<string, string> = {
  vehicles: "Транспорт",
  people: "Люди",
};

export const VideoWidget = () => {
  const { data: settings } = usePublicDetectionSettings();
  const token = getAuthToken();
  const sourceType = settings?.sourceType;
  const status = buildStatus(sourceType);
  const detectionTarget = settings?.detectionTarget ?? "vehicles";
  const detectionModel = settings?.detectionModel ?? "yolo11l.pt";
  const streamUrl =
    token && sourceType
      ? `${apiBaseUrl}/video/stream?token=${encodeURIComponent(token)}`
      : undefined;

  // If sourceType is file and a demo video path is configured, compute demo url as fallback
  const demoVideoPath = settings?.videoPath;
  const demoVideoUrl = demoVideoPath
    ? demoVideoPath.startsWith("http")
      ? demoVideoPath
      : `${apiBaseUrl}${demoVideoPath}`
    : undefined;

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
          {/* Prefer the processed MJPEG stream when authenticated (token present) so the
              widget shows YOLO overlays and loops file playback. If no token is available,
              fall back to serving the static demo video file. */}
          {sourceType === "file" && streamUrl ? (
            <img src={streamUrl} alt="YOLO stream" className="h-full w-full object-cover" />
          ) : sourceType === "file" && demoVideoUrl ? (
            <video src={demoVideoUrl} controls loop muted playsInline className="h-full w-full object-cover" />
          ) : streamUrl ? (
            <img src={streamUrl} alt="YOLO stream" className="h-full w-full object-cover" />
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
    label: "Нет сигнала",
    className: "bg-destructive/10 text-destructive border-destructive/30",
    indicator: "bg-destructive",
  };
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