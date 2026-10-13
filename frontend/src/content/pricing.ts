export const usd = (amount: number) => new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", maximumFractionDigits: 0,
}).format(amount);

export const pricing = {
  projects: [

  {
      id: "consultation", group: "common", name: "Initial Consultation", amount: 0, starting: false,
      summary: "Meet together and discuss your business. Where do you feel bottlenecks lie?",
      includes: ["30 minute virtual session", "Documented discussion" ],
      note: "I look forward to meeting you! Let's talk about where you believe your business is losing money, or where it could systematically improve.",
      detail: "You'll receive an emailed report of our conversation as recorded by an Ai agent."
  },
    {
      id: "assessment", group: "common", name: "Focused Business Assessment", amount: 250, starting: false,
      summary: "Get a clear recommendation on one defined business problem.",
      includes: ["Review of agreed information", "A working conversation", "A written recommendation with priorities"],
      note: "A focused assessment, not a full business audit. Larger or messy engagements are scoped separately.",
      detail: "We agree on the question and information needed before starting. The deliverable is a practical recommendation for that question, with priorities and explicit assumptions.",
    },
    {
      id: "website", group: "common", name: "Marketing Website", amount: 500, starting: true,
      summary: "A clear, useful website that helps the right people take the next step.",
      includes: ["Option for multiple pages, using an agreed layout and supplied business content", "Responsive implementation, an inquiry path, and foundational on-page search setup", "Two consolidated revision rounds within scope, plus launch handoff"],
      note: "Hosting and care are separate. No guaranteed rankings, traffic, or lead counts.",
      detail: "Copywriting, brand identity, ecommerce, complex booking, extensive migration, and custom integrations are separately scoped. Page count, content responsibilities, and supported features are agreed in writing.",
    },
    {
      id: "sprint", group: "advanced", name: "Implementation Sprint", amount: null, starting: true,
      summary: "Move one agreed improvement from a decision to something usable.",
      includes: ["Relevant planning and implementation", "Testing against the agreed outcome", "A documented handoff"],
      note: "A focused work window. Timing depends on scope and access; this is not a full-time developer week or an unlimited task list.",
      detail: "The sprint covers one defined improvement. Dependencies, client access, third-party services, and acceptance criteria are agreed before work begins. Additional work needs a separate agreement.",
    },
    {
      id: "custom", group: "advanced", name: "Custom Systems", amount: null, starting: false,
      summary: "Integrations, internal tools, and bespoke workflows when existing tools do not fit well enough.",
      includes: ["Options and constraints considered before a build", "Scope, ownership, and operating costs made clear", "Implementation and support quoted for the actual system"],
      note: "Scoped after discovery. There is no universal starting price for a custom system.",
      detail: "When uncertainty calls for paid technical discovery, we first agree on its deliverable: a feasibility review, options, key risks, and a proposed implementation scope. Discovery is used when needed, not required for every conversation.",
    },
  ],
  technicalDiscovery: { name: "Paid technical discovery", amount: 1000 },
  otherProjects: [
  ],
  websiteCare: [
    {
      name: "Website Care", amount: 50,
      summary: "Hosting and care for a supported simple marketing site.",
      includes: ["HTTPS, monitoring, and agreed form checks", "Routine upkeep and recovery support"],
      note: "Content changes are separate. Traffic, storage, and supported features are scoped; unusually demanding use is quoted separately.",
    },
    {
      name: "Care & Updates", amount: 149,
      summary: "Website Care, with room for small content changes.",
      includes: ["Everything in Website Care", "Up to 2 hours of minor content changes per month", "A brief quarterly review"],
      note: "Unused time does not roll over. Redesigns and new features must remain within this time constraint otherwise, an additional engagement will be required.",
    },
  ],
  businessSupport: [
    {
      name: "Business Review", amount: 395,
      summary: "A regular review of the measures and decisions that matter.",
      includes: ["Monthly review of agreed measures and current priorities", "Practical recommendations and follow-up", "Up to 4 total hours across preparation, meeting, and follow-up"],
      note: "The review has an agreed scope. Additional analysis or implementation needs a separate agreement.",
    },
    {
      name: "Business Partner", amount: 795,
      summary: "Continuity across business priorities and small improvements.",
      includes: ["Ongoing analysis and vendor coordination", "Small, agreed improvements", "Up to four total hours per month across meetings and delivery"],
      note: "Larger projects are quoted separately. This is scoped support, not unlimited access.",
    },
  ],
  terms: [
    "All prices are in USD. Recurring services are optional; consulting and implementation are available on their own.",
    "Website hosting and care are separate from business support. Each has its own agreed scope.",
    "Software subscriptions, advertising spend, and significant third-party costs are additional when relevant. Additional work requires agreement.",
  ],
} as const;
