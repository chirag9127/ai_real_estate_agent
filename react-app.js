import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom';

const ToggleSwitch = ({ active, onClick }) => {
  const toggleStyle = {
    width: '44px',
    height: '24px',
    border: '1px solid #0d0d0d',
    borderRadius: '99px',
    position: 'relative',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    padding: '2px'
  };

  const toggleAfterStyle = {
    width: '18px',
    height: '18px',
    background: '#0d0d0d',
    borderRadius: '50%',
    position: 'absolute',
    left: '2px',
    transition: 'transform 0.2s',
    transform: active ? 'translateX(20px)' : 'translateX(0)'
  };

  return (
    <div style={toggleStyle} onClick={onClick}>
      <div style={toggleAfterStyle}></div>
    </div>
  );
};

const NavItem = ({ href, active, children, onClick }) => {
  const [isHovered, setIsHovered] = useState(false);
  
  const navItemStyle = {
    padding: (isHovered || active) ? '24px 24px 24px 32px' : '24px',
    borderBottom: '1px solid #0d0d0d',
    textDecoration: 'none',
    color: '#0d0d0d',
    fontFamily: "'Oswald', sans-serif",
    fontSize: '28px',
    textTransform: 'uppercase',
    fontWeight: '400',
    letterSpacing: '0.5px',
    transition: 'background 0.2s, padding-left 0.2s',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: (isHovered || active) ? 'rgba(0,0,0,0.05)' : 'transparent',
    cursor: 'pointer'
  };

  const iconStyle = {
    opacity: (isHovered || active) ? 1 : 0,
    fontSize: '16px',
    transition: 'opacity 0.2s'
  };

  return (
    <div
      style={navItemStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

const KPICard = ({ color, label, number, icon, value, subtitle }) => {
  const cardStyle = {
    border: '1px solid #0d0d0d',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    minHeight: '220px',
    position: 'relative',
    backgroundColor: color === 'orange' ? '#ff5e25' : color === 'green' ? '#4f9664' : '#f2f2f2'
  };

  const iconStyle = {
    width: '40px',
    height: '40px',
    border: '1px solid #0d0d0d',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '20px',
    marginBottom: '64px'
  };

  const labelStyle = {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: '10px',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    marginBottom: '4px',
    display: 'flex',
    justifyContent: 'space-between',
    borderBottom: '1px solid rgba(0,0,0,0.1)',
    paddingBottom: '4px'
  };

  const valueStyle = {
    fontFamily: "'Oswald', sans-serif",
    fontSize: '48px',
    textTransform: 'uppercase',
    lineHeight: '0.9'
  };

  const subStyle = {
    fontSize: '10px',
    marginTop: '8px',
    opacity: '0.7'
  };

  const geoShapeStyle = color === 'white' ? {
    position: 'absolute',
    opacity: '0.5',
    pointerEvents: 'none',
    border: '1px solid #0d0d0d',
    borderRadius: '50%',
    width: '80px',
    height: '80px',
    right: '-20px',
    bottom: '-20px'
  } : null;

  return (
    <article style={cardStyle}>
      <div style={labelStyle}>
        <span>{label}</span>
        <span>{number}</span>
      </div>
      <div style={iconStyle}>{icon}</div>
      <div>
        <div style={valueStyle}>{value}</div>
        <div style={subStyle}>{subtitle}</div>
      </div>
      {geoShapeStyle && <div style={geoShapeStyle}></div>}
    </article>
  );
};

const FilterPill = ({ active, onClick, children }) => {
  const [isHovered, setIsHovered] = useState(false);
  
  const pillStyle = {
    padding: '4px 12px',
    border: '1px solid #0d0d0d',
    borderRadius: '99px',
    fontSize: '11px',
    textTransform: 'uppercase',
    cursor: 'pointer',
    transition: 'all 0.2s',
    background: (active || isHovered) ? '#0d0d0d' : 'transparent',
    color: (active || isHovered) ? '#d4d4d4' : '#0d0d0d'
  };

  return (
    <div
      style={pillStyle}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {children}
    </div>
  );
};

const ListingRow = ({ image, price, address, status, details }) => {
  const [isHovered, setIsHovered] = useState(false);
  
  const rowStyle = {
    display: 'grid',
    gridTemplateColumns: '80px 2fr 1fr 1fr 100px',
    borderBottom: '1px solid #0d0d0d',
    alignItems: 'center',
    transition: 'background 0.1s',
    background: isHovered ? 'rgba(255,255,255,0.4)' : 'transparent'
  };

  const imgStyle = {
    width: '100%',
    height: '50px',
    backgroundColor: '#999',
    borderRight: '1px solid #0d0d0d',
    display: 'block',
    objectFit: 'cover',
    filter: 'grayscale(100%)'
  };

  const cellStyle = {
    padding: '12px 24px',
    fontSize: '12px'
  };

  const mainCellStyle = {
    ...cellStyle,
    display: 'flex',
    flexDirection: 'column',
    gap: '2px'
  };

  const priceStyle = {
    fontFamily: "'Oswald', sans-serif",
    fontSize: '18px',
    fontWeight: '500'
  };

  const addressStyle = {
    opacity: '0.7',
    textTransform: 'uppercase',
    fontSize: '10px'
  };

  const statusPillStyle = {
    display: 'inline-block',
    padding: '2px 8px',
    border: '1px solid #0d0d0d',
    fontSize: '9px',
    textTransform: 'uppercase',
    borderRadius: '99px',
    textAlign: 'center',
    width: 'fit-content',
    background: status === 'Active' ? '#ff5e25' : status === 'Sold' ? '#4f9664' : 'transparent',
    borderColor: status === 'Sold' ? '#4f9664' : '#0d0d0d',
    color: status === 'Sold' ? '#000' : '#0d0d0d'
  };

  return (
    <div
      style={rowStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <img src={image} alt="" style={imgStyle} />
      <div style={mainCellStyle}>
        <span style={priceStyle}>{price}</span>
        <span style={addressStyle}>{address}</span>
      </div>
      <div style={cellStyle}>
        <span style={statusPillStyle}>{status}</span>
      </div>
      <div style={{...cellStyle, fontSize: '10px'}}>
        {details}
      </div>
      <div style={{...cellStyle, textAlign: 'right'}}>
        →
      </div>
    </div>
  );
};

const Dashboard = () => {
  const [sidebarToggle, setSidebarToggle] = useState(false);
  const [liveUpdates, setLiveUpdates] = useState(true);
  const [activeFilter, setActiveFilter] = useState('All');
  const [activeNav, setActiveNav] = useState('Dashboard');

  const listings = [
    {
      image: 'https://images.unsplash.com/photo-1600596542815-200903823460?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
      price: '$850,000',
      address: '124 Industrial Ave, Downtown',
      status: 'Active',
      details: '2 BEDS / 2 BATHS'
    },
    {
      image: 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
      price: '$1,200,000',
      address: '8802 Concrete Blvd, Sector 4',
      status: 'Sold',
      details: '3 BEDS / 2.5 BATHS'
    },
    {
      image: 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
      price: '$450,000',
      address: '901 Loft St, Arts District',
      status: 'Pending',
      details: '1 BED / 1 BATH'
    },
    {
      image: 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?ixlib=rb-4.0.3&auto=format&fit=crop&w=200&q=80',
      price: '$2,400,000',
      address: '55 Skyway Dr, Penthouse',
      status: 'Active',
      details: '4 BEDS / 4 BATHS'
    }
  ];

  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=Anton&family=IBM+Plex+Mono:wght@400;500;600&family=Oswald:wght@300;400;500;700&display=swap');
      
      * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }

      body {
        background-color: #d4d4d4;
        color: #0d0d0d;
        font-family: 'IBM Plex Mono', monospace;
        height: 100vh;
        overflow: hidden;
      }

      body::after {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.08'/%3E%3C/svg%3E");
        pointer-events: none;
        z-index: 9999;
      }
    `;
    document.head.appendChild(style);
    return () => document.head.removeChild(style);
  }, []);

  const appContainerStyle = {
    display: 'grid',
    gridTemplateColumns: '260px 1fr',
    width: '100%',
    height: '100vh',
    border: '1px solid #0d0d0d',
    margin: '12px',
    background: '#d4d4d4',
    overflow: 'hidden'
  };

  const sidebarStyle = {
    borderRight: '1px solid #0d0d0d',
    display: 'flex',
    flexDirection: 'column',
    background: '#d4d4d4'
  };

  const sidebarHeaderStyle = {
    padding: '24px',
    borderBottom: '1px solid #0d0d0d',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const brandStyle = {
    fontFamily: "'Oswald', sans-serif",
    textTransform: 'uppercase',
    fontSize: '20px',
    letterSpacing: '1px'
  };

  const sidebarFooterStyle = {
    marginTop: 'auto',
    padding: '24px',
    borderTop: '1px solid #0d0d0d',
    fontSize: '10px',
    textTransform: 'uppercase',
    display: 'flex',
    justifyContent: 'space-between'
  };

  const mainContentStyle = {
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
    position: 'relative'
  };

  const bgGridStyle = {
    backgroundImage: 'radial-gradient(#0d0d0d 1px, transparent 1px)',
    backgroundSize: '24px 24px',
    opacity: '0.1',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    pointerEvents: 'none',
    zIndex: 0
  };

  const headerBarStyle = {
    padding: '24px 32px',
    borderBottom: '1px solid #0d0d0d',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: '#d4d4d4',
    zIndex: 1
  };

  const pageTitleStyle = {
    fontFamily: "'Oswald', sans-serif",
    textTransform: 'uppercase',
    fontSize: '14px',
    letterSpacing: '1px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  };

  const userControlsStyle = {
    display: 'flex',
    gap: '24px',
    alignItems: 'center'
  };

  const dashboardGridStyle = {
    padding: '32px',
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '24px',
    zIndex: 1
  };

  const listingsContainerStyle = {
    margin: '0 32px 32px',
    border: '1px solid #0d0d0d',
    background: '#d4d4d4',
    zIndex: 1
  };

  const listingsHeaderStyle = {
    padding: '24px',
    borderBottom: '1px solid #0d0d0d',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: '#d4d4d4'
  };

  const filterGroupStyle = {
    display: 'flex',
    gap: '12px'
  };

  const fabStyle = {
    position: 'absolute',
    bottom: '32px',
    right: '32px',
    width: '64px',
    height: '64px',
    background: '#0d0d0d',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#d4d4d4',
    fontSize: '24px',
    cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
    zIndex: 10,
    transition: 'transform 0.2s'
  };

  const [fabHovered, setFabHovered] = useState(false);

  return (
    <div style={appContainerStyle}>
      <aside style={sidebarStyle}>
        <div style={sidebarHeaderStyle}>
          <div style={brandStyle}>EstateOS</div>
          <div style={brandStyle}>V2.0</div>
        </div>
        
        <nav style={{display: 'flex', flexDirection: 'column'}}>
          <NavItem active={activeNav === 'Dashboard'} onClick={() => setActiveNav('Dashboard')}>
            Dashboard <span style={{opacity: activeNav === 'Dashboard' ? 1 : 0, fontSize: '16px', transition: 'opacity 0.2s'}}>●</span>
          </NavItem>
          <NavItem active={activeNav === 'Listings'} onClick={() => setActiveNav('Listings')}>
            Listings <span style={{opacity: activeNav === 'Listings' ? 1 : 0, fontSize: '16px', transition: 'opacity 0.2s'}}>→</span>
          </NavItem>
          <NavItem active={activeNav === 'Clients'} onClick={() => setActiveNav('Clients')}>
            Clients <span style={{opacity: activeNav === 'Clients' ? 1 : 0, fontSize: '16px', transition: 'opacity 0.2s'}}>→</span>
          </NavItem>
          <NavItem active={activeNav === 'Calendar'} onClick={() => setActiveNav('Calendar')}>
            Calendar <span style={{opacity: activeNav === 'Calendar' ? 1 : 0, fontSize: '16px', transition: 'opacity 0.2s'}}>→</span>
          </NavItem>
          <NavItem active={activeNav === 'Reports'} onClick={() => setActiveNav('Reports')}>
            Reports <span style={{opacity: activeNav === 'Reports' ? 1 : 0, fontSize: '16px', transition: 'opacity 0.2s'}}>→</span>
          </NavItem>
        </nav>

        <div style={sidebarFooterStyle}>
          <span>User: Agent 04</span>
          <ToggleSwitch active={sidebarToggle} onClick={() => setSidebarToggle(!sidebarToggle)} />
        </div>
      </aside>

      <main style={mainContentStyle}>
        <div style={bgGridStyle}></div>

        <header style={headerBarStyle}>
          <div style={pageTitleStyle}>
            <span>→</span>
            <span>Overview / October 2023</span>
          </div>
          <div style={userControlsStyle}>
            <span style={{fontSize: '11px', textTransform: 'uppercase'}}>Live Updates</span>
            <ToggleSwitch active={liveUpdates} onClick={() => setLiveUpdates(!liveUpdates)} />
          </div>
        </header>

        <div style={dashboardGridStyle}>
          <KPICard
            color="orange"
            label="Active Listings"
            number="01"
            icon="☻"
            value="24"
            subtitle="Matching Efficiency +12%"
          />
          <KPICard
            color="green"
            label="Total Sales"
            number="02"
            icon="⊕"
            value="$4.2M"
            subtitle="Monthly Target 88%"
          />
          <KPICard
            color="white"
            label="Client Requests"
            number="03"
            icon="✉"
            value="18"
            subtitle="3 High Priority"
          />
        </div>

        <section style={listingsContainerStyle}>
          <div style={listingsHeaderStyle}>
            <div style={{fontFamily: "'Oswald', sans-serif", textTransform: 'uppercase'}}>Recent Properties</div>
            <div style={filterGroupStyle}>
              <FilterPill active={activeFilter === 'All'} onClick={() => setActiveFilter('All')}>All</FilterPill>
              <FilterPill active={activeFilter === 'Residential'} onClick={() => setActiveFilter('Residential')}>Residential</FilterPill>
              <FilterPill active={activeFilter === 'Commercial'} onClick={() => setActiveFilter('Commercial')}>Commercial</FilterPill>
            </div>
          </div>

          <div>
            {listings.map((listing, index) => (
              <ListingRow key={index} {...listing} />
            ))}
          </div>
        </section>

        <div
          style={{...fabStyle, transform: fabHovered ? 'scale(1.05)' : 'scale(1)'}}
          onMouseEnter={() => setFabHovered(true)}
          onMouseLeave={() => setFabHovered(false)}
        >
          →
        </div>
      </main>
    </div>
  );
};

const App = () => {
  return (
    <Router basename="/">
      <Routes>
        <Route path="/" element={<Dashboard />} />
      </Routes>
    </Router>
  );
};

export default App;