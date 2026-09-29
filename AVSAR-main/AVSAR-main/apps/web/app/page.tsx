import Link from 'next/link';

export const dynamic = 'force-dynamic';

/** Landing / entry chooser. Full beneficiary journey lives at /start. */
export default function Home() {
  return (
    <main id="main" className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-6 p-6">
      <header className="text-center">
        <p className="text-sm font-semibold uppercase tracking-widest text-brand-700">PM-AJAY · GIA</p>
        <h1 className="mt-2 text-5xl font-semibold text-brand-900">AVSAR · अवसर</h1>
        <p className="mt-3 text-lg text-ink-soft">
          अपनी बात बोलिए — आपके लिए सही कौशल कोर्स बताएँगे।
        </p>
      </header>

      <nav className="grid gap-4" aria-label="Main choices">
        <Link href="/start" className="tap-primary w-full justify-start">
          🎤 <span>बात शुरू करें / Start conversation</span>
        </Link>
        <Link href="/dashboard" className="tap-secondary w-full justify-start">
          📊 <span>अधिकारी डैशबोर्ड / Officer dashboard</span>
        </Link>
      </nav>

      <footer className="mt-6 text-center text-sm text-ink-muted">
        <p>NSQF-aligned · Grounded in PM-AJAY Guidelines (May 2023)</p>
      </footer>
    </main>
  );
}
