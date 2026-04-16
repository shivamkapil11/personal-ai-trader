Gains — Technical Product Specification & Implementation Blueprint
Project Overview
Product Name: Gains Vision: A premium AI-driven personal trading platform designed for high-signal stock analysis and decision-making. Core Objective: Low-friction onboarding (Google Auth/Kite Integration) leading to immediate stock analysis.


________________


1. Design System & Tokens
Color Palette (Dark Mode First)
Token
	Hex/Value
	Usage
	background/base
	#0F1113
	Main page background
	background/elevated
	#1A1D1F
	Cards and sidebar
	background/panel
	#232629
	Modals and dropdowns
	accent/gains-green
	#22C55E
	Primary actions, Bullish states (Restrained)
	status/blue
	#3B82F6
	Trust, Info, Kite Integration
	status/amber
	#F59E0B
	Medium risk, Watch states
	status/red
	#EF4444
	High risk, Bearish states
	text/primary
	#F4F4F5
	Headlines and titles
	text/secondary
	#A1A1AA
	Body copy
	border/subtle
	rgba(255, 255, 255, 0.08)
	Card borders
	Typography
* Primary Font: Modern Sans-Serif (Inter, SF Pro, or Geist).
* Secondary Font: Monospace (JetBrains Mono) — Optional for tickers and metrics only.
* Styles: Crisp, finance-grade, generous letter-spacing for headlines.


________________


2. Component System Specifications
The Search Engine (Core Component)
* Visuals: Large, centered input with subtle elevation.
* States: Focus glow (Gains Green), loading pulse.
* Features: Ticker search, "Compare" toggle, recent search chips.
Modular Dashboard Cards
* Summary Card: High-impact. Displays "Buy/Watch/Avoid," Time Horizon (Swing/Long), and Expected Return.
* Score Meters: Use segmented bars or semi-ring meters for Risk and Conviction. Avoid "neon" glow.
* Analysis Grid: 2x2 grid for Technical Snapshot, Fundamental Snapshot, Opportunity Sizing, and Context Layer.


________________


3. Screen-by-Screen Implementation Logic
Screen 1: Landing Page
* Hero Section: Split layout. Left: Value prop + Google Sign-in. Right: Premium product mockup (dark UI).
* Features: Grid of 4 cards (Technical Analysis, Risk Scoring, Conviction Rating, Opportunity Sizing).
* Integration Section: Focus on "Kite Connect" benefits but emphasize "No-Broker Required" to reduce friction.
Screen 2: Onboarding Flow
* Auth: Minimalist Google OAuth card.
* Segmentation: "Do you use Zerodha Kite?" choice.
* Connect Screen: Focus on "Read-only access" and "No trade execution" to build trust.
Screen 3: The Dashboard (Main App)
* Layout: Slim left sidebar + fluid main canvas.
* Empty State: Centered search with "Start by analyzing a stock" micro-copy.
* Active State: Immediate transition from search to modular card results.


________________


4. Technical Constraints for Codex
* Framework: Next.js 14 (App Router).
* Styling: Tailwind CSS (using the tokens defined above).
* Animations: Framer Motion (Fade-ins and smooth panel expansions only).
* Icons: Lucide React (Thin stroke).


________________


5. Interaction Principles
1. Progressive Disclosure: Show the summary first; reveal detailed metrics on click/scroll.
2. Speed to Value: Search must be the primary action.
3. Subtle Motion: No "bouncing" or flashy gradients. Use duration: 0.2s for all transitions.


________________




Created for: Gains Development Team