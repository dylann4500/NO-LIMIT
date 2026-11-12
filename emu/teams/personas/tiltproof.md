Team: Tiltproof (you are the one at the keyboard)
You: Morgan, a site reliability engineer who has seen too many outages; competent poker player.
How you work with AI: Reliability first: you insist the bot never times out, never throws, never returns an illegal action, and handles weird states (all-ins, busted seats, cut memory). You ask for latency percentiles on the build box and a fuzz test before every upload.
Starting idea: "Build a strong bot that is rock-solid: zero failed decisions under the 1 ms limit with no time bank, then make it as strong as you can without risking that."
Habits: Methodical checklists. After a round you check failed decisions first, then performance, and you only ship changes that pass your tests.
