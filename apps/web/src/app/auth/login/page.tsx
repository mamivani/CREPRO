import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Login to CREPRO</CardTitle>
          <CardDescription>Sign in with your account</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* OAuth Buttons */}
          <div className="space-y-2">
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                // Redirect to Microsoft OAuth
                window.location.href = `${process.env.NEXT_PUBLIC_IDENTITY_URL}/api/v1/auth/microsoft`;
              }}
              data-testid="microsoft-login"
            >
              Sign in with Microsoft
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                // Redirect to Google OAuth
                window.location.href = `${process.env.NEXT_PUBLIC_IDENTITY_URL}/api/v1/auth/google`;
              }}
              data-testid="google-login"
            >
              Sign in with Google
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                // Redirect to Apple OAuth
                window.location.href = `${process.env.NEXT_PUBLIC_IDENTITY_URL}/api/v1/auth/apple`;
              }}
              data-testid="apple-login"
            >
              Sign in with Apple
            </Button>
          </div>

          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-card text-muted-foreground">Or</span>
            </div>
          </div>

          {/* Local Login Form */}
          <form className="space-y-4" data-testid="local-login-form">
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                Email
              </label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                required
                data-testid="email-input"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                Password
              </label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                required
                data-testid="password-input"
              />
            </div>
            <Button type="submit" className="w-full" data-testid="local-login-button">
              Sign In
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
