# Inflection Architectures

Static marketing site for Inflection Architectures LLC, built with React, TypeScript, Vite, and Tailwind CSS.

## Local development

```bash
npm install
npm run dev
```

## Checks

```bash
npm run lint
npm test
npm run build
```

## Deploy to GitHub Pages

Push to `main` to run the **Deploy website** GitHub Actions workflow, or run it manually from Actions. It installs locked dependencies (`npm ci`), runs lint and all website tests, and builds with TypeScript and Vite before uploading and deploying the Pages artifact. A failed check blocks deployment.

The test suites cover contact validation/submission, the interactive approach curve, improvement calculations, and the improvement calculator UI.

GitHub Pages should use **GitHub Actions** as its build source. The former Stasis release fetching, encryption, artifact checks, tests, and daily refresh schedule have been retired; deployment requires no Stasis secrets or repository variables.

`npm run deploy` is the legacy manual publisher to the `gh-pages` branch; use the Actions workflow for the current deployment pipeline.

The site is configured for the custom domain `https://inflectionarchitectures.com`.

## Contact form activation

The contact form uses [FormSubmit](https://formsubmit.co/) to send inquiries to `jaromwardwell@gmail.com` without a server. After the first submission from the deployed site, open the activation email from FormSubmit and confirm the address. This one-time step is required before messages can be delivered.

## Marketing content and pricing

- `src/content/site.ts`: verified business/contact details, hero copy, navigation, services, process examples, and FAQs.
- `src/content/pricing.ts`: all public prices, included scope, exclusions, and recurring-service boundaries. Update this source to keep offers and the care FAQ consistent.
- `src/components/`: focused homepage sections; supporting section copy lives with its component.
- `src/utils/estimateImprovement.ts`: the actual calculation used by the illustrative estimate.
- `public/banner.png` and `public/logo.png`: supplied branding and favicon.

Preview the production build locally with `npm run build` followed by `npm run preview -- --host 127.0.0.1 --port 4173`. No deployment is needed.

Contact tests mock the existing FormSubmit endpoint. An accepted API response is required before the site shows confirmation; tests do not establish real email delivery. Verify activation separately before relying on the form. The visible email link provides a direct alternative.

## Page structure

The homepage is a short introduction. Navigation opens dedicated `/services/`, `/approach/`, `/pricing/`, `/about/`, and `/contact/` pages. Page compositions are maintained in `src/pages/`; shared sections remain in `src/components/`. Each page has its own HTML entry with a description and canonical URL, registered in `vite.config.ts`, so direct links and refreshes work on GitHub Pages without server rewrites.

`src/main.tsx` forwards the previous homepage section links to their corresponding pages. Navigation links are maintained in `src/content/site.ts`.

The Approach page uses an interactive cubic curve in `src/components/Process.tsx`. Its slope stays positive, eases before Implement, and steepens after Implement, the inflection point. Hover, touch, focus, and arrow keys select a step and its details. The calculator remains interactive without a public source-code panel.
