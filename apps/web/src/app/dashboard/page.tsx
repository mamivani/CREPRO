'use client';

import Link from 'next/link';

export default function DashboardPage() {
  return (
    <div className="space-y-8" data-testid="dashboard-page">
      <div>
        <h1 className="text-4xl font-bold mb-2">Welcome to CREPRO</h1>
        <p className="text-lg text-muted-foreground">Property Management Platform</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          href="/dashboard/properties"
          className="block p-6 bg-card border border-border rounded-lg hover:shadow-lg transition-shadow"
          data-testid="properties-link"
        >
          <h3 className="text-xl font-semibold mb-2">Properties</h3>
          <p className="text-muted-foreground">Manage your properties and units</p>
        </Link>

        <Link
          href="/dashboard/invoices"
          className="block p-6 bg-card border border-border rounded-lg hover:shadow-lg transition-shadow"
          data-testid="invoices-link"
        >
          <h3 className="text-xl font-semibold mb-2">Invoices</h3>
          <p className="text-muted-foreground">View and manage invoices</p>
        </Link>

        <div className="p-6 bg-card border border-border rounded-lg">
          <h3 className="text-xl font-semibold mb-2">Reports</h3>
          <p className="text-muted-foreground">Coming in Days 17-25</p>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="font-semibold text-blue-900 mb-2">Day 16 Status</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>✓ Next.js 15 frontend with TypeScript</li>
          <li>✓ Tailwind CSS + ShadCN UI components</li>
          <li>✓ Authentication pages (OAuth + local login)</li>
          <li>✓ Property CRUD operations</li>
          <li>✓ Invoice management interface</li>
          <li>✓ Playwright E2E test harness</li>
          <li>⏳ E2E tests and CI/CD workflow</li>
        </ul>
      </div>
    </div>
  );
}
