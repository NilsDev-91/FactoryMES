
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { QueryProvider } from '@/components/providers/QueryProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'FactoryOS',
  description: 'Factory Operating System',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <QueryProvider>
          <div className="min-h-screen bg-slate-950 text-slate-50 selection:bg-blue-500/30">
            <Header />

            <div className="pt-16">
              <Sidebar />

              <main className="ml-64 min-h-[calc(100vh-4rem)] p-8 transition-all duration-300 ease-in-out">
                <div className="mx-auto max-w-[1600px] animate-in fade-in zoom-in-95 duration-500">
                  {children}
                </div>
              </main>
            </div>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
