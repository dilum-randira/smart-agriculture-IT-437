const paths = {
  leaf: <><path d="M20 4C9 2 3 8 5 15s14 7 15-11Z" /><path d="M4 21 15 10M9 16v-5m0 5h5" /></>,
  arrow: <><path d="M4 12h16m-6-6 6 6-6 6" /></>,
  chart: <><path d="M4 4v16h17M9 15v-4m5 4V7m5 8v-5" /></>,
  flask: <><path d="M9 3h6m-5 0v7L4 19a1 1 0 0 0 1 2h14a1 1 0 0 0 1-2l-6-9V3M8 15h8" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v6m0-10v1" /></>,
  reset: <><path d="M4 10a8 8 0 1 1 1 8M4 4v6h6" /></>,
  check: <><path d="m5 12 4 4L19 6" /></>,
};

export default function YieldIcon({ name = "leaf", ...props }) {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.leaf}</svg>;
}
