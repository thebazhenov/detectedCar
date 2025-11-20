import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCcw, Settings as SettingsIcon, UploadCloud } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { apiBaseUrl } from "@/integrations/api/client";
import { authHeaders } from "@/integrations/api/auth";
import { getYoloModels, YoloModelInfo } from "@/integrations/api/models";
import {
  CameraSourceType,
  DetectionTarget,
  DetectionSettingsUpdate,
  WidgetPreferences,
  updateDetectionSettings,
} from "@/integrations/api/settings";
import { useAdminDetectionSettings } from "@/hooks/useDetectionSettings";

const ACCEPTED_TYPES = ["video/mp4", "video/webm", "video/ogg"];
const MAX_VIDEO_SIZE_MB = 200;

interface DemoVideoResponse {
  file_name: string;
  file_url: string;
}

const DETECTION_TARGETS: { value: DetectionTarget; title: string; description: string }[] = [
  {
    value: "vehicles",
    title: "Транспортные средства",
    description: "Оптимизировано для распознавания автомобилей и номеров",
  },
  {
    value: "people",
    title: "Люди",
    description: "Используется для мониторинга пешеходов и персонала",
  },
];

const DEFAULT_WIDGETS: WidgetPreferences = {
  videoWidget: true,
  accessButton: true,
};
const DEFAULT_MODEL = "yolo11l.pt";

const Settings = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data: settings, isLoading: isSettingsLoading } = useAdminDetectionSettings();
  const [activeTab, setActiveTab] = useState<CameraSourceType>("rtsp");
  const [rtspUrl, setRtspUrl] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const {
    data: yoloModels = [],
    isLoading: isModelsLoading,
  } = useQuery({
    queryKey: ["yolo-models"],
    queryFn: getYoloModels,
    retry: 1,
    refetchOnWindowFocus: false,
    onError: (error: Error) => {
      toast({
        title: "Не удалось получить список моделей",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const invalidateSettings = () => {
    queryClient.invalidateQueries({ queryKey: ["detection-settings", "admin"] });
    queryClient.invalidateQueries({ queryKey: ["detection-settings", "public"] });
  };

  const updateMutation = useMutation({
    mutationFn: (payload: DetectionSettingsUpdate) => updateDetectionSettings(payload),
    onSuccess: () => invalidateSettings(),
    onError: (error: Error) => {
      toast({
        title: "Не удалось сохранить настройки",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  useEffect(() => {
    if (settings) {
      setActiveTab(settings.sourceType ?? "rtsp");
      setRtspUrl(settings.rtspUrl ?? "");
    }
  }, [settings]);

  const widgetPreferences: WidgetPreferences = settings?.widgets ?? DEFAULT_WIDGETS;
  const detectionTarget = settings?.detectionTarget ?? "vehicles";
  const selectedModel = settings?.detectionModel ?? "";
  const hasModels = yoloModels.length > 0;
  const isSaving = updateMutation.isPending;

  const configuredSourceLabel = useMemo(() => {
    if (settings?.sourceType === "file" && settings.videoFileName) {
      return `Видео: ${settings.videoFileName}`;
    }
    if (settings?.sourceType === "rtsp" && settings.rtspUrl) {
      return `RTSP: ${settings.rtspUrl}`;
    }
    return "Источник не выбран";
  }, [settings]);

  const handleTabsChange = (value: string) => setActiveTab(value as CameraSourceType);

  const handleRtspSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const prepared = rtspUrl.trim();
    if (!prepared.startsWith("rtsp://")) {
      toast({
        title: "Неверный формат ссылки",
        description: "RTSP адрес должен начинаться с rtsp://",
        variant: "destructive",
      });
      return;
    }
    await updateMutation.mutateAsync({
      sourceType: "rtsp",
      rtspUrl: prepared,
      videoPath: "",
      videoFileName: "",
    });
    toast({
      title: "RTSP ссылка обновлена",
      description: "Видео-виджет начнет подключение к новому источнику",
    });
  };

  const handleDetectionTargetChange = async (value: DetectionTarget) => {
    await updateMutation.mutateAsync({ detectionTarget: value });
  };

  const handleModelSelect = async (value: string) => {
    await updateMutation.mutateAsync({ detectionModel: value });
  };

  const handleWidgetToggle = async (key: keyof WidgetPreferences, checked: boolean) => {
    await updateMutation.mutateAsync({
      widgets: {
        [key]: checked,
      },
    });
  };

  const handleReset = async () => {
    await updateMutation.mutateAsync({
      sourceType: null,
      rtspUrl: "",
      videoPath: "",
      videoFileName: "",
      detectionTarget: "vehicles",
      detectionModel: DEFAULT_MODEL,
      widgets: { ...DEFAULT_WIDGETS },
    });
    toast({
      title: "Настройки сброшены",
      description: "Используются значения по умолчанию",
    });
  };

  // Uploads are disabled; we use latest demo file from server. Keep isUploading flag
  // for UI feedback when switching to latest demo file.

  const clearVideo = async () => {
    if (!settings?.videoFileName) return;
    setIsDeleting(true);
    try {
      await deleteDemoVideo(settings.videoFileName);
      invalidateSettings();
      toast({
        title: "Видео удалено",
        description: "Файл убран из папки demo",
      });
    } catch (error) {
      toast({
        title: "Не удалось удалить видео",
        description: error instanceof Error ? error.message : "Попробуйте снова позже",
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const clearRtsp = async () => {
    setRtspUrl("");
    await updateMutation.mutateAsync({
      sourceType: null,
      rtspUrl: "",
    });
  };

  const videoPreviewSrc = resolveApiPath(settings?.videoPath);

  if (isSettingsLoading && !settings) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto space-y-6 p-6">
      <div className="space-y-1">
        <p className="text-sm uppercase tracking-wider text-primary">Настройки</p>
        <h2 className="text-3xl font-bold">Источник видеопотока</h2>
        <p className="text-muted-foreground">Выберите источник, модель и режим отображения для всех пользователей</p>
      </div>

      <Card className="glass-card">
        <CardHeader className="border-b">
          <div className="flex items-center gap-3">
            <SettingsIcon className="h-6 w-6 text-primary" />
            <div>
              <CardTitle className="text-xl">Текущая конфигурация</CardTitle>
              <CardDescription>{configuredSourceLabel}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-6">
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" type="button" onClick={() => setActiveTab("rtsp")}>
              RTSP поток
            </Button>
            <Button variant="secondary" type="button" onClick={() => setActiveTab("file")}>
              Локальное видео
            </Button>
            <Button variant="outline" type="button" onClick={handleReset} className="gap-2" disabled={isSaving}>
              <RefreshCcw className="h-4 w-4" />
              Сбросить настройки
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Объект детекции</CardTitle>
          <CardDescription>Укажите, что система должна отслеживать на камерах</CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup
            value={detectionTarget}
            onValueChange={(value) => handleDetectionTargetChange(value as DetectionTarget)}
            className="grid gap-4 md:grid-cols-2"
          >
            {DETECTION_TARGETS.map((item) => {
              const inputId = `target-${item.value}`;
              return (
                <div key={item.value}>
                  <RadioGroupItem value={item.value} id={inputId} className="peer sr-only" />
                  <Label
                    htmlFor={inputId}
                    className="flex cursor-pointer flex-col rounded-lg border border-border/60 p-4 shadow-sm transition hover:border-primary/60 peer-data-[state=checked]:border-primary peer-data-[state=checked]:shadow-md"
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="font-semibold">{item.title}</p>
                        <p className="text-sm text-muted-foreground">{item.description}</p>
                      </div>
                      <span className="h-3 w-3 rounded-full border border-muted peer-data-[state=checked]:bg-primary peer-data-[state=checked]:border-primary" />
                    </div>
                  </Label>
                </div>
              );
            })}
          </RadioGroup>
        </CardContent>
      </Card>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Модель детекции</CardTitle>
          <CardDescription>
            Файлы из директории <code>models/yolo</code> автоматически появляются в списке выбора
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="yolo-model">YOLO модель</Label>
            <Select
              value={hasModels ? selectedModel : ""}
              onValueChange={handleModelSelect}
              disabled={isModelsLoading || !hasModels}
            >
              <SelectTrigger id="yolo-model">
                <SelectValue placeholder={isModelsLoading ? "Загрузка..." : "Выберите модель"} />
              </SelectTrigger>
              <SelectContent>
                {yoloModels.map((model) => (
                  <SelectItem key={model.file_name} value={model.file_name}>
                    {model.display_name} · {model.size_mb} МБ
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {!isModelsLoading && !hasModels && (
              <p className="text-sm text-muted-foreground">
                Добавьте файлы .pt в папку <code>models/yolo</code>, чтобы выбрать модель.
              </p>
            )}
          </div>
          {hasModels && (
            <div className="grid gap-3 md:grid-cols-2">
              {yoloModels.map((model) => (
                <div
                  key={`card-${model.file_name}`}
                  className="rounded-lg border border-border/70 bg-muted/30 p-3 text-sm"
                >
                  <p className="font-medium">{model.display_name}</p>
                  <p className="text-muted-foreground">{model.file_name}</p>
                  <p className="text-xs text-muted-foreground mt-1">Размер: {model.size_mb} МБ</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Отображение на панели</CardTitle>
          <CardDescription>Включите или выключите блоки, которые должны быть на главной странице</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start justify-between gap-4 rounded-lg border border-border/70 p-4">
            <div>
              <p className="font-semibold">Виджет видеотрансляции</p>
              <p className="text-sm text-muted-foreground">
                Карточка с классами{" "}
                <code>rounded-lg border bg-card text-card-foreground shadow-sm glass-card</code> будет скрыта при
                отключении.
              </p>
            </div>
            <Switch
              checked={widgetPreferences.videoWidget}
              onCheckedChange={(checked) => handleWidgetToggle("videoWidget", checked)}
              disabled={isSaving}
            />
          </div>
          <div className="flex items-start justify-between gap-4 rounded-lg border border-border/70 p-4">
            <div>
              <p className="font-semibold">Кнопка &quot;Разовый въезд&quot;</p>
              <p className="text-sm text-muted-foreground">
                Элемент с классами{" "}
                <code>
                  inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium
                  ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2
                  focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50
                  [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 border border-input bg-background
                  hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2 w-full
                </code>{" "}
                исчезнет с панели мониторинга.
              </p>
            </div>
            <Switch
              checked={widgetPreferences.accessButton}
              onCheckedChange={(checked) => handleWidgetToggle("accessButton", checked)}
              disabled={isSaving}
            />
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={handleTabsChange} className="space-y-4">
        <TabsList className="w-full justify-start">
          <TabsTrigger value="rtsp">RTSP</TabsTrigger>
          <TabsTrigger value="file">Видео</TabsTrigger>
        </TabsList>

        <TabsContent value="rtsp">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Добавьте ссылку на камеру</CardTitle>
              <CardDescription>Используйте RTSP адрес, предоставленный производителем камеры</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={handleRtspSubmit}>
                <div className="space-y-2">
                  <Label htmlFor="rtsp-url">RTSP URL</Label>
                  <Input
                    id="rtsp-url"
                    name="rtsp-url"
                    placeholder="rtsp://user:pass@ip:554/stream"
                    value={rtspUrl}
                    onChange={(event) => setRtspUrl(event.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Пример: rtsp://admin:password@192.168.0.10:554/Streaming/Channels/101
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button type="submit" disabled={isSaving}>
                    {isSaving ? "Сохранение..." : "Сохранить"}
                  </Button>
                  {settings?.rtspUrl && (
                    <Button variant="ghost" type="button" onClick={clearRtsp} disabled={isSaving}>
                      Очистить
                    </Button>
                  )}
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="file">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle>Локальное демо (demo/)</CardTitle>
              <CardDescription>Выберите последнее по дате видео из директории <code>demo/</code> на сервере</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm">Загрузка видео отключена. Поместите файлы в папку <code>demo/</code> на сервере.</p>
                <p className="text-sm">Последнее по дате видео из каталога <code>demo/</code> будет автоматически использоваться как источник для всех пользователей.</p>
                <div className="flex gap-2">
                  {settings?.videoFileName && (
                    <Button variant="outline" type="button" onClick={clearVideo} disabled={isDeleting}>
                      {isDeleting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Удаляем...
                        </>
                      ) : (
                        "Удалить"
                      )}
                    </Button>
                  )}
                </div>
              </div>
              {videoPreviewSrc && (
                <div className="space-y-2">
                  <Label className="text-sm font-semibold">Предпросмотр</Label>
                  <video
                    src={videoPreviewSrc}
                    controls
                    loop
                    muted
                    playsInline
                    className="w-full rounded-lg border shadow-inner"
                  />
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

const uploadDemoVideo = async (file: File): Promise<DemoVideoResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${apiBaseUrl}/demo/video`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!response.ok) {
    const payload = await safeParseJson(response);
    throw new Error(payload?.detail ?? "Ошибка загрузки видео");
  }

  return (await response.json()) as DemoVideoResponse;
};

const deleteDemoVideo = async (fileName: string): Promise<void> => {
  const response = await fetch(`${apiBaseUrl}/demo/video/${encodeURIComponent(fileName)}`, {
    method: "DELETE",
    headers: authHeaders(),
  });

  if (!response.ok) {
    const payload = await safeParseJson(response);
    throw new Error(payload?.detail ?? "Ошибка удаления видео");
  }
};

const resolveApiPath = (relativePath?: string): string | undefined => {
  if (!relativePath) {
    return undefined;
  }
  const normalized = normalizeDemoPath(relativePath);
  if (normalized.startsWith("http")) {
    return normalized;
  }
  const base = apiBaseUrl.endsWith("/") ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
  return `${base}${normalized}`;
};

const normalizeDemoPath = (relativePath: string): string => {
  if (relativePath.startsWith("/demo/")) {
    return relativePath.replace("/demo/", "/demo-files/");
  }
  return relativePath;
};

const safeParseJson = async (response: Response): Promise<{ detail?: string } | null> => {
  try {
    return (await response.json()) as { detail?: string };
  } catch {
    return null;
  }
};

export default Settings;


