'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { authApi } from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const router = useRouter();
  const login = useAuthStore((state) => state.login);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);

  useEffect(() => {
    if (hasHydrated && isAuthenticated) {
      router.replace('/dashboard');
    }
  }, [hasHydrated, isAuthenticated, router]);

  const loginMutation = useMutation({
    mutationFn: () => authApi.login(email, password),
    onSuccess: async (response) => {
      const { access_token, refresh_token } = response.data;

      // Get user info
      const userResponse = await authApi.getMe();
      const userData = userResponse.data;

      login(
        {
          id: userData.id,
          email: userData.email,
          fullName: userData.full_name,
          role: userData.role,
        },
        access_token,
        refresh_token
      );

      toast.success('Welcome back!');
      router.push('/dashboard');
    },
    onError: () => {
      toast.error('Invalid email or password');
    },
  });

  const registerMutation = useMutation({
    mutationFn: () => authApi.register(email, password, fullName),
    onSuccess: () => {
      toast.success('Account created! Please log in.');
      setIsLogin(true);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create account');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLogin) {
      loginMutation.mutate();
    } else {
      registerMutation.mutate();
    }
  };

  const isLoading = loginMutation.isPending || registerMutation.isPending;

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <div className="max-w-md w-full">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-primary-500">EcoEcho AI</h1>
          <p className="mt-2 text-gray-400">Bioacoustic Analysis Platform</p>
        </div>

        {/* Form */}
        <div className="card">
          <h2 className="text-2xl font-semibold text-white mb-6">
            {isLogin ? 'Sign in to your account' : 'Create an account'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label htmlFor="fullName" className="label">
                  Full Name
                </label>
                <input
                  id="fullName"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input"
                  placeholder="John Doe"
                  required={!isLogin}
                />
              </div>
            )}

            <div>
              <label htmlFor="email" className="label">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="••••••••"
                required
                minLength={8}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full"
            >
              {isLoading ? (
                <span className="spinner" />
              ) : isLogin ? (
                'Sign In'
              ) : (
                'Create Account'
              )}
            </button>
          </form>

          <div className="mt-6 text-center">
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-sm text-primary-400 hover:text-primary-300"
            >
              {isLogin
                ? "Don't have an account? Sign up"
                : 'Already have an account? Sign in'}
            </button>
          </div>
        </div>

        {/* Demo credentials */}
        <div className="mt-6 text-center text-sm text-gray-500">
          <p>Demo credentials:</p>
          <p>demo@ecoecho.ai / password123</p>
        </div>
      </div>
    </div>
  );
}
