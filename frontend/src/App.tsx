import { lazy, Suspense } from "react";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import PageSurface from "./components/PageSurface";

const pages = {
  home: lazy(() => import("./pages/HomePage")),
  services: lazy(() => import("./pages/ServicesPage")),
  approach: lazy(() => import("./pages/ApproachPage")),
  pricing: lazy(() => import("./pages/PricingPage")),
  about: lazy(() => import("./pages/AboutPage")),
  contact: lazy(() => import("./pages/ContactPage")),
};

function App() {
  const path = window.location.pathname.replace(/^\/+|\/+$/g, "").replace(/\/index\.html$/, "");
  const page = path in pages ? path as keyof typeof pages : "home";
  const Page = pages[page];
  return <>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <Navbar />
    <PageSurface>
      <main id="main-content" className={page === "home" ? undefined : "page-content"}>
        <Suspense fallback={<div className="page-loading" role="status">Loading page…</div>}><Page /></Suspense>
      </main>
      <Footer />
    </PageSurface>
  </>;
}
export default App;
