import React, { useState } from "react";

const TEAMS = [
  "Chennai Super Kings",
  "Mumbai Indians",
  "Royal Challengers Bangalore",
  "Kolkata Knight Riders",
  "Sunrisers Hyderabad",
  "Rajasthan Royals",
  "Delhi Capitals",
  "Gujarat Titans",
  "Lucknow Super Giants",
  "Punjab Kings",
];

const VENUES = [
  "Wankhede Stadium",
  "Eden Gardens",
  "MA Chidambaram Stadium, Chepauk",
  "M.Chinnaswamy Stadium",
  "Narendra Modi Stadium",
  "Arun Jaitley Stadium",
  "Rajiv Gandhi International Stadium",
];

function MetricCard({ label, value, icon }) {
  return (
    <div className="bg-slate-900/50 border border-slate-700 p-4 rounded-xl flex items-center space-x-4">
      <div className="bg-slate-800 p-2 rounded-lg text-neon">
        {icon}
      </div>
      <div>
        <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
        <p className="text-lg font-bold text-white">{value}</p>
      </div>
    </div>
  );
}

const Icons = {
  Score: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/></svg>
  ),
  Powerplay: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
  ),
  Batter: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18.42 2.61a2.1 2.1 0 0 0-2.97 0l-12.84 12.84a2.1 2.1 0 0 0 0 2.97l2.97 2.97a2.1 2.1 0 0 0 2.97 0l12.84-12.84a2.1 2.1 0 0 0 0-2.97Z"/><path d="M8.11 11.39 12.61 15.89"/></svg>
  ),
  Bowler: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/><path d="M12 2v4"/><path d="M12 18v4"/><path d="M4.93 4.93l2.83 2.83"/><path d="M16.24 16.24l2.83 2.83"/><path d="M2 12h4"/><path d="M18 12h4"/><path d="M4.93 19.07l2.83-2.83"/><path d="M16.24 7.76l2.83-2.83"/></svg>
  )
};

export default function MatchPredictor() {
  const [home, setHome] = useState(TEAMS[0]);
  const [away, setAway] = useState(TEAMS[1]);
  const [venue, setVenue] = useState(VENUES[0]);
  const [tossWinner, setTossWinner] = useState("home");
  const [tossDecision, setTossDecision] = useState("bat");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  async function handlePredict() {
    setLoading(true);
    try {
      if (home === away) {
        setResult({ error: 'Home and Away teams must be different.' });
        setLoading(false);
        return;
      }

      const featRes = await fetch(
        `http://127.0.0.1:8000/api/features/${encodeURIComponent(home)}/${encodeURIComponent(away)}/${encodeURIComponent(venue)}`,
      );
      if (!featRes.ok) throw new Error(`Failed to load features`);
      const featData = await featRes.json();

      const payload = {
        ...featData,
        is_toss_winner_team1: tossWinner === "home" ? 1 : 0,
        toss_decision: tossDecision,
      };

      const res = await fetch("http://127.0.0.1:8000/api/predict/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      
      if (!res.ok) throw new Error(`Prediction failed`);
      const data = await res.json();
      
      setResult({ features: payload, data });
    } catch (e) {
      console.error(e);
      setResult({ error: String(e) });
    } finally {
      setLoading(false);
    }
  }

  const getTeamLabel = (teamName) => {
    const shorts = {
      "Chennai Super Kings": "CSK",
      "Mumbai Indians": "MI",
      "Royal Challengers Bangalore": "RCB",
      "Kolkata Knight Riders": "KKR",
      "Sunrisers Hyderabad": "SRH",
      "Rajasthan Royals": "RR",
      "Delhi Capitals": "DC",
      "Gujarat Titans": "GT",
      "Lucknow Super Giants": "LSG",
      "Punjab Kings": "PBKS"
    };
    return shorts[teamName] || teamName.split(' ').pop();
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 max-w-7xl mx-auto p-4">
      {/* Input Section */}
      <div className="lg:col-span-5 space-y-6 bg-slate-800/30 p-6 rounded-2xl border border-slate-700">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2 text-slate-400 uppercase tracking-wider">Home Team</label>
            <select
              value={home}
              onChange={(e) => setHome(e.target.value)}
              className="w-full p-4 bg-slate-900 border border-slate-700 rounded-xl text-white focus:ring-2 focus:ring-neon focus:border-transparent transition"
            >
              {TEAMS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2 text-slate-400 uppercase tracking-wider">Away Team</label>
            <select
              value={away}
              onChange={(e) => setAway(e.target.value)}
              className="w-full p-4 bg-slate-900 border border-slate-700 rounded-xl text-white focus:ring-2 focus:ring-neon focus:border-transparent transition"
            >
              {TEAMS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2 text-slate-400 uppercase tracking-wider">Venue</label>
            <select
              value={venue}
              onChange={(e) => setVenue(e.target.value)}
              className="w-full p-4 bg-slate-900 border border-slate-700 rounded-xl text-white focus:ring-2 focus:ring-neon focus:border-transparent transition"
            >
              {VENUES.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2 text-slate-400 uppercase tracking-wider">Toss Winner</label>
              <div className="flex bg-slate-900 p-1 rounded-xl border border-slate-700">
                <button
                  onClick={() => setTossWinner("home")}
                  className={`flex-1 py-2 px-1 text-xs rounded-lg transition ${tossWinner === "home" ? "bg-neon text-slate-900 font-bold" : "text-slate-400"}`}
                >
                  {getTeamLabel(home)}
                </button>
                <button
                  onClick={() => setTossWinner("away")}
                  className={`flex-1 py-2 px-1 text-xs rounded-lg transition ${tossWinner === "away" ? "bg-neon text-slate-900 font-bold" : "text-slate-400"}`}
                >
                  {getTeamLabel(away)}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2 text-slate-400 uppercase tracking-wider">Toss Decision</label>
              <div className="flex bg-slate-900 p-1 rounded-xl border border-slate-700">
                <button
                  onClick={() => setTossDecision("bat")}
                  className={`flex-1 py-2 rounded-lg transition ${tossDecision === "bat" ? "bg-neon text-slate-900 font-bold" : "text-slate-400"}`}
                >
                  Bat
                </button>
                <button
                  onClick={() => setTossDecision("bowl")}
                  className={`flex-1 py-2 rounded-lg transition ${tossDecision === "bowl" ? "bg-neon text-slate-900 font-bold" : "text-slate-400"}`}
                >
                  Bowl
                </button>
              </div>
            </div>
          </div>
        </div>

        <button
          onClick={handlePredict}
          disabled={loading}
          className="w-full py-4 bg-gradient-to-r from-neon to-cyan-500 text-slate-900 font-black rounded-xl hover:shadow-[0_0_20px_rgba(0,255,179,0.3)] hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-slate-900" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              ANALYZING DATA...
            </span>
          ) : "GENERATE PREDICTION"}
        </button>
      </div>

      {/* Results Section */}
      <div className="lg:col-span-7">
        <div className="bg-slate-800/30 p-6 rounded-2xl border border-slate-700 h-full">
          <h3 className="text-xl font-black mb-6 text-white tracking-tighter">PREDICTION ANALYSIS</h3>
          
          {loading ? (
            <div className="space-y-8 animate-pulse">
              {/* Win Probabilities Skeleton */}
              <div className="space-y-6 bg-slate-900/50 p-6 rounded-2xl border border-slate-700/50">
                <div className="flex justify-between items-end">
                  <div className="space-y-2 w-1/3">
                    <div className="h-3 bg-slate-800 rounded w-1/2"></div>
                    <div className="h-8 bg-slate-800 rounded w-3/4"></div>
                  </div>
                  <div className="space-y-2 w-1/3 text-right">
                    <div className="h-3 bg-slate-800 rounded w-1/2 ml-auto"></div>
                    <div className="h-8 bg-slate-800 rounded w-3/4 ml-auto"></div>
                  </div>
                </div>
                <div className="w-full h-4 bg-slate-800 rounded-full"></div>
              </div>

              {/* Insights Card Grid Skeleton */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-slate-900/50 border border-slate-700/50 p-6 rounded-2xl space-y-4">
                  <div className="h-4 bg-slate-800 rounded w-1/3"></div>
                  <div className="h-6 bg-slate-800 rounded w-2/3"></div>
                  <div className="h-3 bg-slate-800 rounded w-full"></div>
                </div>
                <div className="bg-slate-900/50 border border-slate-700/50 p-6 rounded-2xl space-y-4">
                  <div className="h-4 bg-slate-800 rounded w-1/3"></div>
                  <div className="h-6 bg-slate-800 rounded w-2/3"></div>
                  <div className="h-3 bg-slate-800 rounded w-full"></div>
                </div>
              </div>

              {/* Metrics Grid Skeleton */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="bg-slate-900/50 border border-slate-700/50 p-4 rounded-xl flex items-center space-x-4">
                    <div className="bg-slate-800 w-10 h-10 rounded-lg"></div>
                    <div className="flex-1 space-y-2">
                      <div className="h-3 bg-slate-800 rounded w-1/4"></div>
                      <div className="h-5 bg-slate-800 rounded w-3/4"></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : result ? (
            result.error ? (
              <div className="bg-red-500/10 border border-red-500/50 p-4 rounded-xl text-red-400">
                {result.error}
              </div>
            ) : (
              <div className="space-y-8">
                {/* Win Probabilities */}
                <div className="space-y-6 bg-slate-900/50 p-6 rounded-2xl border border-slate-700">
                  {(() => {
                    const probs = result.data.probabilities || [];
                    const pTeam1 = probs[1] ?? 0.5;
                    const pTeam2 = probs[0] ?? 0.5;
                    
                    return (
                      <div className="space-y-4">
                        <div className="flex justify-between items-end">
                          <div>
                            <p className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">{home}</p>
                            <p className="text-4xl font-black text-neon">{Math.round(pTeam1 * 100)}%</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">{away}</p>
                            <p className="text-4xl font-black text-rose-500">{Math.round(pTeam2 * 100)}%</p>
                          </div>
                        </div>
                        <div className="w-full h-4 bg-slate-800 rounded-full overflow-hidden flex border border-slate-700">
                          <div className="h-full bg-neon transition-all duration-1000 ease-out" style={{ width: `${pTeam1 * 100}%` }} />
                          <div className="h-full bg-rose-500 transition-all duration-1000 ease-out" style={{ width: `${pTeam2 * 100}%` }} />
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {/* Sleek Insights Section */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Venue Intelligence Card */}
                  {(() => {
                    const chaseBias = result.features.venue_chase_bias ?? 0.5;
                    const chasePercent = Math.round(chaseBias * 100);
                    const defendPercent = 100 - chasePercent;
                    
                    return (
                      <div className="bg-slate-900/50 border border-slate-700 p-6 rounded-2xl flex flex-col justify-between space-y-4">
                        <div className="flex items-center space-x-3">
                          <div className="bg-slate-800 p-2 rounded-lg text-neon">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
                          </div>
                          <h4 className="text-sm font-bold text-white uppercase tracking-wider">Venue Intelligence</h4>
                        </div>
                        
                        <div className="space-y-3">
                          <p className="text-xs text-slate-300">
                            {chasePercent >= 50 ? (
                              <span>
                                <strong className="text-neon">{chasePercent}%</strong> of matches here are won by the <strong className="text-white">chasing team</strong> (Batting 2nd).
                              </span>
                            ) : (
                              <span>
                                <strong className="text-rose-400">{defendPercent}%</strong> of matches here are won by the <strong className="text-white">defending team</strong> (Batting 1st).
                              </span>
                            )}
                          </p>
                          
                          {/* Visual split gauge bar */}
                          <div className="relative pt-1">
                            <div className="flex mb-2 items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                              <span>Batting 1st ({defendPercent}%)</span>
                              <span>Batting 2nd ({chasePercent}%)</span>
                            </div>
                            <div className="overflow-hidden h-3 text-xs flex rounded-full bg-slate-800 border border-slate-700/50">
                              <div style={{ width: `${defendPercent}%` }} className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-slate-700 transition-all duration-1000"></div>
                              <div style={{ width: `${chasePercent}%` }} className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-neon transition-all duration-1000"></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })()}

                  {/* Star Player Matchup Card */}
                  {(() => {
                    const t1Stars = Math.round(result.features.team1_star_players ?? 0);
                    const t2Stars = Math.round(result.features.team2_star_players ?? 0);
                    const totalStars = t1Stars + t2Stars;
                    const t1Ratio = totalStars > 0 ? (t1Stars / totalStars) * 100 : 50;
                    const t2Ratio = totalStars > 0 ? (t2Stars / totalStars) * 100 : 50;
                    const homeLabel = getTeamLabel(home);
                    const awayLabel = getTeamLabel(away);
                    
                    const renderStars = (count) => {
                      const maxStars = 5;
                      return (
                        <div className="flex space-x-1 justify-center my-1">
                          {Array.from({ length: maxStars }).map((_, i) => (
                            <svg 
                              key={i} 
                              className={`w-4 h-4 ${i < count ? "text-amber-400 fill-amber-400 filter drop-shadow-[0_0_4px_rgba(251,191,36,0.5)]" : "text-slate-700"}`} 
                              xmlns="http://www.w3.org/2000/svg" 
                              viewBox="0 0 24 24" 
                              fill="none" 
                              stroke="currentColor" 
                              strokeWidth="2" 
                              strokeLinecap="round" 
                              strokeLinejoin="round"
                            >
                              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                            </svg>
                          ))}
                        </div>
                      );
                    };

                    return (
                      <div className="bg-slate-900/50 border border-slate-700 p-6 rounded-2xl flex flex-col justify-between space-y-4">
                        <div className="flex items-center space-x-3">
                          <div className="bg-slate-800 p-2 rounded-lg text-neon">
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                          </div>
                          <h4 className="text-sm font-bold text-white uppercase tracking-wider">Star Lineup Power</h4>
                        </div>
                        
                        <div className="space-y-3">
                          <div className="flex justify-between items-center text-center">
                            <div className="flex-1">
                              <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">{homeLabel}</p>
                              <p className="text-2xl font-black text-white">{t1Stars}</p>
                              {renderStars(t1Stars)}
                            </div>
                            <div className="px-4 text-xs font-black text-slate-500 uppercase">VS</div>
                            <div className="flex-1">
                              <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">{awayLabel}</p>
                              <p className="text-2xl font-black text-white">{t2Stars}</p>
                              {renderStars(t2Stars)}
                            </div>
                          </div>

                          {/* Tug-of-war split bar */}
                          <div className="overflow-hidden h-2 text-xs flex rounded-full bg-slate-800 border border-slate-700/50 mt-2">
                            <div style={{ width: `${t1Ratio}%` }} className="shadow-none bg-neon transition-all duration-1000"></div>
                            <div style={{ width: `${t2Ratio}%` }} className="shadow-none bg-rose-500 transition-all duration-1000"></div>
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {/* New Metrics Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <MetricCard 
                    label="Exp. 1st Innings Score" 
                    value={result.features.expected_first_innings_score} 
                    icon={Icons.Score}
                  />
                  <MetricCard 
                    label="Powerplay Target" 
                    value={result.features.powerplay_score} 
                    icon={Icons.Powerplay}
                  />
                  <MetricCard 
                    label="Top Batter to Watch" 
                    value={result.features.top_run_scorer} 
                    icon={Icons.Batter}
                  />
                  <MetricCard 
                    label="Top Bowler to Watch" 
                    value={result.features.top_wicket_taker} 
                    icon={Icons.Bowler}
                  />
                </div>

                {/* Raw Features Detail */}
                <details className="text-xs text-slate-500 group">
                  <summary className="cursor-pointer hover:text-slate-300 transition-colors uppercase font-bold tracking-widest">
                    Technical Match Features
                  </summary>
                  <div className="mt-4 bg-slate-900 rounded-xl p-4 border border-slate-800 overflow-x-auto">
                    <pre className="text-neon/70">
                      {JSON.stringify(result.features, null, 2)}
                    </pre>
                  </div>
                </details>
              </div>
            )
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-center space-y-4">
              <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center border border-slate-700">
                <svg className="w-8 h-8 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <p className="text-slate-500 font-medium">Select teams and venue to generate <br/> match insights and probability.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
