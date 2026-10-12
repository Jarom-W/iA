import { pricing } from "./pricing";

export const business = {
  name: "Inflection Architectures",
  legalName: "Inflection Architectures LLC",
  founder: "Jarom Wardwell",
  domain: "https://inflectionarchitectures.com",
  email: "jaromwardwell@gmail.com",
  contactEndpoint: "https://formsubmit.co/ajax/jaromwardwell@gmail.com",
  github: "https://github.com/Jarom-W",
  linkedin: "https://www.linkedin.com/in/jarom-wardwell-9b8121214",
  localContext: "Based in Utah County. Working with owner-led businesses across the Wasatch Front.",
};

export const navigation = [
  { name: "Services", href: "/#services" },
  { name: "Approach", href: "/#process" },
  { name: "Pricing", href: "/#pricing" },
  { name: "About", href: "/#about" },
];

export const hero = {
  category: "Business & Technology Partner",
  headline: ["Better systems.", "Stronger business."],
  description: "I help small business owners reduce wasted work, make informed decisions, and put the right technology to work—from a better website to the systems behind the business.",
  primaryAction: "Let’s talk about your business",
  secondaryAction: "Explore services",
};

export const problems = [
  { title: "Inquiries come in. Follow-up slips.", description: "A request lands in a text, an inbox, or a form. The next step depends on someone remembering it." },
  { title: "More subscriptions. Still manual work.", description: "The software bill grows, but the team still copies information between tools. Start by checking what each service actually provides." },
  { title: "The website makes things harder.", description: "It is difficult to update, unclear about what you do, or missing an obvious way for a visitor to get in touch." },
  { title: "Plenty of numbers. Not enough clarity.", description: "Information exists, but it does not help you decide what to prioritize, what to spend, or what comes next." },
];

export const services = [
  {
    id: "clarity", title: "Business clarity", descriptor: "Understand before you invest.",
    description: "Get a useful view of a cost, a workflow, or a decision. I examine the information with you and separate the real constraint from the symptoms.",
    work: "Focused diagnostics · Financial models and forecasts · Operating reports · Software evaluation",
    deliverable: "A written recommendation, decision model, or operating report with clear assumptions and priorities.",
    next: "Start with one question you need to answer.",
  },
  {
    id: "websites", title: "Websites & visibility", descriptor: "Make the next step obvious.",
    description: "Help visitors understand your business and make contact. Improve an existing site, plan a supported migration, or build a clear marketing website.",
    work: "Marketing websites · Messaging and inquiry paths · Supported migrations · Scoped search visibility work",
    deliverable: "A usable website or a scoped set of improvements, with an inquiry path and launch handoff.",
    next: "Start with your current website—or what you need it to do.",
  },
  {
    id: "systems", title: "Systems & implementation", descriptor: "Turn a decision into better daily work.",
    description: "Choose and configure existing software, connect a workflow, or introduce automation with sensible human oversight. Build custom only when it earns its place.",
    work: "Software setup · Workflow connections · Useful AI and automation · Custom tools and integrations",
    deliverable: "One agreed improvement, tested with the people using it, plus documentation and a clear handoff.",
    next: "Start with a task, a bottleneck, or an agreed priority.",
  },
];

export const processSteps = [
  { title: "Understand", description: "Map the problem, current workflow, costs, and constraints. Agree on what needs to get better." },
  { title: "Decide", description: "Compare process changes, existing tools, integrations, and custom work. Weigh the cost and fit of each." },
  { title: "Implement", description: "Agree on scope, deliver something usable, and test it with the people who will rely on it." },
  { title: "Improve", description: "Review what changed. Adjust the next priority and continue with scoped support when it is useful." },
];

export const workflow = [
  { name: "Inquiry", issue: "Requests arrive through several channels, with no clear owner for the next step.", intervention: "Choose one place to record inquiries and assign follow-up. Connect the website form if it removes a real handoff." },
  { name: "Estimate", issue: "Quotes depend on scattered notes, outdated prices, or information that was never collected.", intervention: "Agree on the required information and a repeatable estimate template. Evaluate your existing quoting tools before adding another." },
  { name: "Job", issue: "The accepted estimate does not reliably become a scheduled job with a clear scope.", intervention: "Define the handoff: approved work, responsible person, schedule, and changes. Configure the tools the team can actually maintain." },
  { name: "Invoice", issue: "Completed work waits to be invoiced because details or approvals are missing.", intervention: "Create a completion checklist and an agreed invoice trigger. Automate a draft where useful, with a person reviewing it." },
  { name: "Payment", issue: "Open invoices are difficult to track, and follow-up is inconsistent.", intervention: "Use an agreed receivables view and follow-up process. Check whether the accounting software already supports the needed reminders." },
];

export const workingPractices = [
  "Written scope and clear deliverables.",
  "Plain-English recommendations and transparent fees.",
  "Existing tools considered before custom development.",
  "Clear ownership and a documented handoff.",
  "Ongoing support with explicit boundaries.",
];

export const faqs = [
  { question: "Can we start with my existing website or software?", answer: "Yes. I start with what you already have: how it works, what it costs, and where it falls short. Improvements or a supported migration may be more sensible than replacing it. Access, compatibility, and any existing service commitments are reviewed before agreeing on changes." },
  { question: "Will you recommend software we can buy instead of building something?", answer: "Yes. A process change or an existing tool is often the right answer. I compare cost, fit, maintainability, and the work required to adopt it. Custom development is an option when those alternatives do not meet the need well enough." },
  { question: "Do I need ongoing support?", answer: "No. Recurring services are optional, and you can start with consulting or implementation without buying hosting. A project can end with a documented handoff. If continuing support would help, we agree on its scope and fees separately." },
  { question: "Who owns the website and accounts?", answer: "Your domain stays in your name and control, with delegated access as needed. Simple marketing sites can use my managed hosting for convenience. Paid-for website deliverables can be handed over, subject to documented third-party license terms. More complex or business-critical systems generally run in your cloud accounts, with direct vendor billing and delegated management access." },
  { question: "What does monthly website care include?", answer: `${pricing.websiteCare[0].summary} It includes ${pricing.websiteCare[0].includes.join("; ").toLowerCase()}. ${pricing.websiteCare[0].note} Care & Updates adds ${pricing.websiteCare[1].includes.slice(1).join(" and ").toLowerCase()}. ${pricing.websiteCare[1].note} Care is separate from business advisory support; it does not promise uninterrupted availability or an after-hours response.` },
  { question: "How does a project begin?", answer: "Tell me about your business and what you would like to improve. We start with a short fit conversation to see whether I can help and identify a sensible next step. That is different from a paid assessment or technical discovery, which has an agreed deliverable and fee. No project work begins until scope and fees are agreed." },
];
