---
name: eli5
description: Explain a topic like I'm a 5 year old using a dead-simple visual HTML artifact with big pictures, diagrams, and few words. Use when the user types /eli5 [topic] or asks for a simple visual, picture-book style explanation of how something works.
---

# eli5 — Explain Like I'm 5 (Visual Picture Explainer)

Explain complex topics, codebases, system architectures, or technical concepts to someone with zero prerequisite knowledge using **big pictures and few words** via a self-contained HTML artifact.

Inspired by Thariq Shihipar's viral Claude Code skill.

## When to Use

- User explicitly invokes `/eli5 <topic>` or `/eli5`.
- User asks for a beginner-level, intuitive, or picture-book style explanation:
  - "5살도 이해할 수 있게 설명해줘", "그림으로 쉽게 설명해줘", "시각적으로 설명해줘"
  - "Explain like I'm 5", "Give me a dead-simple visual explainer", "Picture book explanation".
- When onboarding team members to an unfamiliar system, explaining technical debt/trade-offs, or illustrating incident root causes without overwhelming them with text.

## Core Principles

1. **Zero Prerequisite Knowledge**: Assume no prior background in the domain. Avoid jargon or translate it immediately into everyday metaphors.
2. **Big Pictures, Few Words**: Emphasize visual hierarchy, clear flow diagrams, iconography/SVGs, and concise bullet points rather than long paragraphs.
3. **Analogy First**: Anchor the concept with a relatable real-world comparison (e.g., DNS as a phonebook, Load Balancer as a restaurant host, Git as a time machine / save point system).
4. **Interactive / Visual HTML Artifact**: Always generate a clean, self-contained, responsive HTML artifact that can be viewed directly in the browser or side-pane.

---

## Workflow

### 1. Extract the Topic & Core Metaphor
- Determine the target topic from `$ARGUMENTS` or conversation context.
- Identify:
  - **The Core Problem**: What problem does this solve?
  - **The Everyday Analogy**: What daily-life object or situation works like this?
  - **The Flow / Mechanism**: 3 to 4 chronological steps showing how it works.
  - **The "Before & After" or "With & Without"**: What happens if we don't have it?

### 2. Generate the HTML Artifact
Create a self-contained `.html` file with:
- **Responsive & Modern Styling**: Tailwind CSS via CDN (`https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js` or standard Tailwind) or clean standalone CSS.
- **Theme-aware Design**: High-contrast, clean card-based layout (neutral backgrounds, smooth border-radius, soft shadows).
- **Visual Flow & Diagrams**: Embedded SVGs, icon cards, numbered step-by-step tracks, or flowcharts.
- **Bite-sized Text**: Bold keywords, short 1-2 sentence captions, and high visual emphasis.

#### Recommended HTML Structure Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ELI5: [Topic]</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
</head>
<body class="bg-slate-50 text-slate-800 antialiased p-6 sm:p-10 min-h-screen flex flex-col items-center">
  <main class="max-w-3xl w-full space-y-8">
    <!-- Header -->
    <header class="text-center space-y-2">
      <span class="inline-block px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-semibold uppercase tracking-wider">ELI5 Explainer</span>
      <h1 class="text-3xl sm:text-4xl font-extrabold text-slate-900">[Topic Title]</h1>
      <p class="text-lg text-slate-600 max-w-xl mx-auto">[One-sentence intuitive summary using an analogy]</p>
    </header>

    <!-- The Big Analogy Card -->
    <section class="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-4">
      <div class="flex items-center gap-3">
        <span class="text-2xl">💡</span>
        <h2 class="text-xl font-bold text-slate-900">The Everyday Analogy</h2>
      </div>
      <p class="text-base text-slate-700 leading-relaxed">[Real-world metaphor explained simply]</p>
    </section>

    <!-- Visual Step-by-Step Flow -->
    <section class="space-y-4">
      <h2 class="text-xl font-bold text-slate-900 text-center sm:text-left">How It Works (Step-by-Step)</h2>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <!-- Step 1 -->
        <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col items-center text-center space-y-3">
          <div class="w-12 h-12 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-lg">1</div>
          <h3 class="font-bold text-slate-900">[Step 1 Name]</h3>
          <p class="text-sm text-slate-600">[Short 1-line explanation]</p>
        </div>
        <!-- Step 2 -->
        <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col items-center text-center space-y-3">
          <div class="w-12 h-12 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold text-lg">2</div>
          <h3 class="font-bold text-slate-900">[Step 2 Name]</h3>
          <p class="text-sm text-slate-600">[Short 1-line explanation]</p>
        </div>
        <!-- Step 3 -->
        <div class="bg-white rounded-xl p-5 border border-slate-200 shadow-sm flex flex-col items-center text-center space-y-3">
          <div class="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold text-lg">3</div>
          <h3 class="font-bold text-slate-900">[Step 3 Name]</h3>
          <p class="text-sm text-slate-600">[Short 1-line explanation]</p>
        </div>
      </div>
    </section>

    <!-- Comparison: With vs. Without -->
    <section class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="bg-rose-50 border border-rose-200 rounded-xl p-5 space-y-2">
        <h3 class="font-bold text-rose-900 flex items-center gap-2"><span>❌</span> Without [Topic]</h3>
        <p class="text-sm text-rose-800">[What pain or problem occurs]</p>
      </div>
      <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-5 space-y-2">
        <h3 class="font-bold text-emerald-900 flex items-center gap-2"><span>✨</span> With [Topic]</h3>
        <p class="text-sm text-emerald-800">[How life is simple and easy]</p>
      </div>
    </section>

    <!-- One Line Takeaway -->
    <footer class="bg-slate-900 text-white rounded-2xl p-6 text-center space-y-2">
      <p class="text-xs uppercase tracking-widest text-slate-400 font-semibold">Key Takeaway</p>
      <p class="text-lg font-medium text-slate-100">"[One memorable takeaway sentence]"</p>
    </footer>
  </main>
</body>
</html>
```

### 3. Deliver the Response
- Save the HTML artifact using `write_to_file` (or Claude artifact mechanism).
- In the chat response, provide:
  1. A 2-3 sentence punchy summary.
  2. Direct link or embed to the created visual HTML artifact.
