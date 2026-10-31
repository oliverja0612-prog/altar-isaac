-- Altar command system. Used by the Console tab and the game's own debug
-- console:  altar <command> [args]   (e.g. "altar boss monstro").
return function(A)
	local mod, game, sfx = A.mod, A.game, A.sfx

	---------------------------------------------------------------------------
	-- Data: bosses, rooms, floors, characters, curses
	---------------------------------------------------------------------------

	-- name, entity type, variant, risky (may misbehave outside its own room)
	A.BOSSES = {
		{ "OBLIVION", "oblivion", 0 },
		{ "Monstro", 20, 0 }, { "Monstro II", 43, 0 }, { "Gish", 43, 1 }, { "Larry Jr", 19, 0 },
		{ "The Hollow", 19, 1 }, { "Tuff Twins", 19, 2 }, { "The Shell", 19, 3 }, { "Chub", 28, 0 },
		{ "C.H.A.D.", 28, 1 }, { "Carrion Queen", 28, 2 }, { "Gurdy", 36, 0 }, { "Gurdy Jr", 99, 0 },
		{ "Mama Gurdy", 266, 0 }, { "Pin", 62, 0 }, { "Scolex", 62, 1 }, { "The Frail", 62, 2 },
		{ "Wormwood", 62, 3 }, { "Famine", 63, 0 }, { "Pestilence", 64, 0 }, { "War", 65, 0 },
		{ "Conquest", 65, 1 }, { "Death", 66, 0 }, { "Headless Horseman", 82, 0 }, { "Duke of Flies", 67, 0 },
		{ "The Husk", 67, 1 }, { "Peep", 68, 0 }, { "The Bloat", 68, 1 }, { "Loki", 69, 0 },
		{ "Lokii", 69, 1 }, { "Fistula", 71, 0 }, { "Teratoma", 71, 1 }, { "Blastocyst", 74, 0 },
		{ "Gemini", 79, 0 }, { "Steven", 79, 1 }, { "Blighted Ovum", 79, 2 }, { "Mask of Infamy", 97, 0 },
		{ "Widow", 100, 0 }, { "The Wretched", 100, 1 }, { "Daddy Long Legs", 101, 0 }, { "Triachnid", 101, 1 },
		{ "The Haunt", 260, 0 }, { "Dingle", 261, 0 }, { "Dangle", 261, 1 }, { "Mega Maw", 262, 0 },
		{ "The Gate", 263, 0 }, { "Mega Fatty", 264, 0 }, { "The Cage", 265, 0 }, { "Dark One", 267, 0 },
		{ "The Adversary", 268, 0 }, { "Polycephalus", 269, 0 }, { "The Pile", 269, 1 }, { "Mr. Fred", 270, 0 },
		{ "Uriel", 271, 0 }, { "Gabriel", 272, 0 }, { "The Stain", 401, 0 }, { "Brownie", 402, 0 },
		{ "The Forsaken", 403, 0 }, { "Little Horn", 404, 0 }, { "Rag Man", 405, 0 }, { "Rag Mega", 409, 0 },
		{ "Sisters Vis", 410, 0 }, { "Big Horn", 411, 0 }, { "The Matriarch", 413, 0 }, { "Reap Creep", 900, 0 },
		{ "The Visage", 903, 0 }, { "The Siren", 904, 0 }, { "The Heretic", 905, 0 }, { "Hornfel", 906, 0 },
		{ "Baby Plum", 908, 0 }, { "The Scourge", 909, 0 }, { "Chimera", 910, 0 }, { "Rotgut", 911, 0 },
		{ "Min-Min", 913, 0 }, { "Clog", 914, 0 }, { "Singe", 915, 0 }, { "Bumbino", 916, 0 },
		{ "Colostomia", 917, 0 }, { "Turdlet", 918, 0 }, { "Horny Boys", 920, 0 },
		{ "Mom", 45, 0, true }, { "Mom's Heart", 78, 0, true }, { "It Lives", 78, 1, true },
		{ "Satan", 84, 0, true }, { "Isaac", 102, 0, true }, { "???", 102, 1, true }, { "The Lamb", 273, 0, true },
		{ "Mega Satan", 274, 0, true }, { "Hush", 407, 0, true }, { "Ultra Greed", 406, 0, true },
		{ "Delirium", 412, 0, true }, { "The Fallen", 81, 0, true },
	}

	-- gfx/ui/boss/portrait_<file>.png shipped with the game
	A.BOSS_PORTRAIT = {
		["OBLIVION"] = "gfx/altar/oblivion_portrait.png",
		["Monstro"] = "20.0_monstro", ["Monstro II"] = "43.0_monstro2", ["Gish"] = "43.1_gish",
		["Larry Jr"] = "19.0_larryjr", ["The Hollow"] = "19.1_thehollow", ["Tuff Twins"] = "19.100_tufftwins",
		["The Shell"] = "shell", ["Chub"] = "28.0_chub", ["C.H.A.D."] = "28.1_chad", ["Carrion Queen"] = "28.2_carrionqueen",
		["Gurdy"] = "36.0_gurdy", ["Gurdy Jr"] = "99.0_gurdyjr", ["Mama Gurdy"] = "266.0_mamagurdy", ["Pin"] = "62.0_pin",
		["Scolex"] = "62.1_scolex", ["The Frail"] = "thefrail", ["Wormwood"] = "902.0_wormwood", ["Famine"] = "63.0_famine",
		["Pestilence"] = "64.0_pestilence", ["War"] = "65.0_war", ["Conquest"] = "65.1_conquest", ["Death"] = "66.0_death",
		["Headless Horseman"] = "82.0_headlesshorseman", ["Duke of Flies"] = "67.0_dukeofflies", ["The Husk"] = "67.1_thehusk",
		["Peep"] = "68.0_peep", ["The Bloat"] = "68.1_bloat", ["Loki"] = "69.0_loki", ["Lokii"] = "69.1_lokii",
		["Fistula"] = "71.0_fistula", ["Teratoma"] = "71.1_teratoma", ["Blastocyst"] = "74.0_blastocyst",
		["Gemini"] = "79.0_gemini", ["Steven"] = "79.1_steven", ["Blighted Ovum"] = "79.2_blightedovum",
		["Mask of Infamy"] = "97.0_maskofinfamy", ["Widow"] = "100.0_widow", ["The Wretched"] = "100.1_thewretched",
		["Daddy Long Legs"] = "101.0_daddylonglegs", ["Triachnid"] = "101.1_triachnid", ["The Haunt"] = "260.0_thehaunt",
		["Dingle"] = "261.0_dingle", ["Dangle"] = "dangle", ["Mega Maw"] = "262.0_megamaw", ["The Gate"] = "263.0_megamaw2",
		["Mega Fatty"] = "264.0_megafatty", ["The Cage"] = "265.0_fatty2", ["Dark One"] = "267.0_darkone",
		["The Adversary"] = "268.0_darkone2", ["Polycephalus"] = "269.0_polycephalus", ["The Pile"] = "269.1_polycephalus2",
		["Mr. Fred"] = "270.0_megafred", ["The Stain"] = "401.0_thestain", ["Brownie"] = "402.0_brownie",
		["The Forsaken"] = "403.0_theforsaken", ["Little Horn"] = "404.0_littlehorn", ["Rag Man"] = "405.0_ragman",
		["Rag Mega"] = "ragmega", ["Sisters Vis"] = "sistersvis", ["Big Horn"] = "bighorn", ["The Matriarch"] = "matriarch",
		["Reap Creep"] = "900.0_reapcreep", ["The Visage"] = "903.0_visage", ["The Siren"] = "904.0_siren",
		["The Heretic"] = "905.0_heretic", ["Hornfel"] = "906.0_hornfel", ["Baby Plum"] = "908.0_babyplum",
		["The Scourge"] = "909.0_scourge", ["Chimera"] = "910.0_chimera", ["Rotgut"] = "911.0_rotgut",
		["Min-Min"] = "minmin", ["Clog"] = "clog", ["Singe"] = "singe", ["Bumbino"] = "bumbino",
		["Colostomia"] = "colostomia", ["Turdlet"] = "turdlet", ["Horny Boys"] = "hornyboys", ["Mom"] = "45.0_mom",
		["Mom's Heart"] = "78.0_momsheart", ["It Lives"] = "78.1_itlives", ["Satan"] = "84.0_satan",
		["Isaac"] = "102.0_isaac", ["???"] = "102.1_bluebaby", ["The Lamb"] = "273.0_thelamb",
		["Mega Satan"] = "274.0_megasatan", ["Hush"] = "407.0_hush", ["Ultra Greed"] = "406.0_ultragreed",
		["Delirium"] = "delirium", ["The Fallen"] = "81.0_thefallen",
	}

	A.ROOMS = {
		{ "HARDEST: Oblivion", "hardest" }, -- Floor 14, straight into her room
		{ "Boss", RoomType.ROOM_BOSS }, { "Treasure", RoomType.ROOM_TREASURE }, { "Shop", RoomType.ROOM_SHOP },
		{ "Secret", RoomType.ROOM_SECRET }, { "Super Secret", RoomType.ROOM_SUPERSECRET },
		{ "Ultra Secret", RoomType.ROOM_ULTRASECRET }, { "Curse", RoomType.ROOM_CURSE },
		{ "Sacrifice", RoomType.ROOM_SACRIFICE }, { "Library", RoomType.ROOM_LIBRARY },
		{ "Arcade", RoomType.ROOM_ARCADE }, { "Planetarium", RoomType.ROOM_PLANETARIUM },
		{ "Challenge", RoomType.ROOM_CHALLENGE }, { "Dice", RoomType.ROOM_DICE }, { "Chest", RoomType.ROOM_CHEST },
		{ "Devil / Angel", GridRooms.ROOM_DEVIL_IDX, true }, { "Error Room", GridRooms.ROOM_ERROR_IDX, true },
		{ "Black Market", GridRooms.ROOM_BLACK_MARKET_IDX, true }, { "Crawlspace", GridRooms.ROOM_DUNGEON_IDX, true },
		{ "Start", "start" },
	}

	-- console `stage` codes
	A.FLOORS = {
		{ "Basement", "1" }, { "Cellar", "1a" }, { "Burning Basement", "1b" }, { "Downpour", "1c" }, { "Dross", "1d" },
		{ "Caves", "3" }, { "Catacombs", "3a" }, { "Flooded Caves", "3b" }, { "Mines", "3c" }, { "Ashpit", "3d" },
		{ "Depths", "5" }, { "Necropolis", "5a" }, { "Dank Depths", "5b" }, { "Mausoleum", "5c" }, { "Gehenna", "5d" },
		{ "Womb", "7" }, { "Utero", "7a" }, { "Scarred Womb", "7b" }, { "Corpse", "7c" }, { "Blue Womb", "9" },
		{ "Sheol", "10" }, { "Cathedral", "10a" }, { "Dark Room", "11" }, { "Chest", "11a" }, { "The Void", "12" },
		{ "Home", "13" }, { "Floor 14: Fallen Sky", "14" },
	}

	-- name, PlayerType, gfx/ui/stage/playerportrait_<key>.png
	A.CHARS = {
		{ "Isaac", 0, "isaac" }, { "Magdalene", 1, "magdalene" }, { "Cain", 2, "cain" }, { "Judas", 3, "judas" },
		{ "???", 4, "bluebaby" }, { "Eve", 5, "eve" }, { "Samson", 6, "samson" }, { "Azazel", 7, "azazel" },
		{ "Lazarus", 8, "lazarus" }, { "Eden", 9, "eden" }, { "The Lost", 10, "thelost" }, { "Lilith", 13, "lilith" },
		{ "Keeper", 14, "keeper" }, { "Apollyon", 15, "apollyon" }, { "Forgotten", 16, "theforgotten" },
		{ "Bethany", 18, "bethany" }, { "Jacob", 19, "jacob" },
		{ "T. Isaac", 21, "isaac_b" }, { "T. Magdalene", 22, "magdalene_b" }, { "T. Cain", 23, "cain_b" },
		{ "T. Judas", 24, "judas_b" }, { "T. ???", 25, "bluebaby_b" }, { "T. Eve", 26, "eve_b" },
		{ "T. Samson", 27, "samson_b" }, { "T. Azazel", 28, "azazel_b" }, { "T. Lazarus", 29, "lazarus_b" },
		{ "T. Eden", 30, "eden_b" }, { "T. Lost", 31, "thelost_b" }, { "T. Lilith", 32, "lilith_b" },
		{ "T. Keeper", 33, "keeper_b" }, { "T. Apollyon", 34, "apollyon_b" }, { "T. Forgotten", 35, "theforgotten_b" },
		{ "T. Bethany", 36, "bethany_b" }, { "T. Jacob", 37, "jacob_b" },
	}

	A.CURSES = {
		{ "Darkness", LevelCurse.CURSE_OF_DARKNESS }, { "Labyrinth", LevelCurse.CURSE_OF_LABYRINTH },
		{ "Lost", LevelCurse.CURSE_OF_THE_LOST }, { "Unknown", LevelCurse.CURSE_OF_THE_UNKNOWN },
		{ "Cursed", LevelCurse.CURSE_OF_THE_CURSED }, { "Maze", LevelCurse.CURSE_OF_MAZE },
		{ "Blind", LevelCurse.CURSE_OF_BLIND },
	}

	---------------------------------------------------------------------------
	-- Actions shared by the menu and commands
	---------------------------------------------------------------------------

	local function norm(s) return (tostring(s or ""):lower():gsub("[^%w]", "")) end
	A.norm = norm

	-- Best match by exact name, then prefix, then substring.
	local function find(list, query, nameOf)
		local q = norm(query)
		if q == "" then return nil end
		local prefix, contains
		for _, v in ipairs(list) do
			local n = norm(nameOf(v))
			if n == q then return v end
			if not prefix and n:sub(1, #q) == q then prefix = v end
			if not contains and n:find(q, 1, true) then contains = v end
		end
		return prefix or contains
	end
	A.findIn = find

	local pendingBoss, pendingDelay = nil, 0

	local function spawnBossHere(b)
		local room = game:GetRoom()
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			if A.isBossLike(e) and e:IsActiveEnemy(false) then e:Remove() end
		end
		local pos = room:FindFreePickupSpawnPosition(room:GetCenterPos(), 0, true)
		Isaac.Spawn(b[2], b[3], 0, pos, Vector.Zero, nil)
		sfx:Play(SoundEffect.SOUND_SATAN_GROW, 0.6)
	end

	function A.fightBoss(b, here)
		if b[2] == "oblivion" then
			A.summonOblivion(here)
			return
		end
		if here then
			spawnBossHere(b)
			return
		end
		local level = game:GetLevel()
		local idx = level:QueryRoomTypeIndex(RoomType.ROOM_BOSS, false, RNG())
		pendingBoss, pendingDelay = b, 8
		if idx == level:GetCurrentRoomIndex() then return end
		game:StartRoomTransition(idx, Direction.NO_DIRECTION, RoomTransitionAnim.TELEPORT)
	end

	function mod:altarPendingBoss()
		if not pendingBoss then return end
		pendingDelay = pendingDelay - 1
		if pendingDelay <= 0 and game:GetRoom():GetType() == RoomType.ROOM_BOSS then
			spawnBossHere(pendingBoss)
			pendingBoss = nil
		elseif pendingDelay < -150 then
			pendingBoss = nil
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_UPDATE, mod.altarPendingBoss)

	function A.warpRoom(r)
		local level = game:GetLevel()
		local idx = r[2]
		if idx == "hardest" then
			A.goHardest()
			return
		elseif idx == "start" then
			idx = level:GetStartingRoomIndex()
		elseif not r[3] then
			idx = level:QueryRoomTypeIndex(r[2], false, RNG())
		end
		game:StartRoomTransition(idx, Direction.NO_DIRECTION, RoomTransitionAnim.TELEPORT)
	end

	function A.warpFloor(f)
		if f[2] == "14" then
			A.enterFloor14()
			return
		end
		Isaac.ExecuteCommand("stage " .. f[2])
	end

	function A.setCharacter(c)
		local p = Isaac.GetPlayer(0)
		local ok = pcall(function() p:ChangePlayerType(c[2]) end)
		if ok then
			A.refreshStats()
			sfx:Play(SoundEffect.SOUND_DEATH_CARD, 0.6)
		end
		return ok
	end

	function A.clearRoom()
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			if e.Type ~= A.OBLIVION_TYPE and (e:IsVulnerableEnemy() or (e:IsEnemy() and e:IsActiveEnemy(false))) then e:Kill() end
		end
	end

	function A.revealMap()
		local level = game:GetLevel()
		level:ApplyMapEffect()
		level:ApplyCompassEffect(true)
		level:ApplyBlueMapEffect()
		level:UpdateVisibility()
	end

	---------------------------------------------------------------------------
	-- Commands
	---------------------------------------------------------------------------

	local HEART_CMDS = {
		red = function(p, n) p:AddHearts(2 * n) end, container = function(p, n) p:AddMaxHearts(2 * n) end,
		soul = function(p, n) p:AddSoulHearts(2 * n) end, black = function(p, n) p:AddBlackHearts(2 * n) end,
		bone = function(p, n) p:AddBoneHearts(n) end, rotten = function(p, n) p:AddRottenHearts(2 * n) end,
		golden = function(p, n) p:AddGoldenHearts(n) end, eternal = function(p, n) p:AddEternalHearts(n) end,
		broken = function(p, n) p:AddBrokenHearts(n) end,
	}

	local STAT_KEYS = { damage = "damage", dmg = "damage", tears = "tears", speed = "speed", range = "range",
		shotspeed = "shotspeed", luck = "luck" }

	local function num(s, default) return math.floor(tonumber(s) or default) end

	-- Split "give cosmic overclock 5" into words, pulling a trailing number off.
	local function nameAndCount(args)
		local n = tonumber(args[#args])
		local words = {}
		for i = 1, #args - (n and 1 or 0) do words[#words + 1] = args[i] end
		return table.concat(words, " "), n and math.floor(n) or 1
	end

	local function listNames(list, nameOf, limit)
		local out = {}
		for i, v in ipairs(list) do
			if i > (limit or 999) then out[#out + 1] = "..." break end
			out[#out + 1] = nameOf(v)
		end
		return table.concat(out, ", ")
	end

	A.COMMANDS = {}
	local function cmd(name, usage, help, fn)
		A.COMMANDS[#A.COMMANDS + 1] = { name = name, usage = usage, help = help, fn = fn }
	end

	cmd("help", "help [command]", "List commands or show one command's usage", function(args)
		if args[1] then
			for _, c in ipairs(A.COMMANDS) do
				if c.name == args[1] then return c.usage .. "  -  " .. c.help end
			end
			return "Unknown command: " .. args[1], true
		end
		local names = {}
		for _, c in ipairs(A.COMMANDS) do names[#names + 1] = c.name end
		return "Commands: " .. table.concat(names, ", ")
	end)

	-- "sad onion 2, overclock, black hole 3" -> calls fn(words, count) per part.
	-- Returns the joined messages and whether any part failed.
	local function eachSpec(args, fn)
		local msgs, failed = {}, false
		for part in table.concat(args, " "):gmatch("[^,]+") do
			local words = {}
			for w in part:gmatch("%S+") do words[#words + 1] = w end
			if #words > 0 then
				local msg, err = fn(words)
				msgs[#msgs + 1] = msg
				failed = failed or err
			end
		end
		if #msgs == 0 then return "Nothing to do. Example: give sad onion 2, overclock 3", true end
		return table.concat(msgs, "\n"), failed
	end

	local function itemSpec(verb, max, action)
		return function(args)
			return eachSpec(args, function(words)
				local name, n = nameAndCount(words)
				local item = find(A.getCatalogue(), name, function(i) return i.name end)
				if not item then return "No item matches '" .. name .. "'", true end
				n = math.min(n, max)
				for _ = 1, n do action(item) end
				return verb .. " " .. item.name .. " x" .. n
			end)
		end
	end

	cmd("give", "give <item> [n], <item> [n], ...", "Give items; separate several with commas",
		itemSpec("Gave", 99, function(item) Isaac.GetPlayer(0):AddCollectible(item.id, 0, true) end))

	cmd("spawn", "spawn <item> [n], <item> [n], ...", "Spawn item pedestals; separate several with commas",
		itemSpec("Spawned", 20, function(item) A.spawnItem(item.id) end))

	cmd("floor14", "floor14", "Go to FLOOR 14, The Fallen Sky (Oblivion waits at the end)", function()
		A.enterFloor14()
		return "Falling into the sky..."
	end)

	cmd("oblivion", "oblivion [here|fall]", "Summon OBLIVION (secret boss); 'fall' lands the killing blow", function(args)
		if args[1] == "fall" then return A.oblivionFall() end
		A.summonOblivion(args[1] == "here")
		return "Something is coming..."
	end)

	-- play one of Altar's own tracks (handy for checking a new song works)
	local TRACKS = {
		intro = "Altar Oblivion Intro", reveal = "Altar Oblivion Reveal", battle = "Altar Oblivion Battle",
		battle2 = "Altar Oblivion Battle 2", ending = "Altar Oblivion Ending", space = "Altar Oblivion Space",
		farewell = "Altar Oblivion Farewell", floor14 = "Altar Fallen Sky",
	}
	cmd("music", "music <track>", "Play an Altar track: intro, reveal, battle, battle2, ending, space, farewell, floor14", function(args)
		local name = TRACKS[(args[1] or ""):lower()]
		if not name then return "Tracks: intro, reveal, battle, battle2, ending, space, farewell, floor14", true end
		local id = Isaac.GetMusicIdByName(name)
		if id <= 0 then return name .. " isn't in this build (missing from music_in/)", true end
		MusicManager():Play(id, 1)
		MusicManager():UpdateVolume()
		return "Playing " .. name
	end)

	cmd("farewell", "farewell", "Preview OBLIVION's farewell scene", function()
		return A.previewFarewell()
	end)

	cmd("combo", "combo <name|all|list>", "Give every item for a combo", function(args)
		local q = table.concat(args, " ")
		if q == "" or q == "list" then
			return "Combos: " .. listNames(A.COMBOS, function(c) return c.name end)
		end
		if q == "all" then
			for _, c in ipairs(A.COMBOS) do A.giveCombo(c.key) end
			return "Gave every combo. Good luck, enemies."
		end
		local c = find(A.COMBOS, q, function(v) return v.name end)
		if not c then return "No combo matches '" .. q .. "'", true end
		A.giveCombo(c.key)
		return "Combo ready: " .. c.name
	end)

	cmd("boss", "boss <name>", "Teleport to the boss room and fight any boss", function(args)
		local b = find(A.BOSSES, table.concat(args, " "), function(v) return v[1] end)
		if not b then return "No boss matches. Try: bosses", true end
		A.fightBoss(b)
		return "Summoning " .. b[1] .. (b[4] and " (unstable outside its own room)" or "")
	end)

	cmd("bosshere", "bosshere <name>", "Spawn a boss in this room", function(args)
		local b = find(A.BOSSES, table.concat(args, " "), function(v) return v[1] end)
		if not b then return "No boss matches. Try: bosses", true end
		A.fightBoss(b, true)
		return "Spawned " .. b[1]
	end)

	cmd("bosses", "bosses", "List every boss", function()
		return listNames(A.BOSSES, function(v) return v[1] end)
	end)

	cmd("tp", "tp <room>", "Teleport to a room type (boss, shop, secret, devil, ...)", function(args)
		local r = find(A.ROOMS, table.concat(args, " "), function(v) return v[1] end)
		if not r then return "Rooms: " .. listNames(A.ROOMS, function(v) return v[1] end), true end
		A.warpRoom(r)
		return "Teleporting to " .. r[1]
	end)

	cmd("stage", "stage <floor>", "Warp to a floor by name (womb, mines, 3c...)", function(args)
		local q = table.concat(args, " ")
		local f
		for _, v in ipairs(A.FLOORS) do
			if v[2] == q then f = v end
		end
		f = f or find(A.FLOORS, q, function(v) return v[1] end)
		if not f then return "Floors: " .. listNames(A.FLOORS, function(v) return v[1] end), true end
		A.warpFloor(f)
		return "Warping to " .. f[1]
	end)

	cmd("char", "char <name>", "Become another character", function(args)
		local c = find(A.CHARS, table.concat(args, " "), function(v) return v[1] end)
		if not c then return "Characters: " .. listNames(A.CHARS, function(v) return v[1] end), true end
		if not A.setCharacter(c) then return "This game version can't change characters", true end
		return "You are now " .. c[1]
	end)

	cmd("hearts", "hearts <type> [n], <type> [n]", "Add hearts: red container soul black bone rotten golden eternal broken", function(args)
		return eachSpec(args, function(words)
			local fn = HEART_CMDS[(words[1] or ""):lower()]
			if not fn then return "Types: red container soul black bone rotten golden eternal broken", true end
			local n = num(words[2], 1)
			fn(Isaac.GetPlayer(0), n)
			return "+" .. n .. " " .. words[1] .. " hearts"
		end)
	end)

	for _, res in ipairs({ { "coins", "AddCoins" }, { "bombs", "AddBombs" }, { "keys", "AddKeys" } }) do
		cmd(res[1], res[1] .. " [amount]", "Add " .. res[1], function(args)
			local n = num(args[1], 99)
			local p = Isaac.GetPlayer(0)
			p[res[2]](p, n)
			return "+" .. n .. " " .. res[1]
		end)
	end

	cmd("stat", "stat <damage|tears|speed|range|shotspeed|luck|reset> [value]", "Set an Altar stat bonus", function(args)
		if args[1] == "reset" then
			for k in pairs(A.statBonus) do A.statBonus[k] = 0 end
			A.refreshStats()
			return "Stat bonuses reset"
		end
		local key = STAT_KEYS[(args[1] or ""):lower()]
		local v = tonumber(args[2])
		if not key or not v then return "Usage: stat damage 5", true end
		A.statBonus[key] = v
		A.refreshStats()
		return key .. " bonus = " .. v
	end)

	cmd("heal", "heal", "Full health", function()
		A.forEachPlayer(function(p) p:SetFullHearts() end)
		return "Healed"
	end)
	cmd("god", "god", "Toggle god mode", function()
		A.godMode = not A.godMode
		return "God mode " .. (A.godMode and "ON" or "OFF")
	end)
	cmd("spikes", "spikes", "Toggle Spike Shield (spiked rocks and spikes can't hurt you)", function()
		A.spikeShield = not A.spikeShield
		if A.spikeShield then A.defuseSpikedRocks() end
		return "Spike Shield " .. (A.spikeShield and "ON" or "OFF")
	end)
	cmd("hardest", "hardest", "Go straight to the hardest fight: OBLIVION on Floor 14", function()
		A.goHardest()
		return "Going to Floor 14..."
	end)
	cmd("phase", "phase", "Toggle walking over rocks and pits", function()
		A.phaseWalk = not A.phaseWalk
		A.refreshStats()
		return "Phase walk " .. (A.phaseWalk and "ON" or "OFF")
	end)
	cmd("clear", "clear", "Kill every enemy in the room", function() A.clearRoom() return "Room cleared" end)
	cmd("map", "map", "Reveal the whole floor", function() A.revealMap() return "Map revealed" end)
	cmd("reroll", "reroll", "Reroll items in the room (D6)", function()
		Isaac.GetPlayer(0):UseActiveItem(CollectibleType.COLLECTIBLE_D6, 0, -1)
		return "Rerolled"
	end)
	cmd("charge", "charge", "Fully charge active items", function()
		local p = Isaac.GetPlayer(0)
		for slot = 0, 1 do
			if not pcall(function() p:FullCharge(slot, true) end) then
				p:SetActiveCharge(p:GetActiveCharge(slot) + 12, slot)
			end
		end
		return "Charged"
	end)
	cmd("blackhole", "blackhole", "Open an Event Horizon in front of you", function()
		A.spawnEventHorizon(Isaac.GetPlayer(0))
		return "Nothing escapes."
	end)
	cmd("nuke", "nuke", "Destroy every normal enemy", function()
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			if e:IsVulnerableEnemy() and not A.isBossLike(e) then e:Kill() end
		end
		game:ShakeScreen(30)
		return "Boom."
	end)
	cmd("curses", "curses [off|<name>]", "Remove all curses or add one", function(args)
		local level = game:GetLevel()
		local q = args[1]
		if not q or q == "off" then
			level:RemoveCurses(level:GetCurses())
			return "Curses removed"
		end
		local c = find(A.CURSES, q, function(v) return v[1] end)
		if not c then return "Curses: " .. listNames(A.CURSES, function(v) return v[1] end), true end
		level:AddCurse(c[2], true)
		return "Added Curse of " .. c[1]
	end)
	cmd("q4", "q4 [amount]", "Spawn random quality 4 items", function(args)
		local n = math.min(num(args[1], 1), 10)
		for _ = 1, n do A.spawnRandomQ4(Isaac.GetPlayer(0)) end
		return "Spawned " .. n .. " quality 4 item" .. (n > 1 and "s" or "")
	end)
	cmd("seed", "seed", "Show the run seed", function()
		return "Seed: " .. game:GetSeeds():GetStartSeedString()
	end)
	cmd("die", "die", "Kill yourself", function() Isaac.GetPlayer(0):Die() return "Goodbye" end)

	local runOne

	-- Runs "give overclock 3" (or several joined with ';') and returns (message, isError).
	function A.runCommand(line)
		line = tostring(line)
		if not line:find(";", 1, true) then return runOne(line) end
		local out, anyErr = {}, false
		for part in line:gmatch("[^;]+") do
			if part:match("%S") then
				local msg, err = runOne(part)
				out[#out + 1] = msg
				anyErr = anyErr or err
			end
		end
		return table.concat(out, "\n"), anyErr
	end

	function runOne(line)
		local args = {}
		for w in tostring(line):gmatch("%S+") do args[#args + 1] = w end
		local name = table.remove(args, 1)
		if not name then return "", false end
		name = name:lower()
		for _, c in ipairs(A.COMMANDS) do
			if c.name == name then
				local ok, msg, isErr = pcall(c.fn, args)
				if not ok then return "Error: " .. tostring(msg), true end
				return msg or "", isErr
			end
		end
		return "Unknown command '" .. name .. "'. Type help", true
	end

	-- Suggestions for the Console tab: commands, then items / bosses / rooms etc.
	function A.suggest(line)
		local out = {}
		local words = {}
		for w in line:gmatch("%S+") do words[#words + 1] = w end
		local trailing = line:sub(-1) == " "
		if #words == 0 or (#words == 1 and not trailing) then
			local q = (words[1] or ""):lower()
			for _, c in ipairs(A.COMMANDS) do
				if c.name:sub(1, #q) == q then out[#out + 1] = { text = c.name .. " ", label = c.usage } end
			end
			return out
		end
		local head = words[1]:lower()
		local rest = table.concat(words, " ", 2)
		-- after a comma, complete the newest item and keep what came before
		local before = head .. " "
		local lastComma = line:match("^.*(),")
		if lastComma and (head == "give" or head == "spawn" or head == "hearts") then
			before = line:sub(1, lastComma - 1) .. ", "
			rest = line:sub(lastComma + 1)
		end
		local sources = {
			give = { A.getCatalogue(), function(v) return v.name end },
			spawn = { A.getCatalogue(), function(v) return v.name end },
			boss = { A.BOSSES, function(v) return v[1] end },
			bosshere = { A.BOSSES, function(v) return v[1] end },
			tp = { A.ROOMS, function(v) return v[1] end },
			stage = { A.FLOORS, function(v) return v[1] end },
			char = { A.CHARS, function(v) return v[1] end },
			combo = { A.COMBOS, function(v) return v.name end },
			curses = { A.CURSES, function(v) return v[1] end },
		}
		local src = sources[head]
		if not src then return out end
		local q = norm((rest:gsub("%s%d+%s*$", "")))
		for _, v in ipairs(src[1]) do
			local n = src[2](v)
			if q == "" or norm(n):find(q, 1, true) then
				out[#out + 1] = { text = before .. n .. " ", label = n }
				if #out >= 6 then break end
			end
		end
		return out
	end

	-- "altar <command>" in the game's debug console
	function mod:altarExecuteCmd(command, params)
		if command ~= "altar" then return end
		local msg = A.runCommand(params)
		if A.consoleLog then A.consoleLog("altar " .. params, msg) end
		return msg
	end
	mod:AddCallback(ModCallbacks.MC_EXECUTE_CMD, mod.altarExecuteCmd)
end
