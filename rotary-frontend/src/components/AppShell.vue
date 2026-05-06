<script setup>
import { useEpochStore } from '@/stores/epoch'

const epochStore = useEpochStore()
</script>

<template>
  <div class="app-shell" :class="epochStore.epochClass">
    <header class="header">
      <div class="header-inner">
        <RouterLink to="/" class="logo">RotaryArchiv</RouterLink>

        <nav class="nav-desktop" aria-label="Hauptnavigation">
          <RouterLink to="/" class="nav-link">Startseite</RouterLink>
          <a href="#" class="nav-link">Epochen</a>
          <a href="#" class="nav-link">Karte</a>
          <a href="#" class="nav-link">Netzwerk</a>
          <a href="#" class="nav-link">Über das Projekt</a>
        </nav>

        <div class="header-actions">
          <button class="search-btn" type="button" aria-label="Suche">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.3-4.3"/>
            </svg>
          </button>
          <a href="#" class="login-link">Login</a>

          <details class="nav-mobile-toggle">
            <summary class="hamburger" aria-label="Menü">
              <span></span>
              <span></span>
              <span></span>
            </summary>
            <nav class="nav-mobile" aria-label="Hauptnavigation">
<RouterLink to="/" class="nav-link" aria-current="page">Startseite</RouterLink>
              <a href="#" class="nav-link">Epochen</a>
              <a href="#" class="nav-link">Karte</a>
              <a href="#" class="nav-link">Netzwerk</a>
              <a href="#" class="nav-link">Über das Projekt</a>
              <a href="#" class="nav-link">Login</a>
            </nav>
          </details>
        </div>
      </div>
    </header>

    <main class="main">
      <slot></slot>
    </main>

    <footer class="footer">
      <div class="footer-inner">
        <p class="stats">42 Personen erschlossen</p>
        <RouterLink to="/ueber" class="footer-link">Über das Projekt</RouterLink>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-m) var(--space-l);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-l);
}

.logo {
  font-family: var(--font-serif);
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-primary);
  text-decoration: none;
}

.nav-desktop {
  display: flex;
  gap: var(--space-l);
}

.nav-link {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color var(--transition-fast);
}

.nav-link:hover,
.nav-link.router-link-active,
.nav-link[aria-current="page"] {
  color: var(--color-epoch-primary);
  text-decoration: none;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-m);
}

.search-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: var(--space-xs);
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-btn:hover {
  color: var(--color-epoch-primary);
}

.login-link {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  text-decoration: none;
}

.login-link:hover {
  color: var(--color-epoch-primary);
}

.nav-mobile-toggle {
  display: none;
}

.hamburger {
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  padding: var(--space-xs);
}

.hamburger span {
  width: 24px;
  height: 2px;
  background: var(--color-text-primary);
  border-radius: 2px;
}

.nav-mobile {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: var(--space-m);
  display: flex;
  flex-direction: column;
  gap: var(--space-s);
}

.main {
  flex: 1;
}

.footer {
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  margin-top: auto;
}

.footer-inner {
  max-width: var(--grid-max);
  margin: 0 auto;
  padding: var(--space-l);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.footer-link {
  font-family: var(--font-sans);
  font-size: 0.875rem;
  color: var(--color-epoch-primary);
  text-decoration: none;
}

.footer-link:hover {
  text-decoration: underline;
}

@media (max-width: 768px) {
  .nav-desktop {
    display: none;
  }

  .nav-mobile-toggle {
    display: block;
  }

  .login-link {
    display: none;
  }

  .footer-inner {
    flex-direction: column;
    gap: var(--space-s);
    text-align: center;
  }
}
</style>
