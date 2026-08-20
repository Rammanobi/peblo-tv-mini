import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../lib/AuthContext';
import { ApiError } from '../api/client';

const schema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, status } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  if (status === 'authenticated') return <Navigate to="/shows" replace />;

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await login(values.email, values.password);
    } catch (err) {
      if (err instanceof ApiError) {
        setServerError(err.message);
      } else {
        setServerError('Login failed. Please try again.');
      }
    }
  };

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={handleSubmit(onSubmit)} noValidate>
        <h1>Peblo TV CMS</h1>
        <p className="muted">Sign in with your editor or admin account.</p>

        <label htmlFor="email">Email</label>
        <input id="email" type="email" autoComplete="username" {...register('email')} />
        {errors.email && <p className="field-error">{errors.email.message}</p>}

        <label htmlFor="password">Password</label>
        <input id="password" type="password" autoComplete="current-password" {...register('password')} />
        {errors.password && <p className="field-error">{errors.password.message}</p>}

        {serverError && (
          <div className="form-server-error" role="alert">
            {serverError}
          </div>
        )}

        <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
