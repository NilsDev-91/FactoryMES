
'use client';

import React from 'react';
import useSWR from 'swr';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, AlertTriangle, Zap, TrendingUp, ShoppingBag, Loader2 } from 'lucide-react';
import { Printer } from '@/components/dashboard/PrinterCard'; // Type import
import { Order } from '@/components/orders/OrderTable'; // Type import

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function Dashboard() {
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  // Poll Data
  const { data: printers, error: pError } = useSWR<Printer[]>('http://127.0.0.1:8000/api/printers', fetcher, { refreshInterval: 5000 });
  const { data: orders, error: oError } = useSWR<Order[]>('http://127.0.0.1:8000/api/orders', fetcher, { refreshInterval: 5000 });

  const isLoading = !printers || !orders;
  const isError = pError || oError;

  // --- KPIs Calculation ---
  // Safe defaults if loading
  const printerList = printers || [];
  const orderList = orders || [];

  const activeJobs = printerList.filter(p => p.current_status === 'PRINTING').length;
  const errors = printerList.filter(p => ['OFFLINE', 'error', 'pause'].includes((p.current_status || '').toLowerCase())).length;
  const fleetSize = printerList.length || 1;
  const efficiency = Math.round(((fleetSize - errors) / fleetSize) * 100);
  const pendingOrders = orderList.filter(o => ['OPEN', 'IN_PROGRESS', 'QUEUED'].includes(o.status)).length;

  // Mock Chart Data (Frontend simulation for now)
  const chartData = [
    { name: '08:00', jobs: 2 },
    { name: '10:00', jobs: 5 },
    { name: '12:00', jobs: 8 },
    { name: '14:00', jobs: 7 },
    { name: '16:00', jobs: 12 },
    { name: '18:00', jobs: 10 },
    { name: '20:00', jobs: 14 },
  ];

  // --- Alerts Logic ---
  const alerts: { id: string; type: 'error' | 'warning' | 'info'; msg: string; time: string }[] = [];
  printerList.forEach(p => {
    // Temp Deviation Mock Logic
    if (p.current_status === 'PRINTING' && p.current_temp_nozzle && Math.abs(220 - p.current_temp_nozzle) > 15) {
      alerts.push({ id: p.serial, type: 'warning', msg: `${p.name}: Nozzle Temp Deviation`, time: 'Now' });
    }
    if (p.current_status === 'OFFLINE') {
      alerts.push({ id: p.serial, type: 'error', msg: `${p.name}: Connection Lost`, time: 'Active' });
    }
  });

  if (alerts.length === 0 && errors === 0) {
    alerts.push({ id: 'sys', type: 'info', msg: 'System operating normally.', time: 'Now' });
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500">
        <Loader2 size={48} className="animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-[1600px] mx-auto">

      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Factory Overview</h1>
          <p className="text-slate-400">Real-time production telemetry</p>
        </div>
        {isError && <span className="text-red-400 text-sm font-medium bg-red-500/10 px-3 py-1 rounded-full border border-red-500/20">Backend Connection Failed</span>}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard title="Active Jobs" value={activeJobs} icon={Activity} color="text-blue-400" bg="bg-blue-500/10 border-blue-500/20" />
        <KPICard title="Fleet Efficiency" value={`${efficiency}%`} icon={Zap} color="text-green-400" bg="bg-green-500/10 border-green-500/20" />
        <KPICard title="Issues" value={errors} icon={AlertTriangle} color="text-amber-400" bg="bg-amber-500/10 border-amber-500/20" />
        <KPICard title="Pending Orders" value={pendingOrders} icon={ShoppingBag} color="text-purple-400" bg="bg-purple-500/10 border-purple-500/20" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Production Chart */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <TrendingUp size={20} className="text-blue-400" /> Production Output
          </h3>
          <div className="h-[300px] w-full">
            {mounted ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorJobs" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                    itemStyle={{ color: '#3b82f6' }}
                  />
                  <Area type="monotone" dataKey="jobs" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorJobs)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-slate-600">
                <Loader2 size={24} className="animate-spin" />
              </div>
            )}
          </div>
        </div>

        {/* Issue Center */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <AlertTriangle size={20} className="text-amber-400" /> Issue Center
          </h3>
          <div className="space-y-4">
            {alerts.map((alert, idx) => (
              <div key={idx} className={`p-4 rounded-lg border flex items-start gap-4 ${alert.type === 'error' ? 'bg-red-500/10 border-red-500/20' :
                alert.type === 'warning' ? 'bg-amber-500/10 border-amber-500/20' :
                  'bg-blue-500/10 border-blue-500/20'
                }`}>
                <div className={`mt-1 ${alert.type === 'error' ? 'text-red-400' :
                  alert.type === 'warning' ? 'text-amber-400' :
                    'text-blue-400'
                  }`}>
                  <AlertTriangle size={16} />
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-200">{alert.msg}</div>
                  <div className="text-xs text-slate-500 mt-1">{alert.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

const KPICard = ({ title, value, icon: Icon, color, bg }: {
  title: string;
  value: React.ReactNode;
  icon: any;
  color: string;
  bg: string;
}) => (
  <div className={`p-6 rounded-xl border backdrop-blur-sm ${bg} transition-transform hover:-translate-y-1`}>
    <div className="flex justify-between items-start">
      <div>
        <p className="text-slate-400 text-sm font-medium uppercase tracking-wider">{title}</p>
        <h3 className="text-3xl font-bold text-white mt-2">{value}</h3>
      </div>
      <div className={`p-3 rounded-lg bg-slate-900/40 ${color}`}>
        <Icon size={24} />
      </div>
    </div>
  </div>
);
