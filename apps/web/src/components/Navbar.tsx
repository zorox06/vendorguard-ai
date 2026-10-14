"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard, Users, Package, Bell, Activity, Upload, BarChart3,
  Building2, ChevronRight, Menu, Search, ArrowUpRight, X, ShieldCheck,
  ChevronsUpDown, Command,
} from "lucide-react";
import { useData } from "./DataProvider";

const primary = [
  { label: "Overview", href: "/", icon: LayoutDashboard },
  { label: "Supplier network", href: "/suppliers", icon: Users },
  { label: "Material coverage", href: "/materials", icon: Package },
  { label: "Action queue", href: "/alerts", icon: Bell },
];
const tools = [
  { label: "Monitoring runs", href: "/runs", icon: Activity },
  { label: "Data imports", href: "/imports", icon: Upload },
  { label: "Replay studio", href: "/replay", icon: BarChart3 },
];
const navigation = [...primary, ...tools];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const { alerts, suppliers } = useData();
  const count = alerts.filter(a => a.status === "open").length;
  const current = navigation.find(n => n.href === "/" ? pathname === "/" : pathname.startsWith(n.href))?.label || "Overview";

  function openSearch() {
    setQuery("");
    dialog.current?.showModal();
    searchInput.current?.focus();
  }
  function navigate(href: string) {
    dialog.current?.close();
    setOpen(false);
    router.push(href);
  }
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openSearch();
      }
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function nav(items: typeof primary) {
    return items.map(item => {
      const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
      return <Link key={item.href} href={item.href} onClick={() => setOpen(false)}
        className={`nav-link ${active ? "active" : ""}`} aria-current={active ? "page" : undefined}>
        <item.icon /><span>{item.label}</span>
        {item.href === "/alerts" && count > 0 ? <span className="nav-count">{count}</span> : active && <span className="nav-active-mark" />}
      </Link>;
    });
  }

  const matches = suppliers.filter(s => [s.legal_name, ...s.materials_supplied].join(" ").toLowerCase().includes(query.toLowerCase()));
  return <>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <button className={`sidebar-backdrop ${open ? "is-open" : ""}`} onClick={() => setOpen(false)} aria-label="Close navigation" tabIndex={open ? 0 : -1} />
    <aside className={`app-sidebar ${open ? "is-open" : ""}`} aria-label="Workspace navigation">
      <Link className="brand" href="/" onClick={() => setOpen(false)}>
        <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
        <span>VendorGuard<span className="brand-period"></span></span>
      </Link>
      <div className="workspace">
        <span className="workspace-icon"><Building2 size={18} /></span>
        <div><strong>VendorGuard</strong><small>Operations workspace</small></div>
        <span className="workspace-monogram">VG</span>
      </div>
      <div className="nav-label">WORKSPACE <span>01 — 04</span></div>
      <nav className="nav-section">{nav(primary)}</nav>
      <div className="nav-label">INTELLIGENCE <span>05 — 07</span></div>
      <nav className="nav-section">{nav(tools)}</nav>
      <div className="sidebar-bottom">
        <div className="sidebar-note">
          <span className="sidebar-note-icon"><ShieldCheck size={18} /></span>
          <p>Clarity before<br /><span>the next disruption.</span></p>
          <Link href="/imports">Connect your data <ArrowUpRight size={14} /></Link>
        </div>
        <div className="user-profile">
          <span className="avatar">VG</span>
          <div><strong>Operations team</strong><small>VendorGuard</small></div>
          <span className="profile-indicator" aria-label="Active workspace"><ShieldCheck size={15} /></span>
        </div>
      </div>
    </aside>
    <div className="app-body">
      <header className="topbar">
        <div className="breadcrumbs">
          <button className="mobile-menu" aria-label="Toggle navigation" aria-expanded={open} onClick={() => setOpen(!open)}><Menu /></button>
          <span className="workspace-breadcrumb">Workspace</span><ChevronRight size={12} /><strong>{current}</strong>
          {pathname.split("/").filter(Boolean).length > 1 && <><ChevronRight size={12} /><span>Detail</span></>}
        </div>
        <div className="topbar-right">
          <button className="workspace-search" aria-label="Search workspace" onClick={openSearch}><Search size={15} /><span>Search workspace</span><kbd>Ctrl K</kbd></button>
          <span className="topbar-divider" />
          <Link className="icon-link" href="/alerts" aria-label={`${count} open alerts`}><Bell />{count > 0 && <span className="notification-dot" />}</Link>
          <span className="avatar topbar-avatar" aria-label="VendorGuard">VG</span>
        </div>
      </header>
      <main className="page-content" id="main-content"><div key={pathname} className="page-enter">{children}</div></main>
      <footer className="app-footer">
        <span><span className="dot" /> OPERATIONAL WORKSPACE <span className="footer-separator">/</span> Human decisions. Clear evidence.</span>
        <span>VENDORGUARD <span className="footer-separator">/</span> V.01</span>
      </footer>
    </div>
    <dialog ref={dialog} className="command-dialog" aria-label="Search workspace" onClick={e => { if (e.target === e.currentTarget) dialog.current?.close(); }}>
      <div className="command-search"><Search size={20} /><input ref={searchInput} value={query} onChange={e => setQuery(e.target.value)} placeholder="Find a supplier, material, or page…" aria-label="Search workspace records" /><button onClick={() => dialog.current?.close()} aria-label="Close search"><X size={18} /></button></div>
      <div className="command-results">
        {!query && <><p className="command-label">QUICK NAVIGATION</p>{navigation.map(item => <button key={item.href} onClick={() => navigate(item.href)}><item.icon size={16} /><span>{item.label}</span><ArrowUpRight size={14} /></button>)}</>}
        <p className="command-label">SUPPLIERS {query && `· ${matches.length} MATCHES`}</p>
        {matches.map(s => <button key={s.id} onClick={() => navigate(`/suppliers/${s.id}`)}><Users size={16} /><span>{s.legal_name}<small>{s.materials_supplied.join(", ")}</small></span><ArrowUpRight size={14} /></button>)}
        {matches.length === 0 && <p className="command-empty">No matching suppliers. Try a material name.</p>}
      </div>
      <div className="command-footer"><span>Search your current workspace</span><span><kbd>esc</kbd> to close</span></div>
    </dialog>
  </>;
}

