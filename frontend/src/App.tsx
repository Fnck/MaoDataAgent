import { useEffect } from "react";
import { useStore } from "./store";
import { setOnUnauthorized } from "./api";
import LoginPage from "./components/LoginPage";
import Layout from "./components/Layout";

export default function App() {
  const token = useStore((s) => s.token);
  const logout = useStore((s) => s.logout);

  useEffect(() => {
    setOnUnauthorized(logout);
  }, [logout]);

  if (!token) {
    return <LoginPage />;
  }
  return <Layout />;
}
