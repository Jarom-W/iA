import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import Services from "./components/Services";
import Problems from "./components/Problems";
import ImprovementIllustration from "./components/ImprovementIllustration";
import Pricing from "./components/Pricing";
import About from "./components/About";
import Faq from "./components/Faq";
import Process from "./components/Process";
import Contact from "./components/Contact";
import Footer from "./components/Footer";

function App() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Navbar />

      <main id="main-content">
        <Hero />
        <Problems />
        <Services />
        <Process />
        <ImprovementIllustration />
        <Pricing />
        <About />
        <Faq />
        <Contact />
      </main>

      <Footer />
    </>
  );
}

export default App;
