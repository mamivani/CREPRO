import type { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  title: 'CREPRO - Property Management',
  description: 'Enterprise property management platform',
};

export const viewport: Viewport = {
  themeColor: '#0f172a',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <style>{`
          :root {
            --background: 0 0% 100%;
            --foreground: 0 0% 3.6%;
            --border: 0 0% 89.8%;
            --input: 0 0% 89.8%;
            --ring: 0 84.2% 60.2%;
            --radius: 0.5rem;
          }
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { background-color: hsl(var(--background)); color: hsl(var(--foreground)); font-family: system-ui, -apple-system, sans-serif; }
          html { scroll-behavior: smooth; }
        `}</style>
      </head>
      <body>{children}</body>
    </html>
  );
}
