import { NavLink } from "react-router-dom";
import { Monitor, Database, History, Users, LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
}

const navItems: NavItem[] = [
  { to: "/", icon: Monitor, label: "Мониторинг" },
  { to: "/vehicles", icon: Database, label: "Номера" },
  { to: "/events", icon: History, label: "Журнал" },
  { to: "/users", icon: Users, label: "Пользователи" },
];

export const Sidebar = () => {
  return (
    <aside className="glass-card w-64 min-h-[calc(100vh-5rem)] p-4">
      <nav className="space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-all",
                "hover:bg-primary/10 hover:text-primary",
                isActive
                  ? "bg-primary text-primary-foreground shadow-md"
                  : "text-muted-foreground"
              )
            }
          >
            <item.icon className="h-5 w-5" />
            <span className="font-medium">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};