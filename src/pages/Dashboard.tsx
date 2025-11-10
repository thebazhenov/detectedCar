import { VideoWidget } from "@/components/monitoring/VideoWidget";
import { BarrierControls } from "@/components/monitoring/BarrierControls";
import { SystemStatus } from "@/components/monitoring/SystemStatus";
import { OneTimeAccessDialog } from "@/components/monitoring/OneTimeAccessDialog";

const Dashboard = () => {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h2 className="text-3xl font-bold mb-2">Панель мониторинга</h2>
        <p className="text-muted-foreground">
          Контроль доступа в режиме реального времени
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <VideoWidget />
        </div>
        <div className="space-y-6">
          <BarrierControls />
          <OneTimeAccessDialog />
          <SystemStatus />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;