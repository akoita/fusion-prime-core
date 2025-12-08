import { Link, useLocation } from 'react-router-dom'

// STRATEGIC MENU: Each item maps to a competitive advantage in pitch deck
const navigation = [
  { name: 'Portfolio', href: '/', icon: '📊', description: 'Multi-chain aggregation' },
  { name: 'Risk Monitor', href: '/margin', icon: '⚡', description: 'Real-time margin health' },
  { name: 'My Escrows', href: '/escrow/manage', icon: '🔒', description: 'View escrows by role' },
  { name: 'Create Escrow', href: '/escrow/create', icon: '➕', description: 'Create multi-party escrow' },
  { name: 'Vault Dashboard', href: '/vault', icon: '💰', description: 'View and manage vault balances' },
  { name: 'Cross-Chain', href: '/cross-chain', icon: '🔗', description: 'Manual sync (troubleshooting)', badge: '⚙️' },
]

// REMOVED (Feature creep - not needed for demo):
// - Analytics (nice to have, not critical)
// - Web3 Demo (dev tool, not production feature)
// - Vault Management (consolidated into Cross-Chain)
// - Cross-Chain Settle (consolidated into Cross-Chain)
// - Message Tracker (consolidated into Cross-Chain)
// - Collateral Snapshot (consolidated into Cross-Chain)

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="w-64 border-r border-white/10 bg-black/20 backdrop-blur-xl">
      <nav className="p-4">
        <ul className="space-y-2">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href ||
              (item.href === '/escrow/manage' && location.pathname.startsWith('/escrow/')) ||
              (item.href === '/cross-chain' && location.pathname.startsWith('/cross-chain'))
            return (
              <li key={item.name}>
                <Link
                  to={item.href}
                  className={`
                    flex items-center gap-3 px-4 py-2 rounded-lg transition-colors
                    ${isActive
                      ? 'bg-blue-500/20 text-blue-300 font-medium border border-blue-500/30'
                      : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'
                    }
                  `}
                >
                  <span className="text-xl">{item.icon}</span>
                  <div className="flex flex-col flex-1">
                    <div className="flex items-center gap-2">
                      <span>{item.name}</span>
                      {item.badge && (
                        <span className="text-xs bg-yellow-500/20 text-yellow-300 px-2 py-0.5 rounded-full font-semibold border border-yellow-500/30">
                          MANUAL
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <span className="text-xs text-gray-500 group-hover:text-gray-400 transition-colors">{item.description}</span>
                    )}
                  </div>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}
