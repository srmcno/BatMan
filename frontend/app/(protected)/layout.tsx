'use client';

import { useEffect } from 'react';
import { redirect } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import AppLayout from '@/components/AppLayout';

export default function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) {
      redirect('/login');
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return null;
  }

  return <AppLayout>{children}</AppLayout>;
}
