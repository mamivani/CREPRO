# CREPRO Frontend - Day 16

Property Management Platform - Next.js 15 Frontend with TypeScript, Tailwind CSS, and Playwright E2E Tests.

## Overview

This is the Day 16 deliverable of the 25-day CREPRO implementation plan. The frontend provides a modern, responsive user interface for property management operations including:

- **OAuth Authentication** (Microsoft, Google, Apple) + local login
- **Property Management** (CRUD operations, audit trail)
- **Invoice & Payment Management**
- **Responsive Design** (desktop, tablet, mobile)
- **End-to-End Testing** with Playwright
- **Performance** optimized with Lighthouse ≥90

## Quick Start

### Prerequisites

- Node.js 20+
- npm 11+
- Docker (for running backend services)

### Installation

```bash
# Install dependencies
npm install

# Copy environment template
cp .env.local.example .env.local

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

### Backend Services

The frontend expects these backend services to be running:

- **Identity Service**: `http://localhost:8001` (OAuth, token management)
- **Backend Service** (consolidated domain API: property, tenant, lease, reservation, payment, document, utility, maintenance, reporting): `http://localhost:8003`
- **Invoice Service**: `http://localhost:8003` (Invoice management, served by the backend)

Start them with:

```bash
cd /path/to/CREPRO
docker-compose up -d
```

## Project Structure

```
apps/web/
├── public/                 # Static assets
├── src/
│   ├── app/               # Next.js app directory (pages/layouts)
│   │   ├── auth/          # Authentication pages
│   │   ├── dashboard/     # Main dashboard pages
│   │   └── layout.tsx     # Root layout
│   ├── components/
│   │   ├── ui/            # ShadCN UI components (Button, Card, Input)
│   │   └── layout/        # Layout components (Header, Sidebar)
│   ├── hooks/             # Custom React hooks (useAuth, etc)
│   ├── services/          # API client, HTTP utilities
│   ├── store/             # Zustand stores (auth state)
│   ├── types/             # TypeScript interfaces
│   └── lib/               # Utility functions
├── e2e/                   # Playwright E2E tests
├── playwright.config.ts   # Playwright configuration
├── tailwind.config.ts     # Tailwind CSS configuration
└── tsconfig.json          # TypeScript configuration
```

## Available Scripts

### Development

```bash
# Start dev server (hot reload)
npm run dev

# Type checking
npm run type-check

# Linting
npm run lint

# Code formatting
npm run format
```

### Testing

```bash
# Run all E2E tests
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui

# Run E2E tests in debug mode
npm run test:e2e:debug

# Run tests for specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

### Production

```bash
# Build production bundle
npm run build

# Start production server
npm start
```

## Pages & Features

### Authentication

- **Login Page** (`/auth/login`)
  - OAuth buttons (Microsoft, Google, Apple)
  - Local login form (email/password)
  - Form validation
  - Error handling

- **Callback Page** (`/auth/callback`)
  - OAuth redirect handler
  - Token management
  - Automatic redirect to dashboard

### Dashboard

- **Dashboard Home** (`/dashboard`)
  - Navigation to Properties and Invoices
  - Day 16 implementation status
  - Quick links

- **Properties** (`/dashboard/properties`)
  - List properties with pagination
  - Create new property
  - View property details
  - Edit property
  - Delete property
  - View audit trail

- **Invoices** (`/dashboard/invoices`)
  - List invoices by property
  - View invoice details
  - Payment entry
  - Invoice status tracking

## E2E Test Coverage

Tests are located in `e2e/`:

- `auth.spec.ts` - Authentication flows (OAuth, local login)
- `dashboard.spec.ts` - Dashboard navigation
- `properties.spec.ts` - Property CRUD operations
- `invoices.spec.ts` - Invoice management

### Running Tests

```bash
# All tests, all browsers
npm run test:e2e

# Specific test file
npx playwright test e2e/auth.spec.ts

# Specific test
npx playwright test -g "should load login page"

# Debug mode
npx playwright test --debug

# Watch mode (with UI)
npm run test:e2e:ui
```

## API Integration

The frontend integrates with backend APIs through `src/services/api.ts`:

### Authentication Endpoints

```
GET  /api/v1/auth/{provider}          # OAuth authorization URL
POST /api/v1/auth/callback            # OAuth callback handler
POST /api/v1/auth/refresh             # Token refresh
```

### Property Endpoints

```
GET    /api/v1/properties             # List properties
POST   /api/v1/properties             # Create property
GET    /api/v1/properties/{id}        # Get property
PUT    /api/v1/properties/{id}        # Update property
DELETE /api/v1/properties/{id}        # Delete property
GET    /api/v1/properties/{id}/audit  # Get audit trail
```

### Invoice Endpoints

```
GET    /api/v1/invoices               # List invoices
POST   /api/v1/invoices               # Create invoice
GET    /api/v1/invoices/{id}          # Get invoice
POST   /api/v1/invoices/{id}/payments # Record payment
```

## Authentication Flow

### OAuth Flow

1. User clicks OAuth provider button
2. Redirects to `/api/v1/auth/{provider}` on Identity Service
3. User authenticates with provider
4. Redirected back to `/auth/callback?provider={provider}&code={code}`
5. Frontend exchanges code for access token
6. Token stored in secure httpOnly cookie
7. Redirects to `/dashboard`

### Local Login Flow

1. User enters email/password
2. Form submission to `/api/v1/auth/login`
3. Identity Service returns access token
4. Token stored in secure httpOnly cookie
5. Redirects to `/dashboard`

### Token Refresh

- Automatic token refresh on 401 response
- Refresh token stored in secure httpOnly cookie
- Automatic redirect to login on refresh failure

## State Management

Uses Zustand for lightweight state management:

- **Auth Store** (`src/store/auth.ts`) - User, token, auth state
- **Hooks** (`src/hooks/useAuth.ts`) - Easy access to auth state

```typescript
import { useAuth } from '@/hooks/useAuth';

export default function MyComponent() {
  const { user, token, isAuthenticated, logout } = useAuth();
  
  return <div>{user?.name}</div>;
}
```

## Styling

- **Tailwind CSS** - Utility-first CSS framework
- **ShadCN UI** - Accessible component library
- **CSS Variables** - Theme customization via CSS custom properties

## Performance

### Lighthouse Targets

- Performance: ≥90
- Accessibility: ≥90
- Best Practices: ≥90
- SEO: ≥90

### Optimization Strategies

- Code splitting (automatic with Next.js)
- Image optimization with `next/image`
- CSS-in-JS minimization
- Tree shaking
- Lazy loading routes

## Environment Variables

See `.env.local.example`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_IDENTITY_URL=http://localhost:8001
```

## CI/CD Integration

GitHub Actions workflow (`.github/workflows/e2e.yml`):

- Runs on every PR and push to develop/main
- Tests across Chromium, Firefox, WebKit
- ESLint & TypeScript type checking
- Lighthouse performance audit
- Artifacts: test reports, videos on failure

## Deployment

Runs as the `ca-crepro-web` Container App (`infra/terraform/environments/dev/apps.tf`), built from
`apps/web/Dockerfile` (multi-stage, `output: 'standalone'`). `NEXT_PUBLIC_API_URL` and
`NEXT_PUBLIC_IDENTITY_URL` are Docker build args, not Container App env vars: Next.js inlines
`NEXT_PUBLIC_*` into the bundle at build time, so they have to be known before the image is built,
not at container start. `.github/workflows/deploy.yml` computes them from the Container Apps
Environment's stable default domain and builds/pushes/deploys the image automatically on every push
to `main`. `/api/health` (`src/app/api/health/route.ts`) is the liveness/readiness probe target.

## Development Guidelines

### Code Style

- Use TypeScript for type safety
- Follow ESLint rules
- Format with Prettier
- Use functional components with hooks
- Keep components small and focused

### Component Structure

```typescript
// Always use 'use client' directive for client components
'use client';

import { useState } from 'react';

interface MyComponentProps {
  title: string;
  onAction: () => void;
}

export default function MyComponent({ title, onAction }: MyComponentProps) {
  const [count, setCount] = useState(0);

  return (
    <div>
      <h1>{title}</h1>
      <button onClick={onAction}>Click me</button>
    </div>
  );
}
```

### API Client Usage

```typescript
import { apiClient } from '@/services/api';

// Handle errors gracefully
try {
  const response = await apiClient.getProperties();
  // Use response.data
} catch (error) {
  const message = apiClient.getErrorMessage(error);
  console.error(message);
}
```

## Troubleshooting

### Port 3000 already in use

```bash
# Kill process using port 3000
lsof -ti:3000 | xargs kill -9  # macOS/Linux
netstat -ano | findstr :3000   # Windows
```

### Tests timeout

Increase timeout in `playwright.config.ts`:

```typescript
use: {
  timeout: 30000, // 30 seconds
}
```

### Backend connection refused

Ensure backend services are running:

```bash
docker-compose up -d
docker-compose ps  # Check status
```

### Token not persisting

Verify cookies are enabled and check browser storage:

```javascript
// In browser console
document.cookie // Check for access_token
```

## Next Steps (Days 17-25)

- **Day 17-18**: Lease service (lease CRUD, rent increment engine)
- **Day 19-20**: Utility service (meter reading, consumption tracking)
- **Day 21-22**: Maintenance service (work orders, vendor management)
- **Day 23-24**: Reporting service (financials, occupancy, KPIs)
- **Day 25**: Production readiness (multi-region, staging, monitoring)

## Support

For issues or questions:
1. Check existing GitHub issues
2. Create a new issue with:
   - Browser and OS
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots/videos if applicable

## License

Part of CREPRO project. See parent repository for license information.
