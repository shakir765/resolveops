import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "./components/Layout";
import { UserGate } from "./components/UserGate";
import { UserProvider } from "./context/UserContext";
import { MyTicketsPage } from "./pages/MyTicketsPage";
import { NewTicketPage } from "./pages/NewTicketPage";
import { TicketDetailPage } from "./pages/TicketDetailPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5_000,
    },
  },
});

function AppRoutes() {
  return (
    <UserGate>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<NewTicketPage />} />
          <Route path="tickets" element={<MyTicketsPage />} />
          <Route path="tickets/:ticketId" element={<TicketDetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </UserGate>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <UserProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </UserProvider>
    </QueryClientProvider>
  );
}
