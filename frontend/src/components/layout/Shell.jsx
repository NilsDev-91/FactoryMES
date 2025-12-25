import React from 'react';
import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';

export const Shell = ({ children }) => {
    return (
        <div className="min-h-screen bg-slate-900 text-slate-50 flex flex-col">
            <TopBar />

            <div className="flex flex-1 pt-16">
                <Sidebar />

                {/* Main Content Wrapper */}
                {/* Added pl-[80px] to account for the collapsed sidebar fixed width */}
                {/* Since the sidebar expands on hover over the content, we don't need to adjust padding dynamically if we want it to float over, 
            BUT typically a pushed layout is better. However, with 'fixed' sidebar, margins are properly used. 
            For this hover sidebar, keeping the content margin static at the collapsed width (80px) is standard UX 
            so the content doesn't jump around. */}
                <main className="flex-1 pl-[80px] w-full bg-slate-900 min-h-[calc(100vh-64px)] overflow-y-auto">
                    <div className="p-8 h-full">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
};
