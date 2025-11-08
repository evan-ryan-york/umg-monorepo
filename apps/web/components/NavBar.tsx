'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { PenLine, MessageSquare, BookOpen, Sun, FileText } from 'lucide-react';

export function NavBar(): React.ReactElement {
  const pathname = usePathname();

  const navLinks = [
    { href: '/', label: 'Quick Capture', icon: PenLine },
    { href: '/mentor/chat', label: 'Chat with Mentor', icon: MessageSquare },
    { href: '/log', label: 'Activity Log', icon: BookOpen },
    { href: '/digest', label: 'Daily Digest', icon: Sun },
    { href: '/prompts', label: 'Prompts', icon: FileText },
  ];

  return (
    <nav className="border-b bg-card">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="text-xl font-bold">
              UMG
            </Link>
            <div className="flex gap-2">
              {navLinks.map((link) => {
                const isActive = pathname === link.href;
                const Icon = link.icon;
                return (
                  <Link key={link.href} href={link.href}>
                    <Button
                      variant={isActive ? 'default' : 'ghost'}
                      size="sm"
                      className="gap-2"
                    >
                      <Icon className="h-4 w-4" />
                      {link.label}
                    </Button>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
