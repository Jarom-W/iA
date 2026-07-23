import Navbar from "./components/Navbar";
import Hero from "./components/Hero";
import Services from "./components/Services";
import Industries from "./components/Industries";
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
        <Services />
        <Industries />
        <Process />
        <Contact />
      </main>

      <Footer />
    </>
  );
}

export default App;
