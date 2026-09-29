import type { Metadata, Viewport } from 'next';
import './globals.css';

import RegisterSW from '@/components/RegisterSW';

export const metadata: Metadata = {
  title: 'AVSAR — अवसर',
  description:
    'Voice-first skilling recommendations under PM-AJAY Grant-in-Aid, aligned to NSQF Qualification Packs.',
  manifest: '/manifest.webmanifest',
  applicationName: 'AVSAR',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#4338ca',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="hi" suppressHydrationWarning>
      <body>
        <a className="skip-link" href="#main">
          मुख्य सामग्री पर जाएँ / Skip to main content
        </a>
        {children}
        <RegisterSW />
      </body>
    </html>
  );
}
