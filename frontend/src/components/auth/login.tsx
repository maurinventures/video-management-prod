import { useState } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Mail, Lock, LogIn } from "lucide-react";
import { isInvitedUser } from "../../data/invited-users";
import { toast } from "sonner";

interface LoginProps {
  onLogin: (email: string, password: string) => void;
  onSignupClick?: () => void;
  onForgotPassword?: () => void;
}

export function Login({ onLogin, onSignupClick, onForgotPassword }: LoginProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate if user is invited
    if (!isInvitedUser(email)) {
      toast.error("Access Denied", {
        description: "This email is not on the invited users list. Please contact the administrator.",
      });
      return;
    }
    
    onLogin(email, password);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold mb-2">Internal Platform</h1>
          <p className="text-muted-foreground">Sign in to your AI-powered workspace</p>
        </div>

        <div className="bg-card border border-border rounded-lg p-8 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <Button type="submit" className="w-full" size="lg">
              <LogIn className="mr-2 h-4 w-4" />
              Sign In
            </Button>
          </form>
        </div>

        <div className="flex flex-col items-center gap-2 text-center mt-6">
          <button 
            className="text-[12px] text-primary hover:underline active:text-primary/80 transition-colors" 
            onClick={onForgotPassword}
          >
            Forgot password?
          </button>
          {onSignupClick && (
            <button 
              onClick={onSignupClick} 
              className="text-[12px] text-primary hover:underline active:text-primary/80 transition-colors"
            >
              Create a new account
            </button>
          )}
        </div>
      </div>
    </div>
  );
}