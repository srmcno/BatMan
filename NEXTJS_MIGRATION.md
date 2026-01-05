# Next.js Migration - Deployment Guide

## Migration Complete ✅

The Vite + React frontend has been successfully converted to Next.js 14 with App Router.

## What Changed

### Configuration Files
- ✅ `next.config.js` - Next.js configuration with API proxy
- ✅ `package.json` - Updated with Next.js dependencies
- ✅ `tsconfig.json` - Next.js TypeScript configuration
- ✅ `tailwind.config.js` - Updated content paths for Next.js
- ✅ `.gitignore` - Next.js build artifacts
- ✅ `vercel.json` - Vercel deployment configuration

### Directory Structure
```
frontend/
├── app/                      # Next.js App Router
│   ├── (protected)/         # Protected routes (require auth)
│   │   ├── dashboard/
│   │   ├── projects/
│   │   │   └── [projectId]/
│   │   │       └── sites/[siteId]/recordings/
│   │   ├── recordings/[recordingId]/
│   │   ├── reports/
│   │   ├── review/
│   │   └── settings/
│   ├── login/               # Public login page
│   ├── layout.tsx           # Root layout with providers
│   ├── page.tsx             # Home redirect
│   ├── globals.css          # Global styles
│   └── providers.tsx        # React Query + Toaster
├── components/              # Shared components
│   ├── AppLayout.tsx        # Main app layout with sidebar
│   └── Spectrogram3D.tsx    # Three.js visualization
├── lib/                     # Utilities
│   └── api.ts              # Axios API client
├── stores/                  # Zustand stores
│   └── authStore.ts         # Authentication state
├── public/                  # Static assets
├── middleware.ts            # Next.js middleware
└── next.config.js          # Next.js configuration
```

### Removed Files
- ❌ `vite.config.ts`
- ❌ `index.html`
- ❌ `nginx.conf`
- ❌ `Dockerfile`
- ❌ `tsconfig.node.json`
- ❌ `postcss.config.js`
- ❌ `src/` directory (all files migrated to new structure)

## Development

### Install Dependencies
```bash
cd frontend
npm install
```

### Run Development Server
```bash
npm run dev
```
The app will be available at http://localhost:3000

### Build for Production
```bash
npm run build
```

### Run Production Build
```bash
npm start
```

## Environment Variables

Create a `.env.local` file in the `frontend/` directory:

```env
# API URL (defaults to localhost:8000 if not set)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

For production deployment on Vercel:
- Set `NEXT_PUBLIC_API_URL` to your FastAPI backend URL

## Deployment to Vercel

### Option 1: Vercel Dashboard
1. Connect your GitHub repository to Vercel
2. Set the root directory to `frontend/`
3. Vercel will auto-detect Next.js and use the correct build settings
4. Add environment variables in Vercel dashboard
5. Deploy!

### Option 2: Vercel CLI
```bash
cd frontend
npx vercel --prod
```

## Key Features Preserved

✅ All routes and navigation
✅ Authentication with JWT tokens
✅ React Query data fetching
✅ Zustand state management
✅ TailwindCSS styling
✅ Headless UI components
✅ File upload with react-dropzone
✅ Toast notifications
✅ React Three Fiber 3D visualizations
✅ Recharts data charts

## API Integration

The Next.js app proxies API calls to the FastAPI backend:
- Development: http://localhost:8000
- Production: Set via `NEXT_PUBLIC_API_URL` environment variable

The `next.config.js` rewrites `/api/*` requests to the backend URL.

## Notes

- The backend (FastAPI) remains unchanged
- All existing functionality has been preserved
- Font loading via Google Fonts link in layout (Next.js font optimization skipped due to network restrictions)
- Client-side authentication using Zustand persisted store
- All pages are client-side rendered (`'use client'` directive) to maintain compatibility with existing hooks

## Build Success

```
Route (app)                                          Size     First Load JS
┌ ○ /                                                570 B          90.4 kB
├ ○ /_not-found                                      872 B          88.2 kB
├ ○ /dashboard                                       3.73 kB         133 kB
├ ○ /login                                           4.31 kB         125 kB
├ ○ /projects                                        2.35 kB         156 kB
├ ƒ /projects/[projectId]                            2.53 kB         156 kB
├ ƒ /projects/[projectId]/sites/[siteId]/recordings  21.7 kB         147 kB
├ ƒ /recordings/[recordingId]                        263 kB          384 kB
├ ○ /reports                                         7.05 kB         132 kB
├ ○ /review                                          4.86 kB         130 kB
└ ○ /settings                                        4.71 kB        99.6 kB
```

All routes compiled successfully! ✅
