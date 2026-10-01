import type { Metadata } from 'next';
import './style.css';
export const metadata: Metadata = { title: 'Customer Data Onboarding Agent', description: 'AI-assisted customer data onboarding with deterministic validation and human review.' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
