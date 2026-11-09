export default function Page() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-foreground mb-4">Welcome to CREPRO</h1>
        <p className="text-muted-foreground text-lg mb-8">
          Property Management Platform - Day 16 Frontend Scaffold
        </p>
        <div className="space-x-4">
          <a
            href="/auth/login"
            className="inline-block px-6 py-2 bg-accent text-accent-foreground rounded-lg hover:opacity-90 font-semibold"
          >
            Login
          </a>
          <a
            href="/dashboard"
            className="inline-block px-6 py-2 border border-border text-foreground rounded-lg hover:bg-muted"
          >
            Dashboard
          </a>
        </div>
      </div>
    </main>
  );
}
