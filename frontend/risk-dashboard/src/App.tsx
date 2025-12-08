import { Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import Layout from './components/layout/Layout'
import Login from './pages/Login'
import PortfolioOverview from './features/portfolio/PortfolioOverview'
import MarginMonitor from './features/margin/MarginMonitor'
// REMOVED FROM MENU (Feature creep - not needed for demo)
// import Analytics from './features/analytics/Analytics'
// import Web3Demo from './components/demo/Web3Demo'

// ESCROW PAGES (Working - strategic focus)
import CreateEscrow from './pages/escrow/CreateEscrow'
import ManageEscrows from './pages/escrow/ManageEscrows'
import EscrowDetails from './pages/escrow/EscrowDetails'

// CROSS-CHAIN PAGES
import CrossChainTransfer from './pages/cross-chain/CrossChainTransfer'
import VaultDashboard from './pages/cross-chain/VaultDashboard'
// OLD ROUTES (Consolidated into CrossChainTransfer):
// import VaultManagement from './pages/cross-chain/VaultManagement'
// import CrossChainSettle from './pages/cross-chain/CrossChainSettle'
// import MessageTracker from './pages/cross-chain/MessageTracker'
// import CollateralSnapshot from './pages/cross-chain/CollateralSnapshot'
import { ErrorBoundary } from './components/common/ErrorBoundary'

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout>
                <PortfolioOverview />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/margin"
          element={
            <ProtectedRoute>
              <Layout>
                <MarginMonitor />
              </Layout>
            </ProtectedRoute>
          }
        />
        {/* REMOVED FROM MENU - keeping routes for backward compatibility */}
        {/* <Route
          path="/analytics"
          element={
            <ProtectedRoute>
              <Layout>
                <Analytics />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/web3-demo"
          element={
            <ProtectedRoute>
              <Layout>
                <Web3Demo />
              </Layout>
            </ProtectedRoute>
          }
        /> */}
        <Route
          path="/escrow/create"
          element={
            <ProtectedRoute>
              <Layout>
                <CreateEscrow />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/escrow/manage"
          element={
            <ProtectedRoute>
              <Layout>
                <ManageEscrows />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/escrow/:escrowAddress"
          element={
            <ProtectedRoute>
              <Layout>
                <EscrowDetails />
              </Layout>
            </ProtectedRoute>
          }
        />
        {/* CROSS-CHAIN PAGES */}
        <Route
          path="/cross-chain"
          element={
            <ProtectedRoute>
              <Layout>
                <CrossChainTransfer />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/vault"
          element={
            <ProtectedRoute>
              <Layout>
                <VaultDashboard />
              </Layout>
            </ProtectedRoute>
          }
        />
        {/* OLD CROSS-CHAIN ROUTES - consolidated into /cross-chain */}
        {/* <Route
          path="/cross-chain/vault"
          element={
            <ProtectedRoute>
              <Layout>
                <VaultManagement />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/cross-chain/settle"
          element={
            <ProtectedRoute>
              <Layout>
                <CrossChainSettle />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/cross-chain/messages"
          element={
            <ProtectedRoute>
              <Layout>
                <MessageTracker />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/cross-chain/snapshot"
          element={
            <ProtectedRoute>
              <Layout>
                <CollateralSnapshot />
              </Layout>
            </ProtectedRoute>
          }
        /> */}
        </Routes>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
