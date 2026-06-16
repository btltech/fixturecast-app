function sentence(value) {
  return value.endsWith(".") ? value : `${value}.`;
}

export function getLeagueLandingContent(league) {
  if (!league) {
    return {
      intro: [],
      highlights: [],
      coverageHeading: "Why follow this competition on FixtureCast?",
    };
  }

  const fallbackCountry = league.country && league.country !== "World" ? league.country : "global";
  const genericIntro = [
    sentence(`FixtureCast tracks ${league.name} with AI-powered predictions, fixture coverage, standings and recent results`),
    sentence(`Use this page to follow ${fallbackCountry} football trends, check upcoming matches and jump straight into model-backed predictions for the biggest games in ${league.name}`),
  ];

  const genericHighlights = [
    `Upcoming ${league.name} fixtures with direct links to match predictions`,
    `Standings, results and schedule navigation for ${league.name}`,
    `Competition coverage that updates as new fixtures are published`,
  ];

  const specificById = {
    1: {
      intro: [
        "The FIFA World Cup is the highest-visibility tournament in football, and search intent spikes hard around fixtures, group tables, knockout brackets and prediction angles.",
        "FixtureCast uses this landing page to surface World Cup fixtures, match predictions and tournament navigation quickly, so users can move from broad tournament queries into individual game analysis without friction.",
      ],
      highlights: [
        "World Cup fixture coverage built for group-stage and knockout-stage searches",
        "Direct paths from tournament browsing into individual AI match predictions",
        "Useful for World Cup 2026 build-up, live tournament windows and post-match research",
      ],
    },
    29: {
      intro: [
        "South American World Cup qualifying drives repeat search demand because every matchday can reshape qualification spots, goal difference scenarios and public expectations.",
        "This page helps users move from qualifier discovery into team-specific predictions, fixtures and results, which is exactly the kind of intent chain search engines like to see satisfied on one route.",
      ],
      highlights: [
        "World Cup qualifying fixture discovery for CONMEBOL searches",
        "Fast links into prediction pages for the biggest qualification matches",
        "Useful for qualification table, fixture and betting-intent searches",
      ],
    },
    30: {
      intro: [
        "Asian World Cup qualifying attracts a mix of country-level searches, match intent and qualification-path research throughout the cycle.",
        "FixtureCast keeps the route focused on fixtures, results and prediction access so users can understand the schedule and reach game-level analysis in one step.",
      ],
      highlights: [
        "Asian World Cup qualifier coverage for fixtures and prediction intent",
        "Competition page structured for country, date and match-level searches",
        "Useful for qualification windows and marquee AFC matchdays",
      ],
    },
    31: {
      intro: [
        "CONCACAF World Cup qualifying often produces sharp search spikes around regional giants, decisive away trips and final-round qualification scenarios.",
        "This landing page gives FixtureCast a dedicated surface for qualifier fixtures and prediction discovery instead of forcing that demand through generic pages.",
      ],
      highlights: [
        "CONCACAF qualifier fixture and prediction coverage",
        "Direct route to high-interest match prediction pages",
        "Better support for country and qualification scenario searches",
      ],
    },
    32: {
      intro: [
        "European World Cup qualifying has enormous search volume because users look for fixtures, group standings, qualification rules and match predictions across every international window.",
        "This page strengthens FixtureCast as a tournament hub by combining schedule discovery, standings navigation and direct prediction links for each fixture.",
      ],
      highlights: [
        "European World Cup qualifier hub for fixtures, standings and predictions",
        "Built for international break search demand and qualification race coverage",
        "Short path from group-level browsing into match-level prediction pages",
      ],
    },
    34: {
      intro: [
        "African World Cup qualifying creates recurring demand around qualification races, national-team form and matchday prediction angles.",
        "FixtureCast uses this route to turn broad tournament interest into useful pages for fixtures, results and individual match predictions.",
      ],
      highlights: [
        "African qualifier fixture and result discovery",
        "Direct AI prediction access for major qualification matches",
        "Useful for national-team, schedule and qualification-intent searches",
      ],
    },
    39: {
      intro: [
        "The Premier League is one of the strongest organic search opportunities on the site because users constantly search for fixtures, tables, team form and prediction angles across the full season.",
        "This page gives FixtureCast a focused Premier League landing route where upcoming matches, standings navigation and AI match predictions all sit together instead of being split across generic listings.",
      ],
      highlights: [
        "Premier League fixture discovery with fast access to AI match predictions",
        "Useful entry point for title race, relegation battle and big-six search intent",
        "Supports prediction, standings and results journeys from one landing page",
      ],
    },
    140: {
      intro: [
        "La Liga searches are driven by club demand, title-race interest and constant fixture research, especially around Barcelona, Real Madrid and Atletico Madrid.",
        "This landing page gives users one place to browse upcoming La Liga matches and move into detailed FixtureCast prediction pages for the biggest games.",
      ],
      highlights: [
        "La Liga fixtures and prediction access for high-intent search traffic",
        "Supports club-driven searches around marquee Spanish fixtures",
        "Useful for standings, schedule and match analysis journeys",
      ],
    },
    135: {
      intro: [
        "Serie A combines club-focused search demand with strong interest in form, defensive trends and match predictions across the full campaign.",
        "FixtureCast uses this page to connect that demand to live fixture discovery and deeper prediction pages instead of leaving users at a broad competition overview.",
      ],
      highlights: [
        "Serie A fixture discovery tied directly to prediction pages",
        "Useful for club-form, standings and schedule searches",
        "Supports season-long search intent around top-four and title-race matches",
      ],
    },
    78: {
      intro: [
        "Bundesliga search intent tends to cluster around title contenders, European places and high-scoring matchups, which makes a structured league hub especially useful.",
        "This route helps FixtureCast capture that demand with schedule context, standings navigation and direct links to AI match prediction pages.",
      ],
      highlights: [
        "Bundesliga fixture and match prediction discovery",
        "Useful for title race, Champions League place and club-form searches",
        "Direct links from league browsing into game-level prediction pages",
      ],
    },
    61: {
      intro: [
        "Ligue 1 search demand is heavily shaped by top-club fixtures, goals markets and standings movement across the season.",
        "FixtureCast keeps this page focused on useful next steps: upcoming fixtures, results context and direct paths into AI-backed prediction pages.",
      ],
      highlights: [
        "Ligue 1 fixture and standings discovery in one route",
        "Useful for club-driven prediction and form searches",
        "Direct jump from competition page to match analysis pages",
      ],
    },
    2: {
      intro: [
        "The Champions League generates some of the highest-value football searches on the internet because users want fixtures, knockout paths, tables and prediction angles around elite clubs.",
        "This route gives FixtureCast a dedicated UEFA competition hub that can rank for competition-level intent while funneling traffic into individual prediction pages for each tie.",
      ],
      highlights: [
        "Champions League fixtures, standings context and prediction discovery",
        "Useful for group-stage, round-of-16 and knockout-round search demand",
        "Built to connect broad UEFA interest with match-level AI predictions",
      ],
    },
    3: {
      intro: [
        "The Europa League draws strong search demand from club fans tracking fixtures, qualification stakes and knockout-round predictions.",
        "FixtureCast uses this page as a competition hub so users can find schedule context and then move directly into the prediction pages that matter most.",
      ],
      highlights: [
        "Europa League fixture discovery with AI prediction links",
        "Useful for knockout-round and qualification-race search intent",
        "Supports competition-level and match-level journeys together",
      ],
    },
    13: {
      intro: [
        "Copa Libertadores is one of the strongest non-European competition opportunities for search because interest spans group tables, away trips, knockout ties and betting-style queries.",
        "This page gives FixtureCast a dedicated South American tournament surface where users can browse fixtures and reach individual AI prediction pages without leaving the competition context.",
      ],
      highlights: [
        "Copa Libertadores fixture and prediction hub",
        "Useful for South American club football search intent year-round",
        "Connects competition discovery to individual match analysis routes",
      ],
    },
    253: {
      intro: [
        "MLS is a high-opportunity calendar-year competition because search interest runs differently from European leagues and often peaks around matchdays, playoffs and rivalry games.",
        "FixtureCast uses this landing page to keep MLS users inside a dedicated competition route with updated fixtures, standings context and direct prediction links.",
      ],
      highlights: [
        "MLS fixture and match prediction discovery on a calendar-year schedule",
        "Useful for rivalry fixtures, playoff pushes and team-form searches",
        "Supports American soccer search demand without forcing users through generic pages",
      ],
    },
  };

  const specific = specificById[league.id];
  if (specific) {
    return {
      coverageHeading: `Why ${league.name} matters on FixtureCast`,
      intro: specific.intro.map(sentence),
      highlights: specific.highlights,
    };
  }

  return {
    coverageHeading: `Why follow ${league.name} on FixtureCast?`,
    intro: genericIntro,
    highlights: genericHighlights,
  };
}