import { useAuth } from '@/contexts/AuthContext'
import { ConnectButton } from '@rainbow-me/rainbowkit'

export default function Header() {
  const { user, logout } = useAuth()

  return (
    <header className="border-b border-white/10 bg-black/20 backdrop-blur-xl px-6 py-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white tracking-tight">
          Fusion Prime <span className="text-gradient">Risk Dashboard</span>
        </h1>
        <div className="flex items-center gap-4">
          {/* Web3 Wallet Connection */}
          <ConnectButton
            chainStatus="icon"
            showBalance={true}
            accountStatus="address"
          />

          {/* User Auth Info */}
          {user && (
            <>
              <div className="h-6 w-px bg-white/10" /> {/* Divider */}
              <span className="text-sm text-gray-300">{user.name}</span>
              <span className="text-xs text-gray-500">({user.role})</span>
              <button
                onClick={logout}
                className="px-3 py-1 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition-colors"
              >
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
