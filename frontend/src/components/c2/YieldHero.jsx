import plant from "../../assets/c2/nai-miris-plant.svg";
import YieldIcon from "./YieldIcon";

export default function YieldHero() {
  return (
    <section className="c2-hero" aria-labelledby="yield-heading">
      <div className="c2-hero-copy">
        <span className="c2-eyebrow c2-eyebrow-light"><span className="c2-status-dot" /> C2 · YIELD RESEARCH WORKSPACE</span>
        <h1 id="yield-heading">Small traits.<br /><em>New insights.</em></h1>
        <p>Explore the yield potential of Nai Miris through plant traits, machine learning, and transparent research.</p>
        <div className="c2-hero-actions">
          <a className="c2-button c2-button-lime" href="#yield-estimator">Estimate yield <YieldIcon name="arrow" /></a>
          <a className="c2-text-link" href="#yield-evidence">Explore the evidence <span aria-hidden="true">↗</span></a>
        </div>
        <span className="c2-hero-note"><YieldIcon name="flask" /> Experimental trait-based estimates</span>
      </div>
      <div className="c2-botanical">
        <span className="c2-botanical-orbit" aria-hidden="true" />
        <span className="c2-botanical-orbit c2-botanical-orbit-inner" aria-hidden="true" />
        <span className="c2-botanical-label">CAPSICUM CHINENSE<span>Nai Miris</span></span>
        <img className="c2-plant" src={plant} width="480" height="480" alt="Botanical illustration of a Nai Miris plant with green leaves and ripening orange and red peppers" />
        <span className="c2-illustration-note">Botanical illustration · not a simulation</span>
      </div>
    </section>
  );
}
