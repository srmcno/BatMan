'use client';

import { useEffect } from 'react';
import { redirect } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

export default function Home() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (isAuthenticated) {
      redirect('/dashboard');
    } else {
      redirect('/login');
    }
  }, [isAuthenticated]);

  return null;
}
