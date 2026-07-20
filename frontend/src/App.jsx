import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./state/AuthContext";
import { ThemeProvider } from "./theme/ThemeProvider";
import { ToastHost } from "./widgets/ToastHost";
import { Spinner } from "./widgets/common";

import SplashScreen from "./screens/SplashScreen";
import LoginScreen from "./screens/LoginScreen";
import HomeScreen from "./screens/HomeScreen";
import CreateMovieScreen from "./screens/CreateMovieScreen";
import GenerationProgressScreen from "./screens/GenerationProgressScreen";
import MyMoviesScreen from "./screens/MyMoviesScreen";
import PreviewScreen from "./screens/PreviewScreen";
import ExportScreen from "./screens/ExportScreen";
import SettingsScreen from "./screens/SettingsScreen";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size={28} />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<SplashScreen />} />
      <Route path="/login" element={<LoginScreen />} />

      <Route path="/home" element={<ProtectedRoute><HomeScreen /></ProtectedRoute>} />
      <Route path="/create" element={<ProtectedRoute><CreateMovieScreen /></ProtectedRoute>} />
      <Route path="/create/:projectId" element={<ProtectedRoute><CreateMovieScreen /></ProtectedRoute>} />
      <Route path="/generating/:projectId" element={<ProtectedRoute><GenerationProgressScreen /></ProtectedRoute>} />
      <Route path="/movies" element={<ProtectedRoute><MyMoviesScreen /></ProtectedRoute>} />
      <Route path="/preview/:projectId" element={<ProtectedRoute><PreviewScreen /></ProtectedRoute>} />
      <Route path="/export/:projectId" element={<ProtectedRoute><ExportScreen /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsScreen /></ProtectedRoute>} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <ToastHost />
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}
