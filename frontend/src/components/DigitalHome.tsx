import type { Evidence, HouseholdOverview, VerificationResult } from "../types/api";
import "./DigitalHome.css";

const n = (value: string | number, digits = 0) => Number(value).toLocaleString("en-IN", { maximumFractionDigits: digits });

function DeviceGlyph({ device }: { device: string }) {
  if (device === "light") return <svg viewBox="0 0 64 64" aria-hidden="true"><path d="M32 10v10M20 32a12 12 0 1 1 24 0c0 5-3 8-5 11h-14c-2-3-5-6-5-11Z"/><rect x="25" y="47" width="14" height="7" rx="3"/><line x1="28" y1="58" x2="36" y2="58"/></svg>;
  if (device === "fan") return <svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="6"/><path d="M32 26c0-10 6-16 12-16s4 8-2 14c-3 3-7 2-10 2ZM38 32c10 0 16 6 16 12s-8 4-14-2c-3-3-2-7-2-10ZM32 38c0 10-6 16-12 16s-4-8 2-14c3-3 7-2 10-2ZM26 32c-10 0-16-6-16-12s8-4 14 2c3 3 2 7 2 10Z"/></svg>;
  if (device === "heater") return <svg viewBox="0 0 64 64" aria-hidden="true"><rect x="12" y="13" width="40" height="40" rx="8"/><path d="M22 22v22M32 22v22M42 22v22M18 53v4M46 53v4"/></svg>;
  if (device === "ac") return <svg viewBox="0 0 64 64" aria-hidden="true"><rect x="9" y="15" width="46" height="25" rx="7"/><path d="M18 28h28M21 46c4-4 8-4 12 0M36 46c3-3 6-3 9 0"/></svg>;
  if (device === "tv") return <svg viewBox="0 0 64 64" aria-hidden="true"><rect x="9" y="13" width="46" height="33" rx="5"/><path d="M25 53h14M32 46v7"/></svg>;
  if (device === "refrigerator") return <svg viewBox="0 0 64 64" aria-hidden="true"><rect x="18" y="7" width="28" height="50" rx="5"/><path d="M18 28h28M39 17v6M39 36v7"/></svg>;
  return <svg viewBox="0 0 64 64" aria-hidden="true"><rect x="13" y="10" width="38" height="46" rx="7"/><circle cx="32" cy="34" r="12"/><path d="M20 18h3M28 18h16"/></svg>;
}

function HomeInterior({
  acHighlighted,
  lightOn,
  fanOn,
  tvOn,
  acOn,
  dishwasherOn,
}: {
  acHighlighted: boolean;
  lightOn: boolean;
  fanOn: boolean;
  tvOn: boolean;
  acOn: boolean;
  dishwasherOn: boolean;
}) {
  return <svg className="home-interior" viewBox="0 0 1000 560" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
    <defs>
      <linearGradient id="living-wall" x1="0" y1="0" x2="0.3" y2="1">
        <stop offset="0%" stopColor={lightOn ? "#7c6054" : "#55423b"}/>
        <stop offset="60%" stopColor={lightOn ? "#604b46" : "#3e3232"}/>
        <stop offset="100%" stopColor={lightOn ? "#443439" : "#282024"}/>
      </linearGradient>
      <linearGradient id="kitchen-wall" x1="0" y1="0" x2="0.3" y2="1">
        <stop offset="0%" stopColor="#785944"/>
        <stop offset="60%" stopColor="#5a4234"/>
        <stop offset="100%" stopColor="#423126"/>
      </linearGradient>
      <linearGradient id="living-floor" x1="0" y1="0" x2="0.8" y2="1">
        <stop offset="0%" stopColor={lightOn ? "#936647" : "#6c4832"}/>
        <stop offset="45%" stopColor={lightOn ? "#7b5037" : "#553624"}/>
        <stop offset="100%" stopColor={lightOn ? "#553523" : "#382215"}/>
      </linearGradient>
      <linearGradient id="kitchen-floor-grad" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor="#58483f"/>
        <stop offset="100%" stopColor="#382d27"/>
      </linearGradient>
      <linearGradient id="sofa-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={lightOn ? "#cfc7c5" : "#bbb3b1"}/>
        <stop offset="60%" stopColor={lightOn ? "#9d959c" : "#8c858b"}/>
        <stop offset="100%" stopColor="#68636b"/>
      </linearGradient>
      <linearGradient id="sofa-cushion" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#7a7378"/>
        <stop offset="100%" stopColor="#565158"/>
      </linearGradient>
      <linearGradient id="fridge-steel" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor="#cfd7de"/>
        <stop offset="30%" stopColor="#edf1f5"/>
        <stop offset="70%" stopColor="#d5dde5"/>
        <stop offset="100%" stopColor="#b4c0cd"/>
      </linearGradient>
      <linearGradient id="fridge-door" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#e4ebf1"/>
        <stop offset="100%" stopColor="#c5d0dc"/>
      </linearGradient>
      <linearGradient id="dishwasher-steel" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor="#bac6d2"/>
        <stop offset="40%" stopColor="#e0e7ee"/>
        <stop offset="100%" stopColor="#9fb0c0"/>
      </linearGradient>
      <linearGradient id="ac-body" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#f5f8fa"/>
        <stop offset="70%" stopColor="#dde5ed"/>
        <stop offset="100%" stopColor="#c2d0dc"/>
      </linearGradient>
      <linearGradient id="window-sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#14263f"/>
        <stop offset="100%" stopColor="#254267"/>
      </linearGradient>
      <radialGradient id="lamp-glow" cx="0.25" cy="0.4" r="0.75">
        <stop offset="0%" stopColor="#ffb356" stopOpacity="0.38"/>
        <stop offset="45%" stopColor="#ff9a3c" stopOpacity="0.14"/>
        <stop offset="100%" stopColor="#ff9a3c" stopOpacity="0"/>
      </radialGradient>
      <radialGradient id="ceiling-light-radial" cx="0.5" cy="0.2" r="0.8">
        <stop offset="0%" stopColor="#fff3bf" stopOpacity="0.6"/>
        <stop offset="35%" stopColor="#ffc059" stopOpacity="0.28"/>
        <stop offset="70%" stopColor="#ff9a3c" stopOpacity="0.08"/>
        <stop offset="100%" stopColor="#ff9a3c" stopOpacity="0"/>
      </radialGradient>
      <radialGradient id="kitchen-glow" cx="0.5" cy="0.3" r="0.7">
        <stop offset="0%" stopColor="#ffd88a" stopOpacity="0.28"/>
        <stop offset="55%" stopColor="#ffb856" stopOpacity="0.10"/>
        <stop offset="100%" stopColor="#ffb856" stopOpacity="0"/>
      </radialGradient>
      <filter id="ground-shadow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="8"/>
      </filter>
      <filter id="soft-shadow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="14"/>
      </filter>
      <filter id="pulse-glow" x="-40%" y="-40%" width="180%" height="180%">
        <feGaussianBlur stdDeviation="3"/>
      </filter>
      <filter id="tv-ambient-glow" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="12"/>
      </filter>
    </defs>

    {/* Architectural walls */}
    <path className="house-back living-back" d="M20 120 120 50h525v355L470 535H20Z" fill="url(#living-wall)"/>
    <path className="house-back kitchen-back" d="M645 105 730 58h250v410l-165 67H645Z" fill="url(#kitchen-wall)"/>

    {/* Wall baseboard mouldings */}
    <path className="baseboard living-baseboard" d="M20 405h625" stroke="#2a1f19" strokeWidth="8" strokeLinecap="round"/>
    <path className="baseboard living-baseboard-highlight" d="M20 402h625" stroke="#48362b" strokeWidth="2" strokeLinecap="round"/>
    <path className="baseboard kitchen-baseboard" d="M645 405h335" stroke="#251d18" strokeWidth="8" strokeLinecap="round"/>

    {/* Environmental Ambient Lighting */}
    <ellipse cx="110" cy="310" rx="150" ry="110" fill="url(#lamp-glow)" filter="url(#soft-shadow)"/>
    <ellipse cx="800" cy="270" rx="160" ry="100" fill="url(#kitchen-glow)" filter="url(#soft-shadow)"/>

    {/* Living room ceiling light illumination cone when turned ON */}
    {lightOn && <g className="ceiling-light-wash">
      <ellipse cx="240" cy="115" rx="220" ry="140" fill="url(#ceiling-light-radial)" filter="url(#soft-shadow)"/>
      <polygon points="240,95 30,420 520,420" fill="url(#ceiling-light-radial)" opacity="0.35"/>
    </g>}

    {/* Floors */}
    <path className="floor living-floor" d="M20 405h625L470 535H20Z" fill="url(#living-floor)"/>
    <g className="floor-planks" opacity={lightOn ? 0.22 : 0.16}>
      <path d="M120 405 L70 535 M220 405 L160 535 M320 405 L250 535 M420 405 L340 535 M520 405 L420 535" stroke="#1f140e" strokeWidth="1.5"/>
    </g>
    <path className="floor kitchen-floor" d="M645 405h335l-165 130H470Z" fill="url(#kitchen-floor-grad)"/>
    <g className="tile-seams" opacity="0.14">
      <path d="M720 405 L590 535 M800 405 L690 535 M880 405 L790 535" stroke="#1f1713" strokeWidth="1.5"/>
      <path d="M570 445 L890 445 M520 490 L810 490" stroke="#1f1713" strokeWidth="1.5"/>
    </g>

    {/* Architectural divider with 3D thickness */}
    <path className="divider-shadow" d="M637 105v300L462 535" stroke="#1d2836" strokeWidth="10" strokeLinecap="round"/>
    <path className="divider-front" d="M645 105v300L470 535" stroke="#324962" strokeWidth="7" strokeLinecap="round"/>
    <path className="ceiling-line" d="M20 120 120 50h525l85 8 250 0" stroke="#364e6b" strokeWidth="8" strokeLinecap="round" fill="none"/>

    {/* Window with dusk sky and curtains */}
    <g className="living-window">
      <rect x="470" y="105" width="125" height="126" rx="4" fill="url(#window-sky)" stroke="#a37955" strokeWidth="6"/>
      <path d="M532 105v126M470 168h125" stroke="#75563c" strokeWidth="3"/>
      <path d="M454 96q26 54 3 145" stroke="#8d6554" strokeWidth="14" strokeLinecap="round" fill="none" opacity="0.8"/>
      <path d="M609 96q-25 59-2 145" stroke="#8d6554" strokeWidth="14" strokeLinecap="round" fill="none" opacity="0.8"/>
    </g>

    {/* Physical Living Room Ceiling Light Fixture */}
    <g className="living-ceiling-light">
      <line x1="240" y1="50" x2="240" y2="82" stroke="#261c16" strokeWidth="2.5"/>
      <path d="M224 95 L256 95 L250 82 L230 82 Z" fill="#201a16" stroke="#b08d66" strokeWidth="1.5"/>
      <ellipse cx="240" cy="95" rx="16" ry="5" fill={lightOn ? "#ffe680" : "#322720"} stroke="#826649" strokeWidth="1"/>
      <circle cx="240" cy="97" r={lightOn ? 5.5 : 3.5} fill={lightOn ? "#fffdf0" : "#443428"} filter={lightOn ? "url(#pulse-glow)" : undefined}/>
    </g>

    {/* Physical Living Room Ceiling Fan */}
    <g className="living-ceiling-fan">
      <line x1="380" y1="50" x2="380" y2="74" stroke="#261c16" strokeWidth="3"/>
      <ellipse cx="380" cy="74" rx="12" ry="5" fill="#1b1511" stroke="#483930" strokeWidth="1"/>
      <circle cx="380" cy="77" r="8" fill="#292019" stroke="#544133" strokeWidth="1"/>
      {/* Fan Blades Group */}
      <g className={`ceiling-fan-blades ${fanOn ? "spinning" : ""}`} style={{ transformOrigin: "380px 77px" }}>
        <path d="M380 77 C410 72 448 77 455 81 C448 85 410 82 380 77 Z" fill="#4d3a2c" stroke="#261a12" strokeWidth="1"/>
        <path d="M380 77 C350 72 312 77 305 81 C312 85 350 82 380 77 Z" fill="#4d3a2c" stroke="#261a12" strokeWidth="1"/>
        <path d="M380 77 C384 52 381 22 380 16 C379 22 376 52 380 77 Z" fill="#423023" stroke="#261a12" strokeWidth="1"/>
        <path d="M380 77 C384 102 381 132 380 138 C379 132 376 102 380 77 Z" fill="#584332" stroke="#261a12" strokeWidth="1"/>
        <circle cx="380" cy="77" r="4.5" fill="#cf9d63"/>
      </g>
      {/* Airflow ripples below fan when ON */}
      {fanOn && <g className="fan-breeze">
        <path d="M345 106 Q380 120 415 106" stroke="#5bc0eb" strokeWidth="1.5" strokeDasharray="4 4" fill="none" opacity="0.8"/>
        <path d="M335 125 Q380 142 425 125" stroke="#5bc0eb" strokeWidth="1.5" strokeDasharray="4 4" fill="none" opacity="0.7"/>
      </g>}
    </g>

    {/* Grounding shadows for living room furniture */}
    <polygon points="80,396 260,396 242,414 70,414" fill="#0c0704" opacity="0.45" filter="url(#ground-shadow)"/>
    <ellipse cx="395" cy="442" rx="150" ry="18" fill="#0c0704" opacity="0.48" filter="url(#ground-shadow)"/>
    <ellipse cx="310" cy="486" rx="85" ry="16" fill="#0c0704" opacity="0.42" filter="url(#ground-shadow)"/>
    <ellipse cx="465" cy="468" rx="60" ry="14" fill="#0c0704" opacity="0.46" filter="url(#ground-shadow)"/>

    {/* Left wall: Smart Electrical Breaker Panel (Home Energy Monitoring Point) */}
    <g className="electrical-panel-unit">
      <rect x="34" y="305" width="40" height="78" rx="6" fill="#182739" stroke="#2c4460" strokeWidth="2.5"/>
      <rect x="39" y="312" width="30" height="64" rx="4" fill="#0a1522"/>
      <rect x="42" y="316" width="24" height="28" rx="3" fill="#06101c" stroke="#1d3856" strokeWidth="1.5"/>
      <path d="M54 321 l-3 9 h5 l-2 9 6 -10 h-4 z" fill="#38bdf8" filter="url(#pulse-glow)"/>
      <circle cx="54" cy="354" r="2.5" fill="#38bdf8"/>
      <circle cx="60" cy="354" r="2.5" fill="#38bdf8"/>
      <rect x="52" y="383" width="5" height="23" fill="#24374d"/>
      <rect x="50" y="403" width="9" height="5" rx="2" fill="#314964"/>
    </g>

    {/* Living room wall-mounted Air Conditioner */}
    <g className={`wall-ac-unit ${acHighlighted ? "highlighted-ac" : ""}`}>
      <rect x="117" y="93" width="107" height="44" rx="7" fill="#070c12" opacity="0.32" filter="url(#ground-shadow)"/>
      <rect x="115" y="89" width="107" height="44" rx="7" fill="url(#ac-body)" stroke={acHighlighted ? "#ffd475" : "#c4d3e0"} strokeWidth={acHighlighted ? "2.5" : "1.5"}/>
      <rect x="119" y="92" width="99" height="25" rx="4" fill="#f4f8fb"/>
      <path d="M121 122 h95" stroke="#9bb1c4" strokeWidth="3" strokeLinecap="round"/>
      <path d="M123 127 h91" stroke="#b8c9d8" strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="210" cy="103" r="2.5" fill={acHighlighted ? "#f5b83d" : acOn ? "#38bdf8" : "#5a6e82"} filter={acHighlighted || acOn ? "url(#pulse-glow)" : undefined}/>
      <text x="127" y="105" fill="#8da3b8" fontSize="6" fontFamily="sans-serif" fontWeight="700">VOLTWISE CLIMATE</text>
      {/* Airflow waves when AC is ON */}
      {acOn && <g className="ac-airflow-lines">
        <path d="M135 133 C140 152 132 172 128 188" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 4" fill="none" opacity="0.7"/>
        <path d="M168 133 C173 156 166 178 162 195" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 4" fill="none" opacity="0.8"/>
        <path d="M201 133 C206 152 200 172 196 188" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 4" fill="none" opacity="0.7"/>
      </g>}
    </g>

    {/* Television and wooden media console */}
    <g className="tv-furniture">
      {/* Backlight glow when TV is ON */}
      {tvOn && <rect x="80" y="188" width="193" height="130" rx="8" fill="#1d4ed8" opacity="0.35" filter="url(#tv-ambient-glow)"/>}
      <rect x="88" y="196" width="177" height="114" rx="5" fill="#050e18" stroke={tvOn ? "#38bdf8" : "#16283d"} strokeWidth="5"/>
      {/* Screen Fill */}
      {tvOn ? (
        <g className="tv-screen-active">
          <rect x="91" y="199" width="171" height="108" rx="3" fill="#08182b"/>
          <path d="M91 270 Q130 230 176 260 T262 245 L262 307 L91 307 Z" fill="#1e3a5f" opacity="0.6"/>
          <path d="M91 285 Q140 255 190 280 T262 265 L262 307 L91 307 Z" fill="#0284c7" opacity="0.5"/>
          <circle cx="102" cy="209" r="2" fill="#38bdf8" filter="url(#pulse-glow)"/>
        </g>
      ) : (
        <polygon points="92,199 185,199 125,306 92,306" fill="#fff" opacity="0.03"/>
      )}
      {/* Console */}
      <path d="M103 330h148l18 67H85Z" fill="#583525"/>
      <path d="M85 330h184v6H85Z" fill="#724632"/>
      <path d="M107 350h137M174 330v67" stroke="rgba(235,210,185,.35)" strokeWidth="3"/>
      <rect x="135" y="342" width="14" height="3" rx="1" fill="#2d1c14"/>
      <rect x="202" y="342" width="14" height="3" rx="1" fill="#2d1c14"/>
    </g>

    {/* Sectional sofa */}
    <g className="sofa-furniture">
      <path d="M280 338q0-34 35-34h190q35 0 35 34v92H280Z" fill="url(#sofa-grad)"/>
      <rect x="254" y="345" width="54" height="102" rx="18" fill="url(#sofa-cushion)"/>
      <rect x="513" y="345" width="54" height="102" rx="18" fill="url(#sofa-cushion)"/>
      <path d="M317 318v105M407 310v113M502 318v105" stroke="rgba(35,37,44,.4)" strokeWidth="3"/>
      <path d="M275 447v18M545 447v18" stroke="rgba(235,210,185,.42)" strokeWidth="4"/>
    </g>

    {/* Coffee table */}
    <g className="table-furniture">
      <ellipse cx="310" cy="467" rx="89" ry="28" fill="#6d442c"/>
      <ellipse cx="310" cy="464" rx="85" ry="25" fill="#7f5035"/>
      <path d="M310 481v39M280 521h60" stroke="rgba(235,210,185,.42)" strokeWidth="4"/>
      <rect x="290" y="445" width="36" height="16" rx="6" fill="#254d3c"/>
      <ellipse cx="308" cy="445" rx="12" ry="6" fill="#356d56"/>
    </g>

    {/* Floor lamp */}
    <g className="lamp-furniture">
      <path d="M61 241h73l-15 48H76Z" fill="#e7c17d"/>
      <path d="M63 241h69l-3 4H66Z" fill="#fff" opacity="0.5"/>
      <path d="M97 289v91M72 382h50" stroke="rgba(235,210,185,.55)" strokeWidth="4"/>
    </g>

    {/* Grounding shadows for kitchen */}
    <rect x="650" y="396" width="74" height="14" rx="5" fill="#0a0604" opacity="0.48" filter="url(#ground-shadow)"/>
    <rect x="722" y="415" width="220" height="14" rx="5" fill="#0a0604" opacity="0.42" filter="url(#ground-shadow)"/>
    <ellipse cx="865" cy="486" rx="84" ry="18" fill="#0a0604" opacity="0.44" filter="url(#ground-shadow)"/>

    {/* Kitchen Refrigerator */}
    <g className="kitchen-refrigerator-unit">
      <rect x="652" y="145" width="70" height="252" rx="7" fill="url(#fridge-steel)" stroke="#8093a6" strokeWidth="2"/>
      <rect x="655" y="148" width="64" height="140" rx="5" fill="url(#fridge-door)" stroke="#9fb0c1" strokeWidth="1"/>
      <rect x="655" y="293" width="64" height="99" rx="5" fill="url(#fridge-door)" stroke="#9fb0c1" strokeWidth="1"/>
      <rect x="710" y="200" width="4" height="46" rx="2" fill="#506173"/>
      <rect x="710" y="306" width="4" height="34" rx="2" fill="#506173"/>
      <rect x="655" y="289" width="64" height="3" fill="#2d3b4a"/>
      <rect x="654" y="393" width="66" height="5" rx="1" fill="#222c36"/>
      <rect x="664" y="165" width="16" height="8" rx="2" fill="#0d1822"/>
      <circle cx="672" cy="169" r="1.5" fill="#38bdf8"/>
    </g>

    {/* Kitchen counters, backsplash, sink and integrated Dishwasher */}
    <g className="kitchen-counters">
      <path d="M725 270h209v151H725Z" fill="#53433c"/>
      <path d="M722 266h222v19H722Z" fill="#c8a477"/>
      <rect x="748" y="268" width="45" height="12" rx="2" fill="#3d322c"/>
      <path d="M765 266q0-27 24-27t24 27M785 241v-18" stroke="#ded0be" strokeWidth="5" fill="none" strokeLinecap="round"/>

      {/* Integrated Dishwasher in cabinetry */}
      <g className="kitchen-dishwasher-unit">
        <rect x="805" y="292" width="73" height="120" rx="4" fill="#1c2631" stroke={dishwasherOn ? "#38bdf8" : "#334557"} strokeWidth="1.5"/>
        <rect x="808" y="318" width="67" height="89" rx="3" fill="url(#dishwasher-steel)" stroke="#8193a5" strokeWidth="1"/>
        <rect x="808" y="295" width="67" height="20" rx="2" fill="#09121c"/>
        <circle cx="818" cy="305" r="2.5" fill="#38bdf8" filter="url(#pulse-glow)"/>
        <rect x="834" y="302" width="28" height="6" rx="1" fill={dishwasherOn ? "#0284c7" : "#152332"}/>
        <rect x="820" y="326" width="43" height="4" rx="2" fill="#4d5f72"/>
        <rect x="807" y="408" width="69" height="4" fill="#111820"/>
      </g>

      <path d="M725 285v136M800 285v136M883 285v136" stroke="rgba(235,210,185,.35)" strokeWidth="3"/>
      <path d="M740 328h15M900 328h15" stroke="rgba(235,210,185,.45)" strokeWidth="3"/>
      <path d="M732 120h58v100h-58M812 120h58v100h-58M892 120h43v100h-43" stroke="#9e8067" strokeWidth="6" fill="rgba(75,56,46,.55)"/>
      <path d="M780 180v20M860 180v20M925 180v20" stroke="#d5beab" strokeWidth="3"/>
    </g>

    {/* Dining furniture */}
    <g className="dining-furniture">
      <ellipse cx="865" cy="470" rx="80" ry="28" fill="#6d4a32"/>
      <ellipse cx="865" cy="467" rx="76" ry="25" fill="#7a5439"/>
      <path d="M865 484v43M830 528h70" stroke="rgba(235,210,185,.42)" strokeWidth="4"/>
      <path d="M785 456v69M945 456v69" stroke="rgba(235,210,185,.38)" strokeWidth="4"/>
    </g>

    {/* Indoor plants */}
    <g className="plants">
      <path d="M594 437h38l-5 62h-28Z" fill="#583325"/>
      <path d="M613 437q-38-50-2-72 14 34 2 72Zm2 0q35-58 56-20-19 23-56 20Zm-3-1q-7-64-39-43 5 33 39 43Z" fill="#2d553e"/>
    </g>
  </svg>;
}

type HomeState = "off" | "reported" | "verifying" | "no-draw" | "high-draw" | "recovering" | "verified" | "safety";

type Props = {
  overview: HouseholdOverview | null;
  evidence: Evidence | null;
  previousVerification: VerificationResult | null;
  busy: boolean;
  lastCommand: string | null;
  lightState?: "OFF" | "ON";
  fanState?: "OFF" | "ON";
  tvState?: "OFF" | "ON";
  acState?: "OFF" | "ON";
  dishwasherState?: "OFF" | "ON";
  activeDevice?: string | null;
  resultOverviewFresh?: boolean;
  verificationPresentationStage?: "command" | "evidence" | "diagnosis" | "final" | null;
  onDeviceCommand?: (command: string) => void;
};

export function DigitalHome({
  overview,
  evidence,
  previousVerification,
  busy,
  lastCommand,
  lightState = "OFF",
  fanState = "OFF",
  tvState = "OFF",
  acState = "OFF",
  dishwasherState = "OFF",
  activeDevice = null,
  resultOverviewFresh = false,
  verificationPresentationStage = null,
  onDeviceCommand = () => {},
}: Props) {
  const heater = overview?.devices.find((device) => device.device_id === "heater");
  const ac = overview?.devices.find((device) => device.device_id === "ac");
  const tv = overview?.devices.find((device) => device.device_id === "tv");
  const refrigerator = overview?.devices.find((device) => device.device_id === "refrigerator");
  const dishwasher = overview?.devices.find((device) => device.device_id === "dishwasher");

  const verification = evidence?.kind === "verification" ? evidence.data : null;
  const diagnostic = evidence?.kind === "diagnostic" ? evidence.data : null;
  const firstAttempt = diagnostic?.attempts[0];
  const lastAttempt = diagnostic?.attempts[diagnostic.attempts.length - 1];
  const topContributor = evidence?.kind === "usage" ? evidence.data.contributors[0] : null;

  const heaterRequest = lastCommand?.toLowerCase().includes("heater") ?? false;
  const diagnosisRequest = lastCommand?.toLowerCase().includes("diagnos") ?? false;
  const returnedHighDraw = diagnostic?.diagnostic_classification === "ABNORMAL_HIGH_DRAW" || firstAttempt?.diagnostic_classification === "ABNORMAL_HIGH_DRAW" || /high draw/i.test(verification?.reason ?? "");
  const directPowerCut = returnedHighDraw && /power was cut/i.test(verification?.reason ?? "");
  const presentingVerification = Boolean(verificationPresentationStage && verificationPresentationStage !== "final");

  const heaterState: HomeState = presentingVerification ? "verifying"
    : busy && heaterRequest && diagnosisRequest ? "recovering"
    : busy && heaterRequest ? "verifying"
    : diagnostic?.final_status === "SAFETY_STOP" || directPowerCut ? "safety"
    : diagnostic?.final_status === "RECOVERED" || diagnostic?.final_status === "VERIFIED" ? "verified"
    : diagnostic && returnedHighDraw ? "high-draw"
    : diagnostic ? "no-draw"
    : verification?.verification === "VERIFIED" ? "verified"
    : verification && returnedHighDraw ? "high-draw"
    : verification ? "no-draw"
    : heater?.reported_state === "ON" ? "reported"
    : "off";

  const reported = heaterState === "safety"
    ? resultOverviewFresh ? heater?.reported_state ?? "Unknown" : "Unknown"
    : lastAttempt?.reported_state ?? verification?.reported_state ?? heater?.reported_state ?? "OFF";
  const observed = lastAttempt?.observed_watts ?? verification?.observed_power_watts ?? heater?.current_watts;
  const expected = verification?.expected_power_watts ?? previousVerification?.expected_power_watts ?? heater?.electrical_profile?.expected_running_watts;
  const showingElectricalEvidence = Boolean(verification || diagnostic || (busy && heaterRequest));

  const heaterStatus = heaterState === "verifying" ? "Checking simulated telemetry"
    : heaterState === "recovering" ? "Diagnosing safely"
    : heaterState === "no-draw" ? "Electrical response not verified"
    : heaterState === "high-draw" ? "Abnormal high draw"
    : heaterState === "verified" ? "Electrical response verified"
    : heaterState === "safety" ? "Safety stop · power cut"
    : heaterState === "reported" ? "Reported on"
    : "Ready to verify";

  const acHighlighted = topContributor?.device_id === "ac" || activeDevice === "ac";
  const lightOn = lightState === "ON";
  const fanOn = fanState === "ON";
  const tvOn = (tv?.reported_state === "ON" || tvState === "ON");
  const acOn = (ac?.reported_state === "ON" || acState === "ON");
  const dishwasherOn = (dishwasher?.reported_state === "ON" || dishwasherState === "ON");

  const hasElectricalResult = Boolean(verification || diagnostic);
  const presentationHasEvidence = verificationPresentationStage === "evidence" || verificationPresentationStage === "diagnosis";
  const presentationHasDiagnosis = verificationPresentationStage === "diagnosis";
  const observeStage = heaterState === "safety" ? "danger"
    : presentingVerification ? presentationHasEvidence ? "done" : "current"
    : busy && heaterRequest && !diagnosisRequest ? "current" : showingElectricalEvidence ? "done" : "inactive";
  const reasonStage = heaterState === "safety" ? "danger"
    : presentingVerification ? presentationHasDiagnosis ? "current" : "inactive"
    : busy && diagnosisRequest ? "current" : hasElectricalResult ? "done" : "inactive";
  const actStage = heaterState === "safety" ? "safety"
    : presentingVerification ? "inactive"
    : busy && diagnosisRequest ? "current"
    : diagnostic ? diagnostic.retries_used > 0 ? "done" : "skipped"
    : verification ? verification.verification === "VERIFIED" ? "skipped" : "current"
    : "inactive";
  const verifyStage = heaterState === "verified" ? "verified"
    : heaterState === "safety" ? "skipped"
    : presentingVerification ? "inactive"
    : hasElectricalResult ? "failed"
    : "inactive";
  const reasonValue = presentingVerification && !presentationHasDiagnosis ? null
    : heaterState === "safety" || returnedHighDraw ? "High draw"
    : heaterState === "verified" ? "Normal"
    : hasElectricalResult ? "No draw"
    : null;
  const actValue = heaterState === "safety" ? "Power cut"
    : diagnostic?.retries_used ? `${diagnostic.retries_used} retry`
    : busy && diagnosisRequest ? "Checking"
    : null;

  return <section className={`digital-home home-${heaterState} ${showingElectricalEvidence || busy && heaterRequest ? "investigating-heater" : ""}`} aria-label="VoltWise digital home">
    <header className="home-header">
      <div>
        <p>VoltWise Digital Home</p>
        <h2>A device can report ON. VoltWise verifies the electrical response.</h2>
      </div>
      {evidence?.kind === "energy" ? <div className="home-energy" aria-label="Home cycle energy">
          <span>This period</span>
          <strong>{n(evidence.data.current_kwh)} kWh</strong>
          <small>Previous {n(evidence.data.previous_equivalent_kwh)} · projected {n(evidence.data.projection.projected_kwh, 2)} kWh</small>
        </div>
        : overview && <div className="home-energy quiet">
          <span>Home energy · this cycle</span>
          <strong>{n(overview.current_cycle_kwh)} kWh</strong>
          <small>Smart-home telemetry simulated</small>
        </div>}
    </header>

    <div className="home-stage">
      <div className="home-scene-wrapper">
        <HomeInterior
          acHighlighted={acHighlighted}
          lightOn={lightOn}
          fanOn={fanOn}
          tvOn={tvOn}
          acOn={acOn}
          dishwasherOn={dishwasherOn}
        />

        <span className="room-label living-label">Living room</span>
        <span className="room-label kitchen-label">Kitchen</span>

        {/* Living Room Ceiling Light Badge */}
        <button
          type="button"
          className={`scene-device light-scene ${lightOn ? "on" : "off"} ${activeDevice === "light" ? "active-device" : ""}`}
          onClick={() => onDeviceCommand(lightOn ? "Turn off the light" : "Turn on the light")}
          aria-label={`Living Room Light, ${lightOn ? "ON" : "OFF"}`}
        >
          <DeviceGlyph device="light"/>
          <div>
            <strong>Living Room Light</strong>
            <span>{lightOn ? "ON ✓" : "OFF"}</span>
            {lightOn && <small className="confirmed-pill">State confirmed</small>}
          </div>
        </button>

        {/* Ceiling Fan Badge */}
        <button
          type="button"
          className={`scene-device fan-scene ${fanOn ? "on" : "off"} ${activeDevice === "fan" ? "active-device" : ""}`}
          onClick={() => onDeviceCommand(fanOn ? "Turn off the fan" : "Turn on the fan")}
          aria-label={`Ceiling Fan, ${fanOn ? "ON" : "OFF"}`}
        >
          <DeviceGlyph device="fan"/>
          <div>
            <strong>Ceiling Fan</strong>
            <span>{fanOn ? "ON ✓" : "OFF"}</span>
            {fanOn && <small className="confirmed-pill">Running</small>}
          </div>
        </button>

        {/* Wall-mounted Air Conditioner */}
        {ac && <button
          type="button"
          className={`scene-device ac-scene ${acHighlighted ? "highlighted" : acOn ? "on" : "off"} ${activeDevice === "ac" ? "active-device" : ""}`}
          onClick={() => !acHighlighted && onDeviceCommand(acOn ? "Turn off the AC" : "Turn on the AC")}
          aria-label={`${ac.name}${acHighlighted ? ", largest identified contributor" : acOn ? ", ON" : ", OFF"}`}
        >
          <DeviceGlyph device="ac"/>
          <div>
            <strong>{ac.name}</strong>
            <span>{acHighlighted ? "Largest identified contributor" : (acOn ? "ON ✓" : "OFF")}</span>
            {!acHighlighted && acOn && <small className="confirmed-pill">State confirmed</small>}
            {acHighlighted && topContributor && <small>+{n(topContributor.runtime_change_hours)} h · {n(topContributor.energy_impact_kwh, 2)} kWh {topContributor.energy_impact_type.toLowerCase()}</small>}
          </div>
        </button>}

        {/* Television on console */}
        {tv && <button
          type="button"
          className={`scene-device tv-scene ${tvOn ? "on" : "off"} ${activeDevice === "tv" ? "active-device" : ""}`}
          onClick={() => onDeviceCommand(tvOn ? "Turn off the TV" : "Turn on the TV")}
          aria-label={`${tv.name}, ${tvOn ? "ON" : "OFF"}`}
        >
          <DeviceGlyph device="tv"/>
          <div>
            <strong>{tv.name}</strong>
            <span>{tvOn ? "ON ✓" : "OFF"}</span>
            {tvOn && <small className="confirmed-pill">State confirmed</small>}
          </div>
        </button>}

        {/* Refrigerator inside the kitchen */}
        {refrigerator && <article className="scene-device fridge-scene" aria-label={refrigerator.name}>
          <DeviceGlyph device="refrigerator"/>
          <div>
            <strong>{refrigerator.name}</strong>
            <span>{refrigerator.reported_state || "ON"}</span>
          </div>
        </article>}

        {/* Dishwasher inside the kitchen cabinetry */}
        {dishwasher && <button
          type="button"
          className={`scene-device dishwasher-scene ${dishwasherOn ? "on" : "off"} ${activeDevice === "dishwasher" ? "active-device" : ""}`}
          onClick={() => onDeviceCommand(dishwasherOn ? "Turn off the dishwasher" : "Turn on the dishwasher")}
          aria-label={`${dishwasher.name}, ${dishwasherOn ? "ON" : "OFF"}`}
        >
          <DeviceGlyph device="dishwasher"/>
          <div>
            <strong>{dishwasher.name}</strong>
            <span>{dishwasherOn ? "ON ✓" : "OFF"}</span>
            {dishwasherOn && <small className="confirmed-pill">Running</small>}
          </div>
        </button>}

        {/* VoltWise Electrical Observation Path */}
        {showingElectricalEvidence && <svg className="observation-path" viewBox="0 0 1000 560" preserveAspectRatio="none" aria-hidden="true">
          <path d="M54 385 L54 440 Q62 470 100 478 L240 488 Q300 492 360 480 L455 450"/>
          <circle cx="54" cy="385" r="5"/>
          <circle cx="260" cy="489" r="6"/>
          <circle cx="455" cy="450" r="7"/>
        </svg>}

        {showingElectricalEvidence && <div className="monitor-label">
          <i/>
          <span><strong>VoltWise</strong>Monitoring simulated electrical telemetry…</span>
        </div>}

        {/* Physical Space Heater */}
        {heater && <div className={`physical-heater ${heaterState}`} aria-hidden="true">
          <div className="heat-waves"><i/><i/><i/></div>
          <div className="radiator">
            <i/><i/><i/><i/><i/><span/>
          </div>
          <span className="heater-led"/>
        </div>}

        {/* Contextual Overlay Anchored Directly Above the Heater when verifying/active */}
        {heater && (showingElectricalEvidence || heaterState !== "off") ? (
          <article className={`heater-readout ${heaterState}`} aria-label={`Living Room Heater, ${heaterState === "safety" ? "final simulated state" : "reported"} ${reported}, ${heaterStatus}`}>
            <header>
              <DeviceGlyph device="heater"/>
              <div>
                <strong>{heater.name}</strong>
                <span className="reported-line"><small>{heaterState === "safety" ? "Final simulated state" : "Device report"}</small><b>{reported}</b></span>
              </div>
            </header>
            {showingElectricalEvidence && <dl>
              <div>
                <dt>Expected</dt>
                <dd>{expected != null ? `≈${n(expected)} W` : "Unavailable"}</dd>
              </div>
              <div>
                <dt>{heaterState === "safety" ? "Before cutoff" : "Observed"}</dt>
                <dd>{observed != null ? `${observed >= 1000 ? "≈" : ""}${n(observed)} W` : "Checking…"}</dd>
              </div>
              {heaterState === "safety" && heater.electrical_profile && <div>
                <dt>Safe max</dt>
                <dd>≈{n(heater.electrical_profile.abnormal_high_draw_threshold)} W</dd>
              </div>}
            </dl>}
            <p>
              <b aria-hidden="true">{heaterState === "verified" ? "✓" : heaterState === "off" || heaterState === "reported" ? "○" : "!"}</b>
              <span><small>Electrical response</small><strong>{heaterStatus}</strong></span>
            </p>
          </article>
        ) : heater ? (
          /* Quiet idle heater badge when off and inactive */
          <button
            type="button"
            className="scene-device heater-scene off"
            onClick={() => onDeviceCommand("Turn on the heater")}
            aria-label="Living Room Heater, reported OFF, Ready to verify"
          >
            <DeviceGlyph device="heater"/>
            <div>
              <strong>{heater.name}</strong>
              <span>OFF · select to verify</span>
            </div>
          </button>
        ) : null}

        {/* VoltWise 4-Step Verification Progression in Scene */}
        <div className="home-loop" aria-label="VoltWise verification loop">
          <div className={`loop-step ${observeStage}`}>
            <span className="step-num">1</span>
            <span className="step-name">Observe</span>
            {observed != null && showingElectricalEvidence && <small className="step-val">{observed >= 1000 ? "≈" : ""}{n(observed)} W</small>}
          </div>
          <i className="loop-arrow" aria-hidden="true">→</i>
          <div className={`loop-step ${reasonStage}`}>
            <span className="step-num">2</span>
            <span className="step-name">Reason</span>
            {reasonValue && <small className="step-val">{reasonValue}</small>}
          </div>
          <i className="loop-arrow" aria-hidden="true">→</i>
          <div className={`loop-step ${actStage}`}>
            <span className="step-num">3</span>
            <span className="step-name">Act safely</span>
            {actValue && <small className="step-val">{actValue}</small>}
          </div>
          <i className="loop-arrow" aria-hidden="true">→</i>
          <div className={`loop-step ${verifyStage}`}>
            <span className="step-num">4</span>
            <span className="step-name">Verify</span>
            {heaterState === "verified" && <small className="step-val">Verified ✓</small>}
            {verifyStage === "failed" && <small className="step-val">Not verified</small>}
            {verifyStage === "skipped" && <small className="step-val">Stopped</small>}
          </div>
        </div>
      </div>
    </div>
  </section>;
}
