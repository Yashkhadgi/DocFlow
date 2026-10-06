import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login, register } from '../api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/Card';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { useToast } from '../components/Toast';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const toast = useToast();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('demo@docflow.app');
  const [password, setPassword] = useState('Demo@1234');
  const [fullName, setFullName] = useState('Demo User');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isRegister) {
        await register({ email, password, full_name: fullName });
        await login({ email, password });
        toast.success('Account created and logged in successfully!');
      } else {
        await login({ email, password });
        toast.success('Signed in successfully!');
      }
      navigate('/');
    } catch (err: any) {
      toast.error(err?.error?.message || err?.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto my-12">
      <Card className="shadow-md">
        <CardHeader className="text-center">
          <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-white shadow-sm shadow-indigo-600/30 mx-auto mb-3">
            DF
          </div>
          <CardTitle className="text-xl font-bold">
            {isRegister ? 'Create Account' : 'Welcome back to DocFlow'}
          </CardTitle>
          <CardDescription>
            {isRegister
              ? 'Sign up for automated invoice processing'
              : 'Sign in to access your document dashboard'}
          </CardDescription>
        </CardHeader>

        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {isRegister && (
              <Input
                label="Full Name"
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Asha Sharma"
              />
            )}

            <Input
              label="Email Address"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="demo@docflow.app"
            />

            <Input
              label="Password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              fullWidth
              isLoading={loading}
              className="mt-2"
            >
              {isRegister ? 'Register Account' : 'Sign In'}
            </Button>
          </CardContent>

          <CardFooter className="justify-center border-t border-slate-100 bg-slate-50/50">
            <button
              type="button"
              onClick={() => setIsRegister(!isRegister)}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold"
            >
              {isRegister
                ? 'Already have an account? Sign in'
                : "Don't have an account? Create one"}
            </button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
};
