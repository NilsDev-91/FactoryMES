import { Bell, User, Plus } from 'lucide-react';

export const TopBar = ({ onAddClick }) => {
    return (
        <header className="fixed top-0 left-0 right-0 h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 z-50 flex items-center justify-between px-6 shadow-lg shadow-black/20">
            <div className="flex items-center">
                <h1 className="font-sans font-extrabold uppercase tracking-wider text-white text-xl">
                    Factory OS
                </h1>
            </div>

            <div className="flex items-center gap-4">
                <button
                    onClick={onAddClick}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-bold px-4 py-2 rounded-lg transition-all active:scale-95 shadow-lg shadow-blue-500/20"
                >
                    <Plus size={16} />
                    <span className="hidden sm:inline">Add Device</span>
                </button>

                <button className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full transition-colors">
                    <Bell size={20} />
                </button>
                <div className="h-8 w-8 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 border border-slate-600">
                    <User size={16} />
                </div>
            </div>
        </header>
    );
};
