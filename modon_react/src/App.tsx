import { AppProvider, useApp } from './context/AppContext';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Developers from './pages/Developers';
import Deals from './pages/Deals';
import Mortgages from './pages/Mortgages';
import Rentals from './pages/Rentals';
import Land from './pages/Land';
import Valuation from './pages/Valuation';
import Projects from './pages/Projects';

function PageRouter() {
  const { state } = useApp();

  switch (state.currentPage) {
    case 'dashboard':  return <Dashboard />;
    case 'developers': return <Developers />;
    case 'deals':      return <Deals />;
    case 'mortgages':  return <Mortgages />;
    case 'rentals':    return <Rentals />;
    case 'land':       return <Land />;
    case 'valuation':  return <Valuation />;
    case 'projects':   return <Projects />;
    default:           return <Dashboard />;
  }
}

export default function App() {
  return (
    <AppProvider>
      <Layout>
        <PageRouter />
      </Layout>
    </AppProvider>
  );
}
