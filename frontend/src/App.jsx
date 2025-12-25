import React, { useEffect, useState } from 'react';
// import useSWR from 'swr';
import { fetchOrders, fetchPrinters } from './api';
import { LayoutDashboard, RefreshCw, Printer, Package } from 'lucide-react';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar'; // Ensure this is exported named or adjust
import DashboardView from './components/views/DashboardView';
import FleetView from './components/views/FleetView';
import ProductView from './components/views/ProductView';

function App() {
  const [currentView, setCurrentView] = useState('Dashboard');
  const [orders, setOrders] = useState([]);
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(false);

  // --- Global Data Fetching (Replaced useSWR with useEffect due to crash) ---
  const [printers, setPrinters] = useState([]);
  const [isValidating, setIsValidating] = useState(false);

  const refreshPrinters = async () => {
    setIsValidating(true);
    try {
      const data = await fetchPrinters();
      setPrinters(data || []);
    } catch (e) {
      console.error("Printer Fetch Error", e);
    } finally {
      setIsValidating(false);
    }
  };

  useEffect(() => {
    refreshPrinters();
    const interval = setInterval(refreshPrinters, 2000);
    return () => clearInterval(interval);
  }, []);

  const refreshOrders = async () => {
    try {
      const o = await fetchOrders();
      setOrders(Array.isArray(o) ? o : []);
    } catch (e) { console.error(e) }
  };

  useEffect(() => {
    refreshOrders();
    const interval = setInterval(refreshOrders, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#0f172a] text-white font-sans selection:bg-blue-500/30 overflow-x-hidden">
      <TopBar />
      <Sidebar
        activeView={currentView}
        onNavigate={setCurrentView}
        onExpandChange={setIsSidebarExpanded}
      />

      <main
        className={`pt-24 transition-[padding] duration-300 ease-in-out min-h-screen
            ${isSidebarExpanded ? 'pl-[260px]' : 'pl-[85px]'}`
        }
      >
        <div className="container mx-auto p-8 max-w-[1600px]">

          {/* Header Dynamic Title */}
          <div className="flex justify-between items-center mb-8">
            <h2 className="text-2xl font-bold text-white flex gap-2 items-center tracking-tight">
              {currentView === 'Dashboard' && <><LayoutDashboard className="text-blue-500" /> Dashboard</>}
              {currentView === 'Fleet' && <><Printer className="text-blue-500" /> Fleet Management</>}
              {currentView === 'Products' && <><Package className="text-purple-500" /> Products</>}
              {!['Dashboard', 'Fleet', 'Products'].includes(currentView) && <span className="text-slate-500">Module Under Construction: {currentView}</span>}
            </h2>

            <div className="text-xs text-slate-400 flex gap-2 items-center bg-slate-800/50 px-3 py-1 rounded-full border border-slate-700">
              <RefreshCw size={12} className={isValidating ? "animate-spin" : ""} />
              <span className={!printers.length ? "text-amber-500" : "text-emerald-500"}>
                {printers.length} Systems Active
              </span>
            </div>
          </div>

          {/* View Content */}
          <div className="min-h-[600px]">
            {currentView === 'Dashboard' && (
              <DashboardView printers={printers} orders={orders} />
            )}

            {currentView === 'Fleet' && (
              <FleetView printers={printers} />
            )}

            {currentView === 'Products' && (
              <ProductView />
            )}

            {/* Placeholder for other views */}
            {!['Dashboard', 'Fleet', 'Products'].includes(currentView) && (
              <div className="flex items-center justify-center h-64 border-2 border-dashed border-slate-800 rounded-xl">
                <p className="text-slate-500">The {currentView} module is coming soon.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
