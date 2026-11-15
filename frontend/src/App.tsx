import { useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowRight, Calendar, Check, ChevronDown, CircleHelp, Clock3,
  Compass, Crosshair, Download, Globe2, Layers3, MapPin, Moon, Play,
  Radio, RefreshCw, Search, Settings2, ShieldCheck, Sun, Target, Zap
} from "lucide-react";
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
type Site = { id:string; name:string; lat:number; lon:number; description:string; science_value:string; terrain_available:boolean };
type Series = { t:string[]; sun_az:number[]; sun_el:number[]; earth_az:number[]; earth_el:number[] };
type Metrics = { illumination_pct:number; comm_pct:number; overlap_pct:number; longest_dark_hours:number; longest_comm_outage_hours:number; sun_elevation_max_deg:number; sun_elevation_mean_deg:number; time_to_sunset_hours:number|null; time_to_earthset_hours:number|null };
type Analysis = { site:Site; timeseries:Series; metrics:Metrics; score:{power:number;communication:number;survivability:number;total:number}; terrain_source:string; data_source:string; data_quality:string; warnings:string[]; sun_intervals:{start:string;end:string}[]; earth_intervals:{start:string;end:string}[]; dark_intervals:{start:string;end:string}[] };
type CompareResult = { scenarios:{label:string;analysis:Analysis}[]; summary:string };
const dateNow = () => new Date().toISOString().slice(0,16);
const num = (n:number|null|undefined, digits=1) => n == null || !Number.isFinite(n) ? "—" : n.toFixed(digits);
const duration = (n:number|null) => n == null ? "—" : `${n.toFixed(1)}h`;
const utcLabel = (s:string) => new Date(s).toLocaleString("en-GB",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"UTC"})+" UTC";
function App(){
  const [sites,setSites]=useState<Site[]>([]);
  const [siteId,setSiteId]=useState("shackleton-rim");
  const [date,setDate]=useState(dateNow());
  const [days,setDays]=useState(14);
  const [step,setStep]=useState(60);
  const [analysis,setAnalysis]=useState<Analysis|null>(null);
  const [sample,setSample]=useState(0);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [tab,setTab]=useState<"overview"|"compare">("overview");
  const [compareId,setCompareId]=useState("malapert-massif");
  const [comparison,setComparison]=useState<CompareResult|null>(null);
  const [apiState,setApiState]=useState<"checking"|"online"|"offline">("checking");
  const [custom,setCustom]=useState(false);
  const [lat,setLat]=useState("-89.90");
  const [lon,setLon]=useState("0.00");

  useEffect(()=>{ fetch(`${API}/api/v1/presets`).then(r=>{if(!r.ok)throw new Error();return r.json()}).then((v:Site[])=>{setSites(v);setApiState("online")}).catch(()=>setApiState("offline")); },[]);
  const selected=sites.find(s=>s.id===siteId);
  const count=analysis?.timeseries.t.length||0;
  const current=analysis&&count?{
    time:analysis.timeseries.t[sample]||analysis.timeseries.t[0],
    sunAz:analysis.timeseries.sun_az[sample]||0,sunEl:analysis.timeseries.sun_el[sample]||0,
    earthAz:analysis.timeseries.earth_az[sample]||0,earthEl:analysis.timeseries.earth_el[sample]||0
  }:null;
  const chartData=useMemo(()=>analysis?.timeseries.t.map((t,i)=>({time:t,sun:analysis.timeseries.sun_el[i],earth:analysis.timeseries.earth_el[i]}))||[],[analysis]);
  const activeSite=analysis?.site||selected;
  async function runAnalysis(){
    setBusy(true);setError("");setComparison(null);
    try{
      const body:any={start_utc:new Date(`${date}:00Z`).toISOString(),duration_days:days,step_minutes:step};
      if(custom){body.lat=Number(lat);body.lon=Number(lon)}else body.site_id=siteId;
      const r=await fetch(`${API}/api/v1/analyze-site`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
      const payload=await r.json();if(!r.ok)throw new Error(payload.detail?.detail||payload.detail||"Analysis request failed");
      setAnalysis(payload);setSample(0);setApiState("online");
    }catch(e){setError(e instanceof Error?e.message:"Could not complete analysis");setApiState("offline")}
    finally{setBusy(false)}
  }
  async function runCompare(){
    if(!analysis){await runAnalysis();return}
    setBusy(true);setError("");
    try{
      const base:any={start_utc:new Date(`${date}:00Z`).toISOString(),duration_days:days,step_minutes:step};
      const scenarios=[{...base,site_id:analysis.site.id==="custom"?undefined:analysis.site.id,...(analysis.site.id==="custom"?{lat:analysis.site.lat,lon:analysis.site.lon}:{})},{...base,site_id:compareId}];
      const r=await fetch(`${API}/api/v1/compare`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scenarios})});
      const p=await r.json();if(!r.ok)throw new Error(p.detail?.detail||"Comparison failed");setComparison(p);setTab("compare");
    }catch(e){setError(e instanceof Error?e.message:"Could not compare sites")}
    finally{setBusy(false)}
  }
  function exportCsv(){
    if(!analysis)return;
    const rows=["timestamp,sun_azimuth_deg,sun_elevation_deg,earth_azimuth_deg,earth_elevation_deg",...analysis.timeseries.t.map((t,i)=>[t,analysis.timeseries.sun_az[i],analysis.timeseries.sun_el[i],analysis.timeseries.earth_az[i],analysis.timeseries.earth_el[i]].join(","))];
    const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([rows.join("\n")],{type:"text/csv"}));a.download=`lunar-${analysis.site.id}-ephemeris.csv`;a.click();URL.revokeObjectURL(a.href);
  }
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Moon size={21}/><span/></div><div><b>LUNAR</b><small>LANDING NAVIGATOR</small></div></div>
      <div className="side-label">WORKSPACE</div>
      <button className={`nav-item ${tab==="overview"?"active":""}`} onClick={()=>setTab("overview")}><Compass size={17}/> Mission overview <span className="nav-dot"/></button>
      <button className={`nav-item ${tab==="compare"?"active":""}`} onClick={()=>setTab("compare")}><Layers3 size={17}/> Site comparison</button>
      <div className="side-divider"/>
      <div className="side-label">REFERENCE</div>
      <a className="nav-item" href="https://ssd.jpl.nasa.gov/horizons/" target="_blank" rel="noreferrer"><Globe2 size={17}/> JPL Horizons <ArrowRight size={13}/></a>
      <a className="nav-item" href="https://trek.nasa.gov/moon/" target="_blank" rel="noreferrer"><Target size={17}/> NASA Moon Trek <ArrowRight size={13}/></a>
      <div className="sidebar-bottom"><div className="orbit-art"><div className="orbit-ring"/><div className="orbit-moon"/></div><div className="side-note"><b>MISSION CONTROL</b><span>South pole operations</span></div><div className={`connection ${apiState}`}><i/>{apiState==="online"?"API connected":apiState==="offline"?"API unavailable":"Checking API"}</div></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="crumb">MISSION PLANNING <span>/</span> <b>{tab==="overview"?"SITE ANALYSIS":"SCENARIO COMPARISON"}</b></div><div className="top-actions"><span className="live-indicator"><i/> SYSTEM STATUS</span><button className="icon-button" title="Refresh analysis" onClick={runAnalysis}><RefreshCw size={17}/></button><div className="avatar">cTw</div></div></header>
      <div className="content">
        <section className="page-heading"><div><div className="overline"><span className="overline-line"/> LUNAR SOUTH POLE · DECISION SUPPORT</div><h1>Find your <em>landing window.</em></h1><p>Explore local illumination and Earth visibility to evaluate candidate landing sites.</p></div></section>
        <section className="control-panel">
          <div className="control-heading"><div><span className="step-number">01</span><b>MISSION PARAMETERS</b></div><span className="muted">Configure your scenario</span></div>
          <div className="control-grid">
            <label className="control-field site-field"><span>LANDING SITE</span><div className="input-shell"><MapPin size={17}/><select value={custom?"custom":siteId} onChange={e=>{if(e.target.value==="custom"){setCustom(true)}else{setCustom(false);setSiteId(e.target.value)}}}><optgroup label="Curated locations">{sites.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</optgroup><option value="custom">Custom coordinates…</option></select><ChevronDown size={15}/></div></label>
            {custom?<><label className="control-field"><span>LATITUDE · °</span><input value={lat} onChange={e=>setLat(e.target.value)} type="number" min="-90" max="90" step="0.01"/></label><label className="control-field"><span>LONGITUDE · °</span><input value={lon} onChange={e=>setLon(e.target.value)} type="number" min="-180" max="180" step="0.01"/></label></>:<div className="coordinates"><span>COORDINATES</span><b>{selected?`${selected.lat.toFixed(3)}° / ${selected.lon.toFixed(3)}°`:"Loading sites…"}</b><small>{selected?.science_value||"Choose a candidate location"}</small></div>}
            <label className="control-field"><span>START DATE · UTC</span><div className="input-shell"><Calendar size={16}/><input type="datetime-local" value={date} onChange={e=>setDate(e.target.value)}/></div></label>
            <label className="control-field compact"><span>DURATION</span><div className="input-shell"><input type="number" min="1" max="90" value={days} onChange={e=>setDays(Math.max(1,Math.min(90,Number(e.target.value))))}/><small>DAYS</small></div></label>
            <label className="control-field compact"><span>TIME STEP</span><div className="input-shell"><select value={step} onChange={e=>setStep(Number(e.target.value))}><option value={30}>30 min</option><option value={60}>1 hour</option><option value={120}>2 hours</option><option value={360}>6 hours</option></select><ChevronDown size={14}/></div></label>
            <button className="analyze-button" onClick={runAnalysis} disabled={busy||!date}><span>{busy?<RefreshCw className="spin" size={17}/>:<Play size={16} fill="currentColor"/>}</span>{busy?"ANALYZING":"RUN ANALYSIS"}<ArrowRight size={16}/></button>
          </div>
        </section>
        {error&&<div className="error-banner"><CircleHelp size={17}/>{error}<button onClick={()=>setError("")}>Dismiss</button></div>}
        {!analysis?<section className="welcome-state"><div className="welcome-graphic"><div className="planet"/><div className="planet-shadow"/><div className="signal signal-a"/><div className="signal signal-b"/></div><div className="welcome-copy"><span className="overline">READY FOR ANALYSIS</span><h2>Your next mission starts with the right light.</h2><p>Select a candidate site and mission date, then run an analysis to see solar power opportunity, direct-to-Earth communication windows and operational constraints.</p><div className="welcome-points"><span><Sun size={15}/> Solar illumination</span><span><Radio size={15}/> Earth line-of-sight</span><span><Clock3 size={15}/> Critical time windows</span></div></div></section>:<>
          <div className="section-bar"><div><span className="step-number">02</span><b>MISSION INTELLIGENCE</b><span className="section-sub">{activeSite?.name} · {date.replace("T"," ")} UTC</span></div><button className="export-button" onClick={exportCsv}><Download size={15}/> EXPORT EPHEMERIS</button></div>
          <div className="metric-grid">
            <Metric icon={<Sun size={17}/>} label="SUNLIGHT AVAILABILITY" value={`${num(analysis.metrics.illumination_pct)}%`} detail="Mission duration illuminated" tone="amber" progress={analysis.metrics.illumination_pct}/>
            <Metric icon={<Radio size={17}/>} label="EARTH VISIBILITY" value={`${num(analysis.metrics.comm_pct)}%`} detail="Direct communication window" tone="cyan" progress={analysis.metrics.comm_pct}/>
            <Metric icon={<Zap size={17}/>} label="JOINT OPERATION" value={`${num(analysis.metrics.overlap_pct)}%`} detail="Sun + Earth simultaneously visible" tone="mint" progress={analysis.metrics.overlap_pct}/>
            <Metric icon={<Moon size={17}/>} label="LONGEST DARK PERIOD" value={duration(analysis.metrics.longest_dark_hours)} detail={`${analysis.metrics.longest_comm_outage_hours.toFixed(1)}h longest comm outage`} tone="violet"/>
          </div>
          <div className="analysis-grid">
            <section className="panel sky-panel">
              <div className="panel-top"><div><span className="panel-kicker">LIVE SKY GEOMETRY</span><h2>Horizon view</h2><p>Azimuth and elevation from the selected landing site</p></div><span className="sample-tag"><i/> SAMPLE {sample+1} / {count}</span></div>
              <div className="sky-stage"><SkyPlot sunAz={current?.sunAz||0} sunEl={current?.sunEl||0} earthAz={current?.earthAz||0} earthEl={current?.earthEl||0}/><div className="sky-axis"><span>ZENITH +90°</span><span>HORIZON 0°</span></div></div>
              <div className="body-readouts">
                <Readout icon={<Sun size={16}/>} title="SUN" az={current?.sunAz||0} el={current?.sunEl||0} visible={(current?.sunEl||-90)>0} tone="amber"/>
                <Readout icon={<Globe2 size={16}/>} title="EARTH" az={current?.earthAz||0} el={current?.earthEl||0} visible={(current?.earthEl||-90)>0} tone="cyan"/>
              </div>
              <div className="sky-caption"><Layers3 size={14}/><span>Horizon model: <b>{analysis.terrain_source==="none"?"0° reference horizon":"terrain mask fixture"}</b></span><span className="caption-sep">·</span><span>Azimuth clockwise from north</span></div>
            </section>
            <section className="panel score-panel">
              <div className="panel-top"><div><span className="panel-kicker">DECISION SUPPORT</span><h2>Site suitability</h2><p>Composite planning indicator</p></div><div className="score-dial" style={{"--score":`${analysis.score.total*3.6}deg`} as React.CSSProperties}><div><b>{Math.round(analysis.score.total)}</b><small>/100</small></div></div></div>
              <div className="score-list"><ScoreRow label="Power potential" value={analysis.score.power} tone="amber"/><ScoreRow label="Communications" value={analysis.score.communication} tone="cyan"/><ScoreRow label="Survivability" value={analysis.score.survivability} tone="mint"/></div>
              <div className="score-explain"><ShieldCheck size={16}/><span>Heuristic decision score. Not a certified mission feasibility assessment.</span></div>
              <div className="event-list"><div className="event-head">UPCOMING CONSTRAINTS <span>MODEL ESTIMATE</span></div><Event icon={<Sun size={15}/>} label="Time to sunset" value={duration(analysis.metrics.time_to_sunset_hours)}/><Event icon={<Globe2 size={15}/>} label="Time to Earthset" value={duration(analysis.metrics.time_to_earthset_hours)}/><Event icon={<Moon size={15}/>} label="Longest dark interval" value={duration(analysis.metrics.longest_dark_hours)}/></div>
            </section>
          </div>
          <section className="panel timeline-panel">
            <div className="panel-top timeline-head"><div><span className="panel-kicker">TEMPORAL OPERATIONS</span><h2>Illumination & communication timeline</h2><p>Scrub through the mission to inspect Sun and Earth elevation at each sample.</p></div><div className="timeline-time"><Clock3 size={15}/>{current?utcLabel(current.time):"—"}</div></div>
            <div className="timeline-legend"><span><i className="sun-key"/> Sun above horizon</span><span><i className="earth-key"/> Earth above horizon</span><span><i className="both-key"/> Both visible</span><span><i className="dark-key"/> Neither visible</span></div>
            <div className="timeline-strip">{analysis.timeseries.t.map((t,i)=>{const s=analysis.timeseries.sun_el[i]>0,e=analysis.timeseries.earth_el[i]>0;return <button key={i} title={utcLabel(t)} onClick={()=>setSample(i)} className={`${s&&e?"both":s?"sun":e?"earth":"dark"} ${sample===i?"chosen":""}`}/>})}</div>
            <div className="scrubber"><span>START</span><input type="range" min="0" max={Math.max(0,count-1)} value={sample} onChange={e=>setSample(Number(e.target.value))}/><span>END · {days}D</span></div>
            <div className="timeline-foot"><span>SELECTED SAMPLE <b>{sample+1} / {count}</b></span><span>{current?utcLabel(current.time):""}</span></div>
          </section>
          <div className="lower-grid">
            <section className="panel chart-panel"><div className="panel-top"><div><span className="panel-kicker">ANGULAR ELEVATION</span><h2>Sun & Earth trajectory</h2><p>Elevation above the geometric horizon · degrees</p></div><span className="chart-unit">DEGREES</span></div><div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}><defs><linearGradient id="solarFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#e9ad56" stopOpacity=".22"/><stop offset="100%" stopColor="#e9ad56" stopOpacity="0"/></linearGradient><linearGradient id="earthFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#64b7ce" stopOpacity=".2"/><stop offset="100%" stopColor="#64b7ce" stopOpacity="0"/></linearGradient></defs><CartesianGrid stroke="#27333b" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="time" tickFormatter={v=>new Date(v).toLocaleDateString("en-GB",{day:"numeric",month:"short",timeZone:"UTC"})} tick={{fill:"#77848b",fontSize:10}} axisLine={false} tickLine={false} minTickGap={42}/><YAxis domain={[-90,90]} tick={{fill:"#77848b",fontSize:10}} axisLine={false} tickLine={false} width={35}/><Tooltip contentStyle={{background:"#121b20",border:"1px solid #34434a",borderRadius:8,color:"#f4f1e9"}} labelFormatter={v=>utcLabel(String(v))} formatter={(v:any,n:any)=>[`${Number(v).toFixed(1)}°`,n==="sun"?"Sun elevation":"Earth elevation"]}/><Area type="monotone" dataKey="sun" stroke="#e9ad56" strokeWidth={2} fill="url(#solarFill)" dot={false} isAnimationActive={false}/><Area type="monotone" dataKey="earth" stroke="#64b7ce" strokeWidth={2} fill="url(#earthFill)" dot={false} isAnimationActive={false}/></AreaChart></ResponsiveContainer></div></section>

          </div>
        </>}
        {tab==="compare"&&<section className="compare-section">
          <div className="compare-toolbar panel"><div><span className="panel-kicker">SCENARIO LAB</span><h2>Compare landing candidates</h2><p>Compare the current analysis with another candidate under the same mission dates.</p></div><div className="compare-actions"><label><span>ALTERNATIVE SITE</span><select value={compareId} onChange={e=>setCompareId(e.target.value)}>{sites.filter(s=>s.id!==analysis?.site.id).map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label><button className="analyze-button small" onClick={runCompare} disabled={busy||!analysis}><Play size={14}/> COMPARE</button></div></div>
          {comparison?<><div className="compare-summary"><Check size={17}/>{comparison.summary}</div><div className="compare-cards">{comparison.scenarios.map((s,i)=><div className="panel compare-card" key={s.analysis.site.id}><div className="compare-num">0{i+1}</div><span className="panel-kicker">CANDIDATE SITE</span><h3>{s.analysis.site.name}</h3><p>{s.analysis.site.description}</p><div className="compare-total"><b>{Math.round(s.analysis.score.total)}</b><span>/100<br/>SITE SCORE</span></div><ScoreRow label="Sunlight availability" value={s.analysis.metrics.illumination_pct} tone="amber"/><ScoreRow label="Earth visibility" value={s.analysis.metrics.comm_pct} tone="cyan"/><ScoreRow label="Joint operations" value={s.analysis.metrics.overlap_pct} tone="mint"/><div className="compare-coords"><MapPin size={14}/>{s.analysis.site.lat.toFixed(3)}°, {s.analysis.site.lon.toFixed(3)}°</div></div>)}</div></>:<div className="compare-empty"><Layers3 size={30}/><h3>Build a side-by-side comparison</h3><p>Run an analysis first, then select a second candidate to compare its power, communications and overall decision score.</p><button className="analyze-button small" onClick={()=>setTab("overview")}>BACK TO ANALYSIS</button></div>}
        </section>}
        <footer className="footer"><span>© LUNAR LANDING SITE NAVIGATOR</span><span>DECISION SUPPORT ONLY · VERIFY SOURCE DATA BEFORE MISSION USE</span></footer>
      </div>
    </main>
  </div>
}
function Metric({icon,label,value,detail,tone,progress}:{icon:React.ReactNode;label:string;value:string;detail:string;tone:string;progress?:number}){return <div className={`metric-card ${tone}`}><div className="metric-title"><span>{icon}</span>{label}</div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div>{progress!==undefined&&<div className="metric-progress"><i style={{width:`${Math.max(0,Math.min(100,progress))}%`}}/></div>}</div>}
function ScoreRow({label,value,tone}:{label:string;value:number;tone:string}){return <div className="score-row"><div><span>{label}</span><b>{num(value,0)}<small>/100</small></b></div><div className="bar"><i className={tone} style={{width:`${Math.max(0,Math.min(100,value))}%`}}/></div></div>}
function Event({icon,label,value}:{icon:React.ReactNode;label:string;value:string}){return <div className="event-row"><span>{icon}</span><label>{label}</label><b>{value}</b></div>}
function Readout({icon,title,az,el,visible,tone}:{icon:React.ReactNode;title:string;az:number;el:number;visible:boolean;tone:string}){return <div className={`readout ${tone}`}><div className="readout-heading"><span>{icon}</span><b>{title}</b><i className={visible?"visible":"hidden"}>{visible?"VISIBLE":"BELOW HORIZON"}</i></div><div className="readout-values"><div><b>{num(el)}°</b><small>ELEVATION</small></div><div><b>{num(az)}°</b><small>AZIMUTH</small></div></div></div>}
function SkyPlot({sunAz,sunEl,earthAz,earthEl}:{sunAz:number;sunEl:number;earthAz:number;earthEl:number}){
  const point=(az:number,el:number)=>{const elevation=Math.max(-90,Math.min(90,el));const r=elevation>=0?150*(1-elevation/90):150+Math.abs(elevation)/90*24;const a=(az-90)*Math.PI/180;return {x:200+r*Math.cos(a),y:200+r*Math.sin(a)}};
  const s=point(sunAz,sunEl),e=point(earthAz,earthEl);
  return <svg className="sky-svg" viewBox="0 0 400 400" role="img" aria-label="Polar sky plot showing Sun and Earth positions relative to the horizon">
    <defs><radialGradient id="skyGlow"><stop offset="0%" stopColor="#273b40"/><stop offset="100%" stopColor="#111d21"/></radialGradient></defs>
    <circle cx="200" cy="200" r="174" fill="url(#skyGlow)" stroke="#425159" strokeWidth="1"/>
    {[50,100,150].map(r=><circle key={r} cx="200" cy="200" r={r} fill="none" stroke="#425159" strokeDasharray="3 6" opacity=".7"/>)}<path d="M200 20V380M20 200H380" stroke="#526168" strokeDasharray="2 6"/>
    <path d="M200 26 A174 174 0 0 1 374 200 L200 200Z" fill="#dba85b" opacity=".035"/>
    {Array.from({length:12},(_,i)=>{const a=i*Math.PI/6-Math.PI/2;return <g key={i}><line x1={200+158*Math.cos(a)} y1={200+158*Math.sin(a)} x2={200+175*Math.cos(a)} y2={200+175*Math.sin(a)} stroke="#718087"/><text x={200+190*Math.cos(a)} y={200+190*Math.sin(a)} fill="#839197" fontSize="9" textAnchor="middle" dominantBaseline="middle">{i*30}°</text></g>})}
    <circle cx="200" cy="200" r="5" fill="#e8e1d1"/><circle cx={s.x} cy={s.y} r="14" fill="#e8ad56" opacity=".13"/><circle cx={s.x} cy={s.y} r="6" fill="#f0b95f" stroke="#fff0cf" strokeWidth="1.5"/><path d={`M200 200L${s.x} ${s.y}`} stroke="#e8ad56" strokeDasharray="4 5" opacity=".8"/>
    <circle cx={e.x} cy={e.y} r="14" fill="#64b7ce" opacity=".13"/><circle cx={e.x} cy={e.y} r="6" fill="#64b7ce" stroke="#d6f6ff" strokeWidth="1.5"/><path d={`M200 200L${e.x} ${e.y}`} stroke="#64b7ce" strokeDasharray="4 5" opacity=".8"/>
    <text x="200" y="12" textAnchor="middle" fill="#aab6b8" fontSize="9" letterSpacing="2">N</text><text x="200" y="397" textAnchor="middle" fill="#aab6b8" fontSize="9" letterSpacing="2">S</text>
  </svg>
}
export default App;
