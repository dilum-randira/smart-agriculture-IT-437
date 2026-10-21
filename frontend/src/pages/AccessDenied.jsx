import { Link } from "react-router-dom";
export default function AccessDenied() {
  return <main className="auth-session"><p>Access restricted</p><h1>This section is not available to your role.</h1><p>Contact an administrator if you need additional access. Your assigned farm information and saved forecasts remain available.</p><Link to="/">Return to overview</Link><Link to="/predictions/microclimate">Open assigned farms</Link></main>;
}
