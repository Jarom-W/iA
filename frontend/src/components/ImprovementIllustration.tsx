import { useState } from "react";
import { estimateImprovement } from "../utils/estimateImprovement";
import type { ImprovementEstimate } from "../utils/estimateImprovement";
import calculationSource from "../utils/estimateImprovement.ts?raw";
import { usd } from "../content/pricing";

const fields = [
  { key: "hoursSavedPerMonth", label: "Hours saved per month", unit: "hours" },
  { key: "valuePerHour", label: "Estimated value per hour", unit: "USD / hour" },
  { key: "addedMonthlyCost", label: "Added monthly cost", unit: "USD / month" },
  { key: "setupCost", label: "One-time setup cost", unit: "USD" },
] as const;

function highlight(line: string) {
  return line.split(/(\/\/.*$|"[^"]*"|\b(?:export|type|function|const|return|if|throw|new|number|null)\b|\b\d+\b)/g).map((token, index) => {
    const kind = token.startsWith("//") ? "comment" : token.startsWith('"') ? "string" : /^(export|type|function|const|return|if|throw|new)$/.test(token) ? "keyword" : /^(number|null|\d+)$/.test(token) ? "value" : "plain";
    return <span className={`syntax-${kind}`} key={index}>{token}</span>;
  });
}

export default function ImprovementIllustration() {
  const [values, setValues] = useState({ hoursSavedPerMonth: "8", valuePerHour: "50", addedMonthlyCost: "75", setupCost: "1500" });
  const invalid = fields.filter(({ key }) => values[key].trim() === "" || !Number.isFinite(Number(values[key])) || Number(values[key]) < 0);
  let result: ReturnType<typeof estimateImprovement> | null = null;
  let calculationError = "";
  if (!invalid.length) {
    try {
      const input = Object.fromEntries(fields.map(({ key }) => [key, Number(values[key])])) as ImprovementEstimate;
      result = estimateImprovement(input);
    } catch (error) {
      calculationError = error instanceof Error ? error.message : "Check the values and try again.";
    }
  }
  const payback = result?.paybackMonths;
  const paybackLabel = payback == null ? "No payback under these assumptions"
    : payback === 0 ? "Immediate" : payback < 0.1 ? "Less than 0.1 months" : `${payback.toFixed(1)} months`;

  return (
    <section className="section craft-section" aria-labelledby="craft-title">
      <div className="container">
        <div className="section-heading split-heading">
          <div><p className="section-kicker">The thinking behind the work</p><h2 id="craft-title">A useful improvement<br /><span>should make sense.</span></h2></div>
          <p>Before building an automation, ask what it might be worth. A small, inspectable calculation can make assumptions visible—and a decision easier to discuss.</p>
        </div>
        <div className="estimate-shell">
          <div className="estimate-inputs">
            <p className="small-label">Illustrative estimate / Not a client result</p>
            <h3>Would this improvement pay for itself?</h3>
            <p id="estimate-help">These are hypothetical sample inputs. Change them to explore the assumptions.</p>
            <div className="estimate-fields">
              {fields.map(({ key, label, unit }) => {
                const isInvalid = invalid.some(field => field.key === key);
                return <label key={key} htmlFor={`estimate-${key}`}><span id={`label-${key}`}>{label}</span><span className="input-unit">{unit}</span>
                  <input id={`estimate-${key}`} aria-labelledby={`label-${key}`} type="number" min="0" step="any" inputMode="decimal" value={values[key]} aria-invalid={isInvalid} aria-describedby={isInvalid ? `error-${key}` : "estimate-help"} onChange={event => setValues({ ...values, [key]: event.target.value })} />
                  {isInvalid && <span className="field-error" id={`error-${key}`}>Enter a finite, non-negative amount.</span>}
                </label>;
              })}
            </div>
          </div>
          <div className="estimate-results" aria-live="polite" aria-atomic="true">
            {result ? <>
              <p className="small-label">Estimated net value</p>
              <p className="estimate-total">{usd(result.netMonthlyValue)}<span>/ month</span></p>
              <dl><div><dt>Estimated value of time freed</dt><dd>{usd(result.monthlyTimeValue)} / month</dd></div><div><dt>Estimated setup payback</dt><dd data-testid="payback">{paybackLabel}</dd></div></dl>
              <p>Time value represents estimated capacity, not necessarily cash savings.</p>
            </> : <div className="estimate-incomplete"><p className="small-label">Check your assumptions</p><h3>Let’s use valid numbers.</h3><p>{calculationError || "Complete all four fields with non-negative numbers to see the estimate."}</p></div>}
          </div>
        </div>
        <p className="estimate-caveat">A starting point, not a forecast or guarantee. This simple estimate excludes uncertainty around adoption, maintenance, and whether the freed time is productively used. Real decisions need the business context.</p>
        <details className="calculation-details">
          <summary><span>View the actual calculation</span><span className="small-label">TypeScript <span aria-hidden="true">+</span></span></summary>
          <p className="code-explanation">This is the same function powering the estimate above. Positive monthly value supports a payback estimate; zero or negative value does not.</p>
          <div className="code-panel" tabIndex={0} role="region" aria-label="TypeScript improvement estimate source code"><pre><code>{calculationSource.split("\n").map((line, index) => <span className="code-line" key={index}><span className="line-number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span><span>{highlight(line)}{"\n"}</span></span>)}</code></pre></div>
        </details>
      </div>
    </section>
  );
}
