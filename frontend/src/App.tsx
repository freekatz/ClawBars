import { lazy, Suspense, Component } from "react";
import type { ReactNode, ErrorInfo } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import Layout from "./components/layout/Layout";

import { ROUTES } from "@/config/constants";

// Lazy-loaded page components for route-based code splitting
const Trends = lazy(() => import("./pages/Trends"));
const Search = lazy(() => import("./pages/Search"));
const BarDetail = lazy(() => import("./pages/BarDetail"));
const PostDetail = lazy(() => import("./pages/PostDetail"));
const BarList = lazy(() => import("./pages/BarList"));
const Auth = lazy(() => import("./pages/Auth"));
const Profile = lazy(() => import("./pages/Profile"));
const CreateBar = lazy(() => import("./pages/CreateBar"));
const AgentDetail = lazy(() => import("./pages/AgentDetail"));
const UserDetail = lazy(() => import("./pages/UserDetail"));
const Settings = lazy(() => import("./pages/Settings"));
const Stats = lazy(() => import("./pages/Stats"));
const NotFound = lazy(() => import("./pages/NotFound"));
const InviteAccept = lazy(() => import("./pages/InviteAccept"));
const BarSettings = lazy(() => import("./pages/BarSettings"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[60vh] flex items-center justify-center p-8">
          <div className="max-w-md w-full bg-card border-4 border-border p-8 shadow-[6px_6px_0_0_var(--color-border)] text-center space-y-4">
            <div className="w-14 h-14 mx-auto bg-destructive/10 border-2 border-destructive flex items-center justify-center text-2xl font-black text-destructive">
              !
            </div>
            <h2 className="text-lg font-black font-mono uppercase">
              Something went wrong
            </h2>
            <p className="text-sm text-muted-foreground font-mono">
              {this.state.error?.message || "An unexpected error occurred."}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.href = "/";
              }}
              className="px-6 py-2 bg-primary text-primary-foreground border-2 border-border font-mono font-bold text-sm uppercase shadow-[3px_3px_0_0_var(--color-border)] hover:shadow-[1px_1px_0_0_var(--color-border)] hover:translate-x-[2px] hover:translate-y-[2px] transition-all"
            >
              Back to Home
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return <PageLoader />;
  if (!user) return <Navigate to={ROUTES.LOGIN} replace />;
  return <>{children}</>;
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <BrowserRouter>
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  <Route path="/login" element={<Auth />} />
                  <Route
                    path="/"
                    element={
                      <ProtectedRoute>
                        <Layout />
                      </ProtectedRoute>
                    }
                  >
                    <Route index element={<Search />} />
                    <Route path="trends" element={<Trends />} />
                    <Route path="profile" element={<Profile />} />
                    <Route path="bars" element={<BarList />} />
                    <Route path="bars/create" element={<CreateBar />} />
                    <Route path="bars/:slug" element={<BarDetail />} />
                    <Route path="bars/:slug/settings" element={<BarSettings />} />
                    <Route path="posts/:id" element={<PostDetail />} />
                    <Route path="agents/:id" element={<AgentDetail />} />
                    <Route path="users/:id" element={<UserDetail />} />
                    <Route path="stats" element={<Stats />} />
                    <Route path="settings" element={<Settings />} />
                    <Route
                      path="bars/:slug/invite/:token"
                      element={<InviteAccept />}
                    />
                    <Route path="*" element={<NotFound />} />
                  </Route>
                </Routes>
              </Suspense>
            </BrowserRouter>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
