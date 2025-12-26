import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, CheckCircle, AlertTriangle, Zap, TrendingUp, ShoppingBag, Clock } from 'lucide-react';

const DashboardView = ({ printers = [], orders = [] }) => {

    // --- 1. Calculate KPIs ---

    const activeJobs = printers.filter(p => p.current_status === 'PRINTING').length;
    const errors = printers.filter(p => ['OFFLINE', 'error', 'pause'].includes((p.current_status || '').toLowerCase())).length;
    const fleetSize = printers.length || 1; // avoid div by zero
    const efficiency = Math.round(((fleetSize - errors) / fleetSize) * 100);
    const pendingOrders = orders.filter(o => ['OPEN', 'IN_PROGRESS'].includes(o.status)).length;

    // Mock Data for Charts
    const data = [
        { name: '08:00', jobs: 2 },
        { name: '10:00', jobs: 5 },
        { name: '12:00', jobs: 8 },
        { name: '14:00', jobs: 7 },
        { name: '16:00', jobs: 12 },
        { name: '18:00', jobs: 10 },
        { name: '20:00', jobs: 14 },
    ];

    // --- 2. Alerts Logic (Issue Center) ---
    const alerts = [];
    printers.forEach(p => {
        // Temp Deviation
        if (p.current_status === 'PRINTING' && Math.abs(p.target_nozzle_temper - p.current_temp_nozzle) > 10) {
            alerts.push({ id: p.serial, type: 'warning', msg: `${p.name}: Nozzle Temp Deviation`, time: 'Now' });
        }
        // Status Errors
        if (p.current_status === 'OFFLINE') {
            alerts.push({ id: p.serial, type: 'error', msg: `${p.name}: Connection Lost`, time: '2m ago' });
        }
    });

    // Mock more alerts if empty for demo
    if (alerts.length === 0 && errors === 0) {
        alerts.push({ id: 'sys', type: 'info', msg: 'System operating normally.', time: 'Now' });
    }

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <KPICard title="Active Jobs" value={activeJobs} icon={Activity} color="text-blue-400" bg="bg-blue-500/10 border-blue-500/20" />
                <KPICard title="Fleet Efficiency" value={`${efficiency}%`} icon={Zap} color="text-green-400" bg="bg-green-500/10 border-green-500/20" />
                <KPICard title="Issues" value={errors} icon={AlertTriangle} color="text-amber-400" bg="bg-amber-500/10 border-amber-500/20" />
                <KPICard title="Pending Orders" value={pendingOrders} icon={ShoppingBag} color="text-purple-400" bg="bg-purple-500/10 border-purple-500/20" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Production Chart */}
                <div className="lg:col-span-2 bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 backdrop-blur-sm">
                    <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
                        <TrendingUp size={20} className="text-blue-400" /> Production Output
                    </h3>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={data}>
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
                    </div>
                </div>

                {/* Issue Center */}
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 backdrop-blur-sm">
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
};

const KPICard = ({ title, value, icon: Icon, color, bg }) => (
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

export default DashboardView;
