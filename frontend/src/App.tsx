import { useState, useEffect } from "react";
import { ThemeProvider } from "next-themes";
import { Toaster } from "./components/ui/sonner";
import { Login } from "./components/auth/login";
import { Signup } from "./components/auth/signup";
import { EmailVerification } from "./components/auth/email-verification";
import { TwoFactorSetup } from "./components/auth/two-factor-setup";
import { TwoFactorVerify } from "./components/auth/two-factor-verify";
import { BackupCodes } from "./components/auth/backup-codes";
import { ChatScreen } from "./components/screens/chat-screen";
import { ScriptGenerationScreen } from "./components/screens/script-generation-screen";
import { LibraryScreen } from "./components/screens/library-screen";
import { LibraryOverviewScreen } from "./components/screens/library-overview-screen";
import { ProjectsScreen } from "./components/screens/projects-screen";
import { ProjectDetailScreen } from "./components/screens/project-detail-screen";
import { PROJECTS, type Project } from "./data/projects";
import { isInvitedUser } from "./data/invited-users";
import { toast } from "sonner";

// Session storage keys
const SESSION_KEY = "resonance_session";
const SESSION_DURATION = 30 * 24 * 60 * 60 * 1000; // 30 days in milliseconds

interface SessionData {
  email: string;
  timestamp: number;
}

type AuthStep = 
  | "login" 
  | "signup" 
  | "2fa-verify" 
  | "email-verification" 
  | "2fa-setup" 
  | "backup-codes" 
  | "authenticated";
type AppView = 
  | "chat" 
  | "script-generation" 
  | "projects" 
  | "project-detail"
  | "library"
  | "library-videos" 
  | "library-audio" 
  | "library-transcripts" 
  | "library-pdfs";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

interface Chat {
  id: string;
  title: string;
  messages: Message[];
  starred?: boolean;
  projectId?: string;
  projectName?: string;
}

function App() {
  const [authStep, setAuthStep] = useState<AuthStep>("login");
  const [currentView, setCurrentView] = useState<AppView>("chat");
  const [userEmail, setUserEmail] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [isNewUser, setIsNewUser] = useState(false); // Track if this is signup flow
  
  // Shared chat state across all screens - start with empty array
  const [allChats, setAllChats] = useState<Chat[]>([]);
  
  // Shared projects state - initialize with default projects
  const [allProjects, setAllProjects] = useState<Project[]>(PROJECTS);

  // Check for existing session on mount
  useEffect(() => {
    const sessionData = localStorage.getItem(SESSION_KEY);
    if (sessionData) {
      try {
        const session: SessionData = JSON.parse(sessionData);
        const now = new Date().getTime();
        
        // Check if session is still valid (within 30 days)
        if (now - session.timestamp < SESSION_DURATION) {
          setUserEmail(session.email);
          setAuthStep("authenticated");
          toast.success("Welcome back!", {
            description: `Signed in as ${session.email}`,
          });
        } else {
          // Session expired
          localStorage.removeItem(SESSION_KEY);
          toast.info("Session expired", {
            description: "Please sign in again for security.",
          });
        }
      } catch (error) {
        console.error("Invalid session data:", error);
        localStorage.removeItem(SESSION_KEY);
      }
    }
  }, []);

  // Save session when authenticated
  const saveSession = (email: string) => {
    const session: SessionData = {
      email,
      timestamp: new Date().getTime(),
    };
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  };

  // Logout handler
  const handleLogout = () => {
    localStorage.removeItem(SESSION_KEY);
    setAuthStep("login");
    setUserEmail("");
    setAllChats([]);
    toast.success("Signed out successfully");
  };

  // Auth handlers - Login flow (existing users)
  const handleLogin = (email: string, password: string) => {
    console.log("Login:", email, password);
    setUserEmail(email);
    setIsNewUser(false);
    // Existing users go straight to 2FA verification
    setAuthStep("2fa-verify");
  };

  // Auth handlers - Signup flow (new users)
  const handleSignup = (data: { email: string; password: string; firstName: string; lastName: string; timezone: string }) => {
    console.log("Signup:", data);
    setUserEmail(data.email);
    setIsNewUser(true);
    // New users must verify email first
    setAuthStep("email-verification");
  };

  const handleEmailVerify = (code: string) => {
    console.log("Email verified:", code);
    // After email verification, new users set up 2FA
    setAuthStep("2fa-setup");
  };

  const handle2FASetup = (code: string) => {
    console.log("2FA setup:", code);
    // After 2FA setup, show backup codes
    setAuthStep("backup-codes");
  };

  const handle2FAVerify = (code: string) => {
    console.log("2FA verified:", code);
    // After 2FA verification for returning users, they're authenticated
    saveSession(userEmail);
    setAuthStep("authenticated");
    toast.success("Welcome back!", {
      description: "You have been successfully authenticated.",
    });
  };

  const handleBackupCodesComplete = () => {
    console.log("Backup codes saved");
    // After saving backup codes (new users), they're authenticated
    saveSession(userEmail);
    setAuthStep("authenticated");
    toast.success("Account created!", {
      description: "Your account has been successfully created.",
    });
  };

  const handleUseBackupCode = () => {
    toast.info("Backup code", {
      description: "Backup code functionality coming soon. Please contact support.",
    });
  };

  // Navigation handlers
  const handleProjectSelect = (projectId: string) => {
    setSelectedProjectId(projectId);
    setCurrentChatId(null); // Clear current chat when selecting project folder
    setCurrentView("project-detail");
  };

  const handleBackToProjects = () => {
    setCurrentView("projects");
    setSelectedProjectId(null);
  };

  const handleNewProject = () => {
    console.log("Creating new project");
    // In a real app, this would create a new project and navigate to it
  };

  const handleLibraryNavigation = (libraryType: "videos" | "audio" | "transcripts" | "pdfs") => {
    setCurrentView(`library-${libraryType}` as AppView);
  };

  const handleNewChat = () => {
    setCurrentView("chat");
    setCurrentChatId(null);
  };

  const handleProjectsNavigation = () => {
    setCurrentView("projects");
  };

  const handleLibraryHomeNavigation = () => {
    setCurrentView("library");
  };

  const handleVideoScriptClick = () => {
    setCurrentView("script-generation");
    setCurrentChatId(null);
  };

  const handleChatSelect = (chatId: string) => {
    const selectedChat = allChats.find(chat => chat.id === chatId);
    
    // If chat belongs to a project, navigate to project detail view
    if (selectedChat?.projectId) {
      setSelectedProjectId(selectedChat.projectId);
      setCurrentChatId(chatId);
      setCurrentView("project-detail");
    } else {
      // Chat doesn't belong to a project, go to regular chat view
      setCurrentChatId(chatId);
      setCurrentView("chat");
    }
  };

  // Mock data for 2FA
  const mockQRCode = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect width='200' height='200' fill='%23fff'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' fill='%23000'%3EQR Code%3C/text%3E%3C/svg%3E";
  const mockSecret = "JBSWY3DPEHPK3PXP";
  const mockBackupCodes = [
    "A1B2C3D4",
    "E5F6G7H8",
    "I9J0K1L2",
    "M3N4O5P6",
    "Q7R8S9T0",
    "U1V2W3X4",
    "Y5Z6A7B8",
    "C9D0E1F2",
  ];

  // Render auth flow - Login (existing users)
  if (authStep === "login") {
    return (
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <Login 
          onLogin={handleLogin} 
          onSignupClick={() => setAuthStep("signup")}
          onForgotPassword={() => {
            toast.info("Password reset", {
              description: "Password reset functionality coming soon. For demo purposes, please contact support.",
            });
          }}
        />
        <Toaster />
      </ThemeProvider>
    );
  }

  // Render auth flow - Signup (new users)
  if (authStep === "signup") {
    return (
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <Signup 
          onSignup={handleSignup} 
          onBackToLogin={() => setAuthStep("login")}
        />
        <Toaster />
      </ThemeProvider>
    );
  }

  // Email verification (new users only)
  if (authStep === "email-verification") {
    return (
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <EmailVerification
          email={userEmail}
          onVerify={handleEmailVerify}
          onBack={() => setAuthStep("signup")}
        />
        <Toaster />
      </ThemeProvider>
    );
  }

  // 2FA Setup (new users only)
  if (authStep === "2fa-setup") {
    return (
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <TwoFactorSetup
          qrCode={mockQRCode}
          secret={mockSecret}
          onComplete={handle2FASetup}
        />
        <Toaster />
      </ThemeProvider>
    );
  }

  // 2FA Verification (returning users only)
  if (authStep === "2fa-verify") {
    return (
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <TwoFactorVerify
          email={userEmail}
          onVerify={handle2FAVerify}
          onBack={() => setAuthStep("login")}
          onUseBackupCode={handleUseBackupCode}
        />
        <Toaster />
      </ThemeProvider>
    );
  }

  // Backup codes (new users only)
  if (authStep === "backup-codes") {
    return (
      <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
        <BackupCodes
          codes={mockBackupCodes}
          onComplete={handleBackupCodesComplete}
        />
        <Toaster />
      </ThemeProvider>
    );
  }

  // Main app - render based on current view
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem>
      {currentView === "chat" && (
        <ChatScreen
          onProjectClick={handleProjectSelect}
          onLibraryClick={handleLibraryNavigation}
          onProjectsClick={handleProjectsNavigation}
          onLibraryHeaderClick={handleLibraryHomeNavigation}
          onNewChat={handleNewChat}
          allChats={allChats}
          setAllChats={setAllChats}
          currentChatId={currentChatId}
          onChatSelect={handleChatSelect}
        />
      )}
      {currentView === "script-generation" && <ScriptGenerationScreen />}
      {currentView === "projects" && (
        <ProjectsScreen
          onProjectSelect={handleProjectSelect}
          onNewProject={handleNewProject}
          onLibraryClick={handleLibraryNavigation}
          onProjectsClick={handleProjectsNavigation}
          onLibraryHeaderClick={handleLibraryHomeNavigation}
          onNewChat={handleNewChat}
          allChats={allChats}
          setAllChats={setAllChats}
          onChatSelect={handleChatSelect}
          currentChatId={currentChatId}
          allProjects={allProjects}
          setAllProjects={setAllProjects}
        />
      )}
      {currentView === "project-detail" && selectedProjectId && (
        <ProjectDetailScreen
          projectId={selectedProjectId}
          projectName={allProjects.find(project => project.id === selectedProjectId)?.name}
          onBack={handleBackToProjects}
          onProjectClick={handleProjectSelect}
          onLibraryClick={handleLibraryNavigation}
          onProjectsClick={handleProjectsNavigation}
          onLibraryHeaderClick={handleLibraryHomeNavigation}
          onNewChat={handleNewChat}
          allChats={allChats}
          setAllChats={setAllChats}
          initialChatId={currentChatId}
          onChatSelect={handleChatSelect}
        />
      )}
      {currentView === "library" && (
        <LibraryOverviewScreen
          onProjectClick={handleProjectSelect}
          onLibraryClick={handleLibraryNavigation}
          onProjectsClick={handleProjectsNavigation}
          onLibraryHeaderClick={handleLibraryHomeNavigation}
          onNewChat={handleNewChat}
          allChats={allChats}
          onChatSelect={handleChatSelect}
        />
      )}
      {currentView === "library-videos" && (
        <LibraryScreen
          type="videos"
          onProjectClick={handleProjectSelect}
          onLibraryClick={handleLibraryNavigation}
          onProjectsClick={handleProjectsNavigation}
          onLibraryHeaderClick={handleLibraryHomeNavigation}
          onNewChat={handleNewChat}
          allChats={allChats}
          onChatSelect={handleChatSelect}
        />
      )}
      {currentView === "library-audio" && (
        <LibraryScreen
          type="audio"
          onProjectClick={handleProjectSelect}
          onLibraryClick={handleLibraryNavigation}
          onProjectsClick={handleProjectsNavigation}
          onLibraryHeaderClick={handleLibraryHomeNavigation}
          onNewChat={handleNewChat}
          allChats={allChats}
          onChatSelect={handleChatSelect}
        />
      )}
      {currentView === "library-transcripts" && (
        <LibraryScreen
          type="transcripts"
          onProjectClick={handleProjectSelect}
          onLibraryClick={handleLibraryNavigation}
          onProjectsClick={handleProjectsNavigation}
          onLibraryHeaderClick={handleLibraryHomeNavigation}
          onNewChat={handleNewChat}
          allChats={allChats}
          onChatSelect={handleChatSelect}
        />
      )}
      {currentView === "library-pdfs" && (
        <LibraryScreen
          type="pdfs"
          onProjectClick={handleProjectSelect}
          onLibraryClick={handleLibraryNavigation}
          onProjectsClick={handleProjectsNavigation}
          onLibraryHeaderClick={handleLibraryHomeNavigation}
          onNewChat={handleNewChat}
          allChats={allChats}
          onChatSelect={handleChatSelect}
        />
      )}
      <Toaster />
    </ThemeProvider>
  );
}

export default App;