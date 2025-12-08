import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import APIReference from './pages/APIReference'
import Playground from './pages/Playground'
import APIKeys from './pages/APIKeys'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/reference" element={<APIReference />} />
        <Route path="/playground" element={<Playground />} />
        <Route path="/keys" element={<APIKeys />} />
      </Routes>
    </Layout>
  )
}

export default App
