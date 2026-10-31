-- OBLIVION, Devourer of Stars: Altar's secret boss.
-- Summon with the "oblivion" command or Warp > Bosses.
--
-- Story intro (illustrated panels + voice lines), three forms with their own
-- sprites and attacks, voiced interludes between forms, and a death sequence.
-- Voice lines come from scripts/altar_voice.lua (AltarModManager/tools/import_voice.py).
return function(A)
	local mod, game, sfx = A.mod, A.game, A.sfx
	local music = MusicManager()

	local OBLIVION = Isaac.GetEntityTypeByName("Oblivion")
	local HOLE = Isaac.GetEntityVariantByName("Altar Oblivion Hole")
	local SINGULARITY = Isaac.GetEntityVariantByName("Altar Singularity")
	local ARENA = Isaac.GetEntityVariantByName("Altar Oblivion Arena")
	-- custom tracks from content/music.xml (tools/import_music.py); -1 when missing
	local MUSIC_INTRO = Isaac.GetMusicIdByName("Altar Oblivion Intro")
	local MUSIC_BATTLE = Isaac.GetMusicIdByName("Altar Oblivion Battle")
	local MUSIC_BATTLE2 = Isaac.GetMusicIdByName("Altar Oblivion Battle 2") -- from half HP
	local MUSIC_ENDING = Isaac.GetMusicIdByName("Altar Oblivion Ending")    -- the moment she falls
	Isaac.DebugString("[Altar Core] music ids intro=" .. tostring(MUSIC_INTRO) .. " battle=" .. tostring(MUSIC_BATTLE)
		.. " battle2=" .. tostring(MUSIC_BATTLE2) .. " ending=" .. tostring(MUSIC_ENDING))

	local FORMS = {
		{ idle = "Idle1", charge = "Charge1", title = "FORM I", sub = "OBLIVION", scale = 1.0 },
		{ idle = "Idle2", charge = "Charge2", title = "FORM II", sub = "THE HOLLOW SERAPH", scale = 1.08 },
		{ idle = "Idle3", charge = "Charge3", title = "FORM III", sub = "THE LAST STAR", scale = 1.18 },
	}

	-- voice lines + subtitles; missing sounds fall back to subtitles only
	local VOICE = {}
	do
		local ok, v = pcall(include, "scripts.altar_voice")
		if ok and type(v) == "table" then VOICE = v end
		for _, line in ipairs(VOICE) do
			line.id = line.sound and Isaac.GetSoundIdByName(line.sound) or -1
		end
	end

	local PHASE_LEN, DEATH_LEN = 140, 320
	local DAMAGE_CAP = 0.008 -- no single hit takes more than 0.8% of max HP

	---------------------------------------------------------------------------
	-- Drawing helpers (cutscenes draw on top of everything)
	---------------------------------------------------------------------------

	local px = Sprite()
	px:Load("gfx/altar/altar_pixel.anm2", true)
	px:Play("Idle", true)

	local hole = Sprite()
	hole:Load("gfx/altar/horizon.anm2", true)
	hole:Play("Idle", true)

	local orb = Sprite()
	orb:Load("gfx/altar/bh_tear.anm2", true)
	orb:Play("Spin", true)

	-- story flipbooks (tools/make_story.py), loaded up front so the cutscene never hitches.
	-- Panels 3 and 4 follow the voice line frame by frame; the others loop.
	local FLIP_FRAMES = 48 -- 12 drawings x 4 ticks
	local FLIP_SYNC = { [3] = true, [4] = true }
	local panels = {}
	for i = 1, 5 do
		local s = Sprite()
		s:Load("gfx/altar/story/flip" .. i .. ".anm2", true)
		s:Play("Play", true)
		panels[i] = s
	end

	local function font(...)
		local f = Font()
		for _, p in ipairs({ ... }) do
			f:Load(p)
			local ok, loaded = pcall(f.IsLoaded, f)
			if not ok or loaded then return f end
		end
		return f
	end
	local fBig = font("font/upheaval.fnt", "font/teammeatfont16bold.fnt")
	local fText = font("font/pftempestasevencondensed.fnt", "font/terminus.fnt")

	local function lineH(f)
		local ok, h = pcall(f.GetLineHeight, f)
		return (ok and type(h) == "number" and h > 0) and h or 10
	end

	local function rect(x, y, w, h, r, g, b, a)
		if w <= 0 or h <= 0 or a <= 0 then return end
		px.Scale = Vector(w / 4, h / 4)
		px.Color = Color(r, g, b, a, 0, 0, 0)
		px:Render(Vector(math.floor(x), math.floor(y)), Vector.Zero, Vector.Zero)
	end

	local function circle(cx, cy, radius, r, g, b, a, thick)
		local n = math.max(24, math.floor(radius * 1.6))
		for i = 0, n - 1 do
			local ang = i / n * math.pi * 2
			rect(cx + math.cos(ang) * radius - 1, cy + math.sin(ang) * radius * 0.75 - 1, thick or 2, thick or 2, r, g, b, a)
		end
	end

	-- centred text with a 1px drop shadow so it stays readable over anything
	local function textC(f, str, y, r, g, b, a, scale)
		local W = Isaac.GetScreenWidth()
		scale = scale or 1
		local w = f:GetStringWidth(str) * scale
		local x = math.floor((W - w) / 2)
		f:DrawStringScaled(str, x + 1, math.floor(y) + 1, scale, scale, KColor(0, 0, 0, a * 0.8), 0, false)
		f:DrawStringScaled(str, x, math.floor(y), scale, scale, KColor(r, g, b, a), 0, false)
	end

	local function clamp(v, lo, hi) return math.max(lo or 0, math.min(hi or 1, v)) end
	local function ease(t) t = clamp(t) return 1 - (1 - t) ^ 3 end
	local function playSound(id, vol, pitch) sfx:Play(id, vol or 1, 0, false, pitch or 1) end

	-- custom boss SFX made with ElevenLabs (tools/import_sfx.py). Missing ones fall back to
	-- the game's own sound; layer=true plays both, for the short custom hits.
	local FX = {}
	for _, k in ipairs({ "roar", "laser", "pillar", "blackhole", "supernova", "feathers", "orb", "implosion", "transform" }) do
		FX[k] = Isaac.GetSoundIdByName("Altar FX " .. k)
	end
	local function fx(key, fallback, vol, pitch, layer)
		local id = FX[key]
		if id and id > 0 then
			sfx:Play(id, vol or 1, 0, false, pitch or 1)
			if layer and fallback then playSound(fallback, (vol or 1) * 0.5, pitch) end
		elseif fallback then
			playSound(fallback, vol, pitch)
		end
	end
	-- The game's room-music logic swaps the track back to its own boss/room music,
	-- so the track we want is re-asserted every frame (see altarOblivionEffects).
	local wantedMusic, wantedVol, wantedUntil = nil, 1, nil

	local function startMusic(id, fallback, volume, holdFrames)
		pcall(function()
			if id and id > 0 then
				music:Play(id, volume or 1)
				music:UpdateVolume()
				wantedMusic, wantedVol = id, volume or 1
				wantedUntil = holdFrames and (game:GetFrameCount() + holdFrames) or nil
			elseif fallback then
				music:Crossfade(fallback)
			end
		end)
	end

	local function voiceFrames(i, fallback)
		local v = VOICE[i]
		return (v and v.frames and v.frames > 0) and v.frames or fallback
	end

	---------------------------------------------------------------------------
	-- Cutscene state
	---------------------------------------------------------------------------

	local cs -- { kind = "intro"|"phase"|"death", t, ... }
	local boss -- the live Oblivion entity
	local arena -- the void floor laid over the boss room
	local deathHole -- the black hole she falls into
	local bar = { shown = 0, trail = 1, last = 1, hit = 0 }
	local stars = {}
	local pending -- summon queued for after a room transition
	local subtitle -- { line = i, t0 = frame, frames = n }
	local pillars = {} -- judgement beams: { pos, t, delay }
	local nova -- supernova: { zone = Vector, t, len }

	function A.cutsceneActive() return cs ~= nil end

	-- music dips while she speaks so the voice is never buried under the soundtrack
	local ducked = false
	local function duck(on)
		if on == ducked then return end
		ducked = on
		pcall(function() music:VolumeSlide(on and 0.3 or 1, on and 0.12 or 0.025) end)
	end

	local function stopVoices()
		for _, v in ipairs(VOICE) do
			if v.id and v.id > 0 then sfx:Stop(v.id) end
		end
		subtitle = nil
		duck(false)
	end

	local function say(i)
		local v = VOICE[i]
		if not v then return end
		stopVoices() -- one line at a time: a new line never gets lost under an old one
		if v.id and v.id > 0 then
			sfx:Play(v.id, 2, 0, false, 1)
			duck(true)
		end
		subtitle = { line = i, t0 = 0, frames = voiceFrames(i, 110) }
	end

	local function freezePlayers(on)
		A.forEachPlayer(function(p) p.ControlsEnabled = not on end)
	end

	local function clearProjectiles()
		for _, e in ipairs(Isaac.FindByType(EntityType.ENTITY_PROJECTILE)) do e:Die() end
	end

	local function lockRoom()
		local room = game:GetRoom()
		room:SetClear(false)
		for slot = 0, 7 do
			local door = room:GetDoor(slot)
			if door then door:Close(true) end
		end
	end

	-- intro timeline: a fade, five voiced story panels, then the reveal
	local function buildIntro()
		local segs, t = {}, 40
		for i = 1, 5 do
			local dur = math.max(150, voiceFrames(i, 0) + 45)
			segs[i] = { start = t, dur = dur, panel = i, line = i }
			t = t + dur
		end
		return segs, t
	end

	local function startCutscene(kind, extra)
		cs = { kind = kind, t = 0 }
		for k, v in pairs(extra or {}) do cs[k] = v end
		if kind ~= "phase" then freezePlayers(true) end
	end

	local function spawnBoss()
		local room = game:GetRoom()
		local npc = Isaac.Spawn(OBLIVION, 0, 0, room:GetCenterPos() + Vector(0, -40), Vector.Zero, nil):ToNPC()
		npc:GetData().altarCut = true
		boss = npc
		return npc
	end

	-- the custom arena: a void floor drawn under every entity, sized to the room
	-- the custom arena: a void laid over the whole room (floor and walls), under every entity
	local function spawnArena(alpha)
		if arena and arena:Exists() then return end
		local room = game:GetRoom()
		local e = Isaac.Spawn(EntityType.ENTITY_EFFECT, ARENA, 0, room:GetCenterPos(), Vector.Zero, nil)
		e:AddEntityFlags(EntityFlag.FLAG_RENDER_FLOOR)
		e.SpriteScale = Vector(room:GetGridWidth() / 15, room:GetGridHeight() / 9)
		e.Color = Color(1, 1, 1, alpha or 0, 0, 0, 0)
		arena = e
	end

	local function setArenaAlpha(a)
		if arena and arena:Exists() then arena.Color = Color(1, 1, 1, clamp(a), 0, 0, 0) end
	end

	-- rooms Oblivion was fought in this floor: the game's own room-clear reward (the
	-- boss's chest / item, or the Void's ending chest) never spawns there
	local fightRooms = {}

	local function beginIntro()
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			if e:IsActiveEnemy(false) or e.Type == EntityType.ENTITY_DELIRIUM then e:Remove() end
		end
		fightRooms[game:GetLevel():GetCurrentRoomIndex()] = true
		clearProjectiles()
		lockRoom()
		spawnArena()
		setArenaAlpha(A.floor14 and 0.9 or 0)
		bar = { shown = 0, trail = 1, last = 1, hit = 0 }
		startMusic(MUSIC_INTRO, nil, 0.7)
		if MUSIC_INTRO <= 0 then pcall(function() music:Fadeout(0.02) end) end
		stars, pillars, nova = {}, {}, nil
		local segs, reveal = buildIntro()
		startCutscene("intro", { segs = segs, reveal = reveal, len = reveal + 270 })
		playSound(SoundEffect.SOUND_HELL_PORTAL1, 0.8, 0.6)
		if A.closeMenu then A.closeMenu() end
	end

	-- FLOOR 14, The Fallen Sky: The Void re-skinned as a dead sky; every room is the
	-- void arena, and Oblivion waits where Delirium would be.
	local floor14Pending, floor14Check = false, nil
	A.floor14 = false

	function A.enterFloor14()
		floor14Pending = true
		Isaac.ExecuteCommand("stage 12")
	end

	function mod:altarFloor14Level()
		A.floor14 = floor14Pending
		floor14Pending = false
		fightRooms = {}
		if A.floor14 and A.banner then A.banner("FLOOR 14", "THE FALLEN SKY") end
	end
	mod:AddCallback(ModCallbacks.MC_POST_NEW_LEVEL, mod.altarFloor14Level)

	-- Delirium is hidden and frozen the moment it spawns (it shape-shifts into other
	-- bosses, so looking for it later can miss), and the intro starts a few frames on
	function mod:altarFloor14Delirium(npc)
		if not A.floor14 or (boss and boss:Exists()) then return end
		npc.Visible = false
		npc:AddEntityFlags(EntityFlag.FLAG_FREEZE | EntityFlag.FLAG_NO_TARGET)
		npc.EntityCollisionClass = EntityCollisionClass.ENTCOLL_NONE
		if not cs then floor14Check = 3 end
	end
	mod:AddCallback(ModCallbacks.MC_POST_NPC_INIT, mod.altarFloor14Delirium, EntityType.ENTITY_DELIRIUM)

	function mod:altarBlockCleanAward()
		if fightRooms[game:GetLevel():GetCurrentRoomIndex()] then return true end
	end
	mod:AddCallback(ModCallbacks.MC_PRE_SPAWN_CLEAN_AWARD, mod.altarBlockCleanAward)

	-- anything the replaced boss drops on its way out (chest, trophy, boss item) goes too
	function mod:altarBlockBossDrops(pickup)
		if not (cs and cs.kind == "intro") then return end
		local v = pickup.Variant
		if v == PickupVariant.PICKUP_BIGCHEST or v == PickupVariant.PICKUP_TROPHY
			or v == PickupVariant.PICKUP_COLLECTIBLE then
			pickup:Remove()
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_PICKUP_INIT, mod.altarBlockBossDrops)

	function A.summonOblivion(here)
		if boss and boss:Exists() then return end
		local room = game:GetRoom()
		if here or room:GetType() == RoomType.ROOM_BOSS then
			beginIntro()
			return
		end
		local level = game:GetLevel()
		pending = 0
		game:StartRoomTransition(level:QueryRoomTypeIndex(RoomType.ROOM_BOSS, false, RNG()), Direction.NO_DIRECTION,
			RoomTransitionAnim.TELEPORT)
	end

	---------------------------------------------------------------------------
	-- Boss AI
	---------------------------------------------------------------------------

	-- voice line played when an attack starts (scripts/altar_voice.lua lines 10-14)
	local TAUNTS = { lasers = 10, pillars = 11, collapse = 12, supernova = 13, hole = 14 }

	local ATTACKS = {
		{ "rings", "barrage", "spiral", "blink", "orbs", "lasers" },
		{ "rings", "barrage", "spiral", "blink", "lasers", "hole", "summon", "feathers", "pillars", "orbs" },
		{ "rings", "spiral", "lasers", "hole", "dash", "collapse", "feathers", "pillars", "supernova", "orbs" },
	}

	local TINT = {
		Color(0.5, 0.2, 1, 1, 0.3, 0, 0.5),
		Color(0.85, 0.8, 1, 1, 0.45, 0.4, 0.6),
		Color(1, 0.55, 0.2, 1, 0.7, 0.25, 0),
	}
	local STAR = Color(1, 1, 1, 1, 0.6, 0.6, 0.8)
	local FEATHER = Color(1, 1, 1, 1, 0.8, 0.8, 0.85)

	local function shoot(npc, pos, vel, color, scale, kind)
		local p = Isaac.Spawn(EntityType.ENTITY_PROJECTILE, ProjectileVariant.PROJECTILE_NORMAL, 0, pos, vel, npc):ToProjectile()
		p.FallingSpeed = 0
		p.FallingAccel = -0.1
		p.Height = -28
		p.Color = color or TINT[1]
		p.Scale = scale or 1.2
		p:GetData().altarShot = kind or "orb"
		return p
	end

	local function ring(npc, n, speed, offset, color, scale, kind)
		for i = 0, n - 1 do
			shoot(npc, npc.Position, Vector.FromAngle(offset + i * 360 / n):Resized(speed), color, scale, kind)
		end
	end

	local function phaseOf(npc)
		local r = npc.HitPoints / npc.MaxHitPoints
		return r > 0.66 and 1 or r > 0.33 and 2 or 3
	end

	local function nearestPlayer(pos)
		return game:GetNearestPlayer(pos) or Isaac.GetPlayer(0)
	end

	local function play(npc, anim)
		local s = npc:GetSprite()
		if not s:IsPlaying(anim) then s:Play(anim, true) end
	end

	local function pickAttack(d)
		local pool = ATTACKS[d.phase]
		local choice
		for _ = 1, 8 do
			choice = pool[math.random(#pool)]
			if choice ~= d.last
				and not (choice == "collapse" and d.collapseCd > 0)
				and not (choice == "supernova" and d.novaCd > 0)
				and not (choice == "summon" and d.summonCd > 0) then
				break
			end
		end
		if (choice == "collapse" and d.collapseCd > 0) or (choice == "supernova" and d.novaCd > 0) then choice = "spiral" end
		d.last = choice
		return choice
	end

	local function hurtPlayer(p, amount, src)
		if A.godMode then return end
		p:TakeDamage(amount, 0, EntityRef(src), 30)
	end

	-- Each attack is a function(npc, d, t) called every frame; return true when done.
	local ATTACK = {}

	function ATTACK.rings(npc, d, t)
		local waves = ({ 4, 5, 6 })[d.phase]
		local n = ({ 22, 26, 32 })[d.phase]
		if t % 16 == 0 then
			ring(npc, n, 4.5 + (t / 16 % 2) * 2.5, (t / 16) * (180 / n), t % 32 == 0 and TINT[d.phase] or STAR)
			playSound(SoundEffect.SOUND_BLOODSHOOT, 0.7, 0.7)
		end
		return t >= waves * 16
	end

	function ATTACK.barrage(npc, d, t)
		if t % 5 == 0 then
			local target = nearestPlayer(npc.Position)
			-- lead the target slightly so standing still or strafing both get punished
			local aim = target.Position + target.Velocity * 8
			local dir = (aim - npc.Position):Normalized()
			local spread = ({ 5, 7, 9 })[d.phase]
			for i = 1, spread do
				shoot(npc, npc.Position, dir:Rotated((i - (spread + 1) / 2) * 10):Resized(11.5), TINT[d.phase], 1, "orb")
			end
			playSound(SoundEffect.SOUND_BLOODSHOOT, 0.6, 1.2)
		end
		return t >= 54
	end

	function ATTACK.spiral(npc, d, t)
		local arms = d.phase + 3
		if t % 3 == 0 then
			for i = 0, arms - 1 do
				local a = t * (d.phase == 3 and 13 or 9) + i * 360 / arms
				shoot(npc, npc.Position, Vector.FromAngle(a):Resized(6), TINT[d.phase], 1, "orb")
				if d.phase == 3 then shoot(npc, npc.Position, Vector.FromAngle(-a):Resized(4), STAR, 0.9, "orb") end
			end
		end
		npc.Velocity = npc.Velocity * 0.85
		return t >= 130
	end

	function ATTACK.blink(npc, d, t)
		d.trail = true
		if t < 12 then
			npc.Color = Color(1, 1, 1, 1 - t / 12, 0.5, 0, 1)
		elseif t == 12 then
			local room = game:GetRoom()
			local p = nearestPlayer(npc.Position)
			local center = room:GetCenterPos()
			npc.Position = room:GetClampedPosition(center + (center - p.Position) * 0.8, 40)
			npc.Velocity = Vector.Zero
			fx("orb", SoundEffect.SOUND_HELL_PORTAL1, 0.7, 1.4)
		elseif t < 24 then
			npc.Color = Color(1, 1, 1, (t - 12) / 12, 0.5, 0, 1)
		elseif t == 24 then
			npc.Color = Color(1, 1, 1, 1, 0, 0, 0)
			ring(npc, 28 + d.phase * 6, 6.5, math.random(360), STAR)
		end
		if t >= 34 then d.trail = false end
		return t >= 34
	end

	function ATTACK.orbs(npc, d, t)
		if t % 10 == 0 and t < 50 then
			for i = -1, 1, 2 do
				local p = shoot(npc, npc.Position, Vector.FromAngle(t * 20 + i * 90):Resized(3), TINT[d.phase], 1.6, "void")
				p:AddProjectileFlags(ProjectileFlags.SMART)
				p.HomingStrength = 0.55 + d.phase * 0.2
			end
			fx("orb", SoundEffect.SOUND_BLACK_POOF, 0.6, 1)
		end
		return t >= 60
	end

	function ATTACK.lasers(npc, d, t)
		local count = ({ 4, 6, 8 })[d.phase]
		npc.Velocity = npc.Velocity * 0.7
		if t == 0 then
			d.laserBase = math.random(360)
			d.tele = {}
			for i = 0, count - 1 do d.tele[#d.tele + 1] = d.laserBase + i * 360 / count end
			playSound(SoundEffect.SOUND_DOGMA_LIGHT_RAY_CHARGE, 1)
		end
		if t < 40 then
			play(npc, FORMS[d.phase].charge)
		elseif t == 40 then
			d.tele = nil
			for i = 0, count - 1 do
				local laser = EntityLaser.ShootAngle(LaserVariant.THICK_RED, npc.Position, d.laserBase + i * 360 / count, 100,
					Vector(0, -30), npc)
				laser:SetActiveRotation(6, 120, d.phase == 3 and 1.7 or 1.25, false)
				laser.DepthOffset = 50
			end
			fx("laser", SoundEffect.SOUND_DOGMA_LIGHT_RAY_FIRE, 1.2, 1, true)
			game:ShakeScreen(20)
		end
		if t > 40 and t % 20 == 0 and d.phase >= 2 then ring(npc, 10, 4, t, STAR, 0.9) end
		return t >= 145
	end

	function ATTACK.hole(npc, d, t)
		if t == 0 then
			local room = game:GetRoom()
			local p = nearestPlayer(npc.Position)
			local pos
			for _ = 1, 20 do
				pos = room:GetRandomPosition(60)
				if pos:Distance(p.Position) > 140 then break end
			end
			local e = Isaac.Spawn(EntityType.ENTITY_EFFECT, HOLE, 0, pos, Vector.Zero, npc)
			e:GetData().altarLife = d.phase == 3 and 240 or 180
			e.Color = d.phase == 3 and Color(1, 0.6, 0.4, 1, 0.4, 0.1, 0) or Color(0.9, 0.8, 1, 1, 0.2, 0.1, 0.4)
			e.SpriteScale = Vector(0.05, 0.05)
			fx("blackhole", SoundEffect.SOUND_HELL_PORTAL1, 1.2, 1)
		end
		if t % 24 == 12 then ring(npc, 14, 4, t * 7, TINT[d.phase], 0.9) end
		return t >= 72
	end

	function ATTACK.summon(npc, d, t)
		if t == 0 then
			for i = 0, 4 do
				Isaac.Spawn(EntityType.ENTITY_ATTACKFLY, 0, 0, npc.Position + Vector.FromAngle(i * 72):Resized(50), Vector.Zero, npc)
			end
			playSound(SoundEffect.SOUND_MONSTER_ROAR_2, 1, 0.6)
			d.summonCd = 500
		end
		return t >= 30
	end

	-- Form II+: the wings fire fans of feathers from both sides
	function ATTACK.feathers(npc, d, t)
		if t % 9 == 0 and t < 72 then
			local p = nearestPlayer(npc.Position)
			for side = -1, 1, 2 do
				local origin = npc.Position + Vector(side * 40, -20)
				local dir = (p.Position - origin):Normalized()
				for k = -2, 2 do
					shoot(npc, origin, dir:Rotated(k * 9 + side * (t % 18)):Resized(8.5), FEATHER, 0.8, "feather")
				end
			end
			fx("feathers", SoundEffect.SOUND_BIRD_FLAP, 0.9, 1)
		end
		return t >= 80
	end

	-- Form II+: judgement beams strike where you are (and where you're going)
	function ATTACK.pillars(npc, d, t)
		local count = d.phase == 3 and 10 or 7
		if t % 10 == 0 and t < count * 10 then
			local p = nearestPlayer(npc.Position)
			local lead = (t / 12) % 2 == 0 and 0 or 14
			local pos = game:GetRoom():GetClampedPosition(p.Position + p.Velocity * lead + RandomVector() * math.random(0, 30), 20)
			pillars[#pillars + 1] = { pos = pos, t = 0, delay = 30, src = npc }
			playSound(SoundEffect.SOUND_LIGHTBOLT_CHARGE, 0.6, 1.2)
		end
		return t >= count * 10 + 30
	end

	function ATTACK.dash(npc, d, t)
		d.trail = true
		if t == 0 then
			local p = nearestPlayer(npc.Position)
			d.dashDir = (p.Position - npc.Position):Normalized()
			playSound(SoundEffect.SOUND_MONSTER_ROAR_0, 1, 0.5)
		end
		if t < 16 then
			npc.Velocity = npc.Velocity * 0.6
			npc.Color = Color(1, 1, 1, 1, (t % 6 < 3) and 0.6 or 0, 0, 0)
		elseif t < 40 then
			npc.Color = Color(1, 1, 1, 1, 0, 0, 0)
			npc.Velocity = d.dashDir * 17
			if t % 2 == 0 then
				shoot(npc, npc.Position, d.dashDir:Rotated(90):Resized(3.5), TINT[3], 0.9)
				shoot(npc, npc.Position, d.dashDir:Rotated(-90):Resized(3.5), TINT[3], 0.9)
			end
		elseif t == 40 then
			ring(npc, 20, 5, 0, STAR)
		end
		if t >= 52 then d.trail = false end
		return t >= 52
	end

	function ATTACK.collapse(npc, d, t)
		local center = game:GetRoom():GetCenterPos()
		d.invuln = t < 150
		d.darken = t < 150 and math.min(1, t / 30) or 0
		if t < 30 then
			npc.Velocity = (center - npc.Position) * 0.15
			play(npc, FORMS[d.phase].charge)
		else
			npc.Velocity = Vector.Zero
		end
		if t == 30 then
			playSound(SoundEffect.SOUND_MEGA_BLAST_START, 1, 0.6)
			game:ShakeScreen(60)
		end
		if t > 30 and t < 120 then
			A.forEachPlayer(function(p) p.Velocity = p.Velocity + (npc.Position - p.Position):Resized(0.6) end)
			if t % 15 == 0 then ring(npc, 12, 3, t * 5, STAR, 0.8) end
		end
		if t == 120 or t == 132 or t == 144 or t == 156 then
			ring(npc, 36, 5 + (t - 120) / 10, t, t % 24 == 0 and TINT[3] or STAR, 1.4)
			Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.SHOCKWAVE, 0, npc.Position, Vector.Zero, npc)
			playSound(SoundEffect.SOUND_EXPLOSION_STRONG, 1, 0.7)
			game:ShakeScreen(25)
		end
		if t == 156 then d.collapseCd = 300 end
		return t >= 175
	end

	-- Form III ultimate: everything outside the safe zone burns
	function ATTACK.supernova(npc, d, t)
		local room = game:GetRoom()
		local center = room:GetCenterPos()
		d.invuln = t < 140
		if t == 0 then
			local p = nearestPlayer(npc.Position)
			local zone
			for _ = 1, 30 do
				zone = room:GetRandomPosition(70)
				if zone:Distance(p.Position) > 120 and zone:Distance(center) > 80 then break end
			end
			nova = { zone = zone, t = 0, len = 140 }
			playSound(SoundEffect.SOUND_SUPERHOLY, 1, 0.6)
		end
		if t < 30 then
			npc.Velocity = (center - npc.Position) * 0.15
		else
			npc.Velocity = Vector.Zero
		end
		play(npc, FORMS[3].charge)
		if t % 20 == 0 and t < 120 then
			playSound(SoundEffect.SOUND_HEARTBEAT_FASTER, 1, 1 + t / 200)
			ring(npc, 10, 3.5, t * 3, STAR, 0.9)
		end
		if t == 140 then
			A.forEachPlayer(function(p)
				if p.Position:Distance(nova.zone) > 40 then hurtPlayer(p, 4, npc) end
			end)
			ring(npc, 48, 7, 0, TINT[3], 1.3)
			fx("supernova", SoundEffect.SOUND_MEGA_BLAST_END, 1.4, 1, true)
			game:ShakeScreen(50)
			d.flash = 1
			d.novaCd = 420
		end
		if t > 140 then nova = nil end
		return t >= 160
	end

	local function startDeath(npc)
		local d = npc:GetData()
		d.dying = true
		d.invuln = true
		d.attack = nil
		d.trail = false
		npc.HitPoints = 1
		npc.Velocity = Vector.Zero
		clearProjectiles()
		pillars, nova = {}, nil
		for _, e in ipairs(Isaac.FindByType(EntityType.ENTITY_LASER)) do e:Remove() end
		for _, e in ipairs(Isaac.FindByType(EntityType.ENTITY_EFFECT, HOLE)) do e:Remove() end
		startMusic(MUSIC_ENDING, nil, 1, 1800)
		if MUSIC_ENDING <= 0 then pcall(function() music:Fadeout(0.004) end) end
		local s = npc:GetSprite()
		s:Play(FORMS[3].charge, true)
		d.fallFrom = npc.Position
		local hole = Isaac.Spawn(EntityType.ENTITY_EFFECT, HOLE, 0, game:GetRoom():GetCenterPos() + Vector(0, -10),
			Vector.Zero, nil)
		hole:GetData().altarDeathHole = true
		hole.SpriteScale = Vector(0.05, 0.05)
		hole.DepthOffset = -100
		deathHole = hole
		startCutscene("death")
		playSound(SoundEffect.SOUND_ULTRA_GREED_DEATH_SCREAM, 1, 0.55)
	end

	function mod:altarOblivionUpdate(npc)
		local d = npc:GetData()
		if not d.altarInit then
			d.altarInit = true
			local p = Isaac.GetPlayer(0)
			local dps = p.Damage * 30 / (p.MaxFireDelay + 1)
			local hp = math.min(1000000, math.max(75000, dps * 480))
			npc.MaxHitPoints = hp
			npc.HitPoints = hp
			npc:AddEntityFlags(EntityFlag.FLAG_NO_STATUS_EFFECTS | EntityFlag.FLAG_NO_KNOCKBACK | EntityFlag.FLAG_NO_PHYSICS_KNOCKBACK)
			npc.GridCollisionClass = EntityGridCollisionClass.GRIDCOLL_NONE
			d.phase, d.cd, d.collapseCd, d.summonCd, d.novaCd = 1, 30, 300, 0, 200
			d.history = {}
			boss = npc
		end

		-- afterimage history for the trail effect
		if npc.FrameCount % 2 == 0 then
			table.insert(d.history, 1, npc.Position)
			if #d.history > 6 then d.history[7] = nil end
		end

		if d.altarCut or d.dying or cs then
			npc.Velocity = Vector.Zero
			return
		end
		local room = game:GetRoom()
		local form = FORMS[d.phase]
		npc.SpriteScale = Vector(form.scale, form.scale)

		local ph = phaseOf(npc)
		if ph > d.phase then
			d.phase = ph
			d.attack, d.tele, d.invuln, d.darken, d.trail = nil, nil, false, 0, false
			pillars, nova = {}, nil
			clearProjectiles()
			startCutscene("phase", { phase = ph, len = math.max(PHASE_LEN, voiceFrames(ph + 4, 0) + 40) })
			say(ph + 4)
			fx("roar", SoundEffect.SOUND_HUSH_ROAR, 1.3, 0.9)
			game:ShakeScreen(40)
			return
		end

		if not d.halfMusic and npc.HitPoints / npc.MaxHitPoints < 0.5 then
			d.halfMusic = true
			startMusic(MUSIC_BATTLE2, nil)
			d.flash = 0.8
			game:ShakeScreen(25)
		end

		d.collapseCd = math.max(0, d.collapseCd - 1)
		d.summonCd = math.max(0, d.summonCd - 1)
		d.novaCd = math.max(0, d.novaCd - 1)
		if d.phase == 3 then d.trail = true end

		-- desperation (under 15% HP): a slow rain of light on top of everything else
		d.desperate = d.phase == 3 and npc.HitPoints / npc.MaxHitPoints < 0.15
		if d.desperate then
			if not d.saidDesperate then
				d.saidDesperate = true
				say(15)
			end
			if npc.FrameCount % 22 == 0 then
				ring(npc, 10, 2.6, npc.FrameCount * 7, STAR, 0.9)
			end
			if npc.FrameCount % 90 == 0 then
				local p = nearestPlayer(npc.Position)
				pillars[#pillars + 1] = { pos = p.Position, t = 0, delay = 28, src = npc }
			end
		end

		-- drift on a figure-eight; faster every form
		local f = npc.FrameCount
		local center = room:GetCenterPos()
		local target = center + Vector(math.cos(f * 0.014) * 160, math.sin(f * 0.028) * 75 - 20)
		local speed = ({ 0.05, 0.07, 0.095 })[d.phase]
		if not d.attack or d.attack == "rings" or d.attack == "barrage" or d.attack == "hole" or d.attack == "orbs"
			or d.attack == "feathers" or d.attack == "pillars" then
			npc.Velocity = npc.Velocity * 0.9 + (target - npc.Position) * speed * 0.3
		end
		npc.Position = room:GetClampedPosition(npc.Position, 30)

		if d.attack then
			local done = ATTACK[d.attack](npc, d, d.at)
			d.at = d.at + 1
			if done then
				d.attack = nil
				d.invuln = false
				d.darken = 0
				d.cd = ({ 20, 12, 5 })[d.phase]
			end
		else
			d.cd = d.cd - 1
			if d.cd <= 0 then
				d.attack = pickAttack(d)
				d.at = 0
				-- big attacks get a voiced taunt, at most one every 10 seconds
				local line = TAUNTS[d.attack]
				if line and not subtitle and npc.FrameCount - (d.lastTaunt or -999) > 300
					and (d.attack == "supernova" or math.random() < 0.5) then
					d.lastTaunt = npc.FrameCount
					say(line)
				end
			end
		end

		local charging = (d.attack == "lasers" and d.at < 40) or (d.attack == "collapse" and d.at < 150)
			or d.attack == "supernova"
		if not charging then play(npc, form.idle) end
	end
	mod:AddCallback(ModCallbacks.MC_NPC_UPDATE, mod.altarOblivionUpdate, OBLIVION)

	local capping = false
	function mod:altarOblivionDamage(ent, amount, flags, source, countdown)
		local npc = ent:ToNPC()
		if not npc or capping then return end
		local d = npc:GetData()
		if d.altarCut or d.invuln or cs then return false end
		local cap = npc.MaxHitPoints * DAMAGE_CAP
		if math.min(amount, cap) >= npc.HitPoints - 1 then
			-- lethal either way: never let the engine kill her and skip the death sequence
			startDeath(npc)
			return false
		end
		if amount > cap then
			-- re-apply the hit at the cap so broken builds can't one-shot it
			capping = true
			npc:TakeDamage(cap, flags, source, countdown)
			capping = false
			amount = cap
			if npc.HitPoints <= 1 and not d.dying then startDeath(npc) end
			return false
		end
		if amount >= npc.HitPoints - 1 then
			startDeath(npc)
			return false
		end
	end
	mod:AddCallback(ModCallbacks.MC_ENTITY_TAKE_DMG, mod.altarOblivionDamage, OBLIVION)

	-- players can't be hurt while a cutscene plays
	function mod:altarCutsceneShield(ent)
		if cs and ent:ToPlayer() then return false end
	end
	mod:AddCallback(ModCallbacks.MC_ENTITY_TAKE_DMG, mod.altarCutsceneShield, EntityType.ENTITY_PLAYER)

	-- Boss black holes: pull the player in, eat their tears, hurt at the core
	function mod:altarOblivionHole(eff)
		local d = eff:GetData()
		if d.altarDeathHole then -- the hole she falls into: only grows, holds, and snaps shut
			local t = (cs and cs.kind == "death") and cs.t or 999
			local s = t < 60 and ease(t / 60) * 2.4 or t < 225 and 2.4 or math.max(0.05, 2.4 * (1 - (t - 225) / 13))
			eff.SpriteScale = Vector(s, s)
			if t >= 240 then eff:Remove() end
			return
		end
		local life, f = d.altarLife or 160, eff.FrameCount
		local s = math.min(1, f / 20, (life - f) / 20) * 1.1
		eff.SpriteScale = Vector(math.max(0.05, s), math.max(0.05, s))
		A.forEachPlayer(function(p)
			local dist = p.Position:Distance(eff.Position)
			if dist < 260 then
				p.Velocity = p.Velocity + (eff.Position - p.Position):Resized(0.85 * (1 - dist / 260) + 0.18)
			end
			if dist < 30 * s then hurtPlayer(p, 2, eff) end
		end)
		for _, t in ipairs(Isaac.FindByType(EntityType.ENTITY_TEAR)) do
			if t.Position:Distance(eff.Position) < 44 * s then t:Die() end
		end
		if f >= life then eff:Remove() end
	end
	mod:AddCallback(ModCallbacks.MC_POST_EFFECT_UPDATE, mod.altarOblivionHole, HOLE)

	-- judgement pillars and the supernova timer tick at game speed
	function mod:altarOblivionEffects()
		for i = #pillars, 1, -1 do
			local pl = pillars[i]
			pl.t = pl.t + 1
			if pl.t == pl.delay then
				A.forEachPlayer(function(p)
					if p.Position:Distance(pl.pos) < 30 then hurtPlayer(p, 2, pl.src) end
				end)
				Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.SHOCKWAVE, 0, pl.pos, Vector.Zero, nil)
				fx("pillar", SoundEffect.SOUND_LIGHTBOLT, 0.9, 1)
				game:ShakeScreen(6)
			end
			if pl.t > pl.delay + 14 then table.remove(pillars, i) end
		end
		if nova then nova.t = nova.t + 1 end
		if wantedMusic then
			if wantedUntil and game:GetFrameCount() > wantedUntil then
				wantedMusic = nil
			elseif music:GetCurrentMusicID() ~= wantedMusic then
				pcall(function()
					music:Play(wantedMusic, wantedVol)
					music:UpdateVolume()
				end)
			end
		end
		if boss and boss:Exists() then
			local d = boss:GetData()
			if d.flash then d.flash = math.max(0, d.flash - 0.06) end
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_UPDATE, mod.altarOblivionEffects)

	-- custom projectile looks: void orbs get a spinning black hole core
	function mod:altarOblivionShotRender(proj, offset)
		local kind = proj:GetData().altarShot
		if kind ~= "orb" and kind ~= "void" then return end
		local pos = Isaac.WorldToScreen(proj.Position + proj.PositionOffset) + (offset or Vector.Zero)
		local s = (kind == "void" and 0.75 or 0.38) * proj.Scale
		orb.Scale = Vector(s, s)
		orb.Color = Color(1, 1, 1, 0.9, 0, 0, 0)
		orb:Render(pos, Vector.Zero, Vector.Zero)
	end
	mod:AddCallback(ModCallbacks.MC_POST_PROJECTILE_RENDER, mod.altarOblivionShotRender)

	-- telegraphs + afterimages, drawn with the boss
	function mod:altarOblivionRender(npc)
		local d = npc:GetData()
		if d.trail and d.history and not d.dying then
			local s = npc:GetSprite()
			local saved = s.Color
			local tint = d.phase == 3 and { 1, 0.4, 0.1 } or d.phase == 2 and { 0.8, 0.8, 1 } or { 0.5, 0.1, 0.9 }
			for k = #d.history, 2, -1 do
				s.Color = Color(1, 1, 1, 0.28 * (1 - k / 7), tint[1], tint[2], tint[3])
				s:Render(Isaac.WorldToScreen(d.history[k]), Vector.Zero, Vector.Zero)
			end
			s.Color = saved
		end
		if d.tele then
			local base = Isaac.WorldToScreen(npc.Position + Vector(0, -30))
			local blink = (npc.FrameCount % 6 < 3) and 0.6 or 0.25
			for _, ang in ipairs(d.tele) do
				local dir = Vector.FromAngle(ang)
				for k = 2, 70 do
					local p = base + dir * (k * 6)
					rect(p.X - 1, p.Y - 1, 2, 2, 1, 0.15, 0.1, blink)
				end
			end
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_NPC_RENDER, mod.altarOblivionRender, OBLIVION)

	---------------------------------------------------------------------------
	-- Cutscene timeline (advanced at 30fps in MC_POST_UPDATE)
	---------------------------------------------------------------------------

	local function giveRewards(pos)
		local room = game:GetRoom()
		local p = Isaac.GetPlayer(0)
		for _ = 1, 3 do A.spawnRandomQ4(p) end
		A.spawnItem(A.ITEM.event_horizon, p)
		Isaac.Spawn(EntityType.ENTITY_PICKUP, PickupVariant.PICKUP_LOCKEDCHEST, 0,
			room:FindFreePickupSpawnPosition(pos, 0, true), Vector.Zero, nil)
		for _ = 1, 25 do
			Isaac.Spawn(EntityType.ENTITY_PICKUP, PickupVariant.PICKUP_COIN, 0, pos, RandomVector() * (3 + math.random() * 5), nil)
		end
	end

	local function endCutscene()
		local kind = cs.kind
		cs = nil
		freezePlayers(false)
		if kind == "intro" and boss then
			boss:GetData().altarCut = false
			boss.Visible = true
			startMusic(MUSIC_BATTLE, Music.MUSIC_VOID_BOSS)
			say(9)
			setArenaAlpha(1)
		end
	end

	local function skipIntro()
		if not cs or cs.kind ~= "intro" then return end
		if cs.t < cs.reveal then
			stopVoices()
			cs.t = cs.reveal
		elseif cs.t < cs.reveal + 240 and cs.t > cs.reveal + 115 then
			cs.t = cs.reveal + 240
		end
	end

	function mod:altarCutsceneUpdate()
		if floor14Check then
			floor14Check = floor14Check - 1
			if floor14Check <= 0 then
				floor14Check = nil
				local room = game:GetRoom()
				if not cs and not (boss and boss:Exists()) and not room:IsClear()
					and #Isaac.FindByType(EntityType.ENTITY_DELIRIUM) > 0 then
					beginIntro()
				end
			end
		end
		if pending then
			-- wait until the teleport has actually landed in the boss room
			pending = pending + 1
			local room = game:GetRoom()
			if room:GetType() == RoomType.ROOM_BOSS and room:GetFrameCount() > 8 then
				pending = nil
				beginIntro()
			elseif pending > 300 then
				pending = nil
			end
			return
		end
		if subtitle then
			subtitle.t0 = subtitle.t0 + 1
			if subtitle.t0 > subtitle.frames + 45 then
				subtitle = nil
				duck(false)
			end
		end
		if not cs then return end
		local t = cs.t
		cs.t = t + 1

		if cs.kind == "intro" then
			for _, seg in ipairs(cs.segs) do
				if t == seg.start + 12 then say(seg.line) end
				if t == seg.start then playSound(SoundEffect.SOUND_PAPER_IN, 0.3, 0.6) end
			end
			local r = t - cs.reveal
			if r >= 0 then setArenaAlpha(r / 110) end
			if r == 0 then
				stopVoices()
				playSound(SoundEffect.SOUND_DOGMA_LIGHT_RAY_CHARGE, 1, 0.6)
			end
			if r > 0 and r < 110 and r % 10 == 0 then game:ShakeScreen(math.floor(r / 8)) end
			if r == 110 then
				local npc = spawnBoss()
				npc.Visible = true
				fx("transform", SoundEffect.SOUND_SATAN_GROW, 1.2, 0.8)
				fx("roar", SoundEffect.SOUND_HUSH_ROAR, 1.4, 1, true)
				game:ShakeScreen(40)
				npc:GetSprite():Play(FORMS[1].charge, true)
			end
			if r == 140 then playSound(SoundEffect.SOUND_MEGA_BLAST_END, 0.8, 0.5) end
			if t >= cs.len then endCutscene() end
		elseif cs.kind == "phase" then
			if boss then
				boss.Velocity = Vector.Zero
				play(boss, FORMS[cs.phase - 1].charge)
				if t >= 50 then play(boss, FORMS[cs.phase].charge) end
			end
			if t == 50 and boss then
				boss.SpriteScale = Vector(FORMS[cs.phase].scale, FORMS[cs.phase].scale)
				ring(boss, 40, 7, 0, STAR, 1.3)
				Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.SHOCKWAVE, 0, boss.Position, Vector.Zero, nil)
				fx("transform", SoundEffect.SOUND_SUPERHOLY, 1.3, 1, true)
				game:ShakeScreen(35)
			end
			if t >= cs.len then endCutscene() end
		elseif cs.kind == "death" then
			local pos = (deathHole and deathHole:Exists()) and deathHole.Position or game:GetRoom():GetCenterPos()
			if t == 20 then say(8) end
			if t == 40 then fx("blackhole", SoundEffect.SOUND_HELL_PORTAL1, 1.4, 0.8, true) end
			-- she spirals into the black hole, stretched toward it and darkening
			if boss and t >= 40 and t < 225 then
				local k = (t - 40) / 185
				local e = k * k
				local start = boss:GetData().fallFrom or boss.Position
				local r0 = start:Distance(pos)
				local a0 = math.deg(math.atan(start.Y - pos.Y, start.X - pos.X))
				local ang = a0 + e * 900
				boss.Position = pos + Vector.FromAngle(ang):Resized(math.max(0.1, r0 * (1 - e)))
				boss.Velocity = Vector.Zero
				local sc = FORMS[3].scale * (1 - e * 0.95)
				boss.SpriteScale = Vector(sc * (1 - 0.5 * e), sc * (1 + 0.9 * e))
				boss.SpriteRotation = ang + 90
				boss.Color = Color(1 - e * 0.8, 1 - e * 0.8, 1 - e * 0.6, 1, e * 0.3, 0, e * 0.5)
				if t % 6 == 0 then
					for _ = 1, 3 do
						local mote = Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.EMBER_PARTICLE, 0,
							boss.Position + RandomVector() * 20, (pos - boss.Position):Resized(3), nil)
						mote.Color = Color(1, 0.8, 0.6, 1, 0.5, 0.3, 0.1)
					end
				end
				if t % 10 == 0 then game:ShakeScreen(4 + math.floor(e * 14)) end
			end
			if t == 225 and boss then boss.Visible = false end
			if t == 238 then -- the hole snaps shut
				local e = Isaac.Spawn(EntityType.ENTITY_EFFECT, SINGULARITY, 0, pos, Vector.Zero, nil)
				e.SpriteScale = Vector(3, 3)
				Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.SHOCKWAVE, 0, pos, Vector.Zero, nil)
				fx("implosion", SoundEffect.SOUND_MEGA_BLAST_END, 1.5, 1, true)
				game:ShakeScreen(60)
			end
			if t == 245 and boss then
				boss.Visible = false
				local d = boss:GetData()
				d.invuln, d.altarCut = false, true
				boss:Kill()
				boss = nil
				giveRewards(pos)
				if A.toast then A.toast("Oblivion defeated") end
			end
			if t > 250 then setArenaAlpha(1 - (t - 250) / 60) end
			if t >= DEATH_LEN then endCutscene() end
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_UPDATE, mod.altarCutsceneUpdate)

	local saidPlayerDeath = false
	function mod:altarCutsceneFreeze(p)
		if cs and cs.kind ~= "phase" then p.ControlsEnabled = false end
		-- she gets the last word if she kills you
		if boss and boss:Exists() and p:IsDead() and not saidPlayerDeath then
			saidPlayerDeath = true
			say(16)
		end
		if not (boss and boss:Exists()) then saidPlayerDeath = false end
	end
	mod:AddCallback(ModCallbacks.MC_POST_PLAYER_UPDATE, mod.altarCutsceneFreeze)

	function mod:altarCutsceneNewRoom()
		if cs and cs.kind ~= "death" then
			cs = nil
			stopVoices()
			freezePlayers(false)
		end
		pillars, nova = {}, nil
		if boss and not boss:Exists() then boss = nil end
		arena, deathHole = nil, nil
		wantedMusic = nil -- leaving the fight hands the music back to the game
		if A.floor14 then
			-- the Void's walls swapped for the starfield backdrop: a sky that fell
			pcall(function()
				game:ShowHallucination(0, BackdropType.PLANETARIUM)
				sfx:Stop(SoundEffect.SOUND_DEATH_CARD) -- ShowHallucination's own sound
			end)
			spawnArena(0.9)
			floor14Check = 6 -- look for Delirium once the room has spawned its enemies
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_NEW_ROOM, mod.altarCutsceneNewRoom)

	---------------------------------------------------------------------------
	-- Rendering
	---------------------------------------------------------------------------

	local BAR = 34 -- letterbox height

	local function letterbox(W, H, k)
		local bar = math.floor(BAR * ease(k))
		rect(0, 0, W, bar, 0, 0, 0, 1)
		rect(0, H - bar, W, bar, 0, 0, 0, 1)
	end

	-- subtitles sit centred in the bottom letterbox bar, or above the HP bar when there is none
	local function drawSubtitle(W, H, inBar)
		if not subtitle then return end
		local v = VOICE[subtitle.line]
		if not v then return end
		local reveal = clamp(subtitle.t0 / math.max(30, subtitle.frames * 0.85))
		local shown = v.text:sub(1, math.floor(#v.text * reveal + 0.5))
		local a = clamp(math.min(subtitle.t0 / 8, (subtitle.frames + 45 - subtitle.t0) / 15))
		local y = inBar and (H - BAR + math.floor((BAR - lineH(fText)) / 2)) or (H - 58)
		if not inBar then
			local w = fText:GetStringWidth(v.text) + 16
			rect((W - w) / 2, y - 3, w, lineH(fText) + 6, 0, 0, 0, 0.55 * a)
		end
		textC(fText, shown, y, 1, 0.95, 0.85, a, 1)
	end

	local function renderStars(cx, cy, strength)
		if #stars < 90 then
			for _ = 1, 3 do
				stars[#stars + 1] = { a = math.random() * math.pi * 2, d = 160 + math.random() * 200, s = 1 + math.random() * 3 }
			end
		end
		for _, s in ipairs(stars) do
			s.d = s.d - s.s * (1 + strength * 4)
			if s.d < 8 then s.d = 160 + math.random() * 200 end
			local x, y = cx + math.cos(s.a) * s.d, cy + math.sin(s.a) * s.d * 0.7
			local len = 2 + strength * 6
			for k = 0, len do
				rect(x + math.cos(s.a) * k * 1.5, y + math.sin(s.a) * k, 1, 1, 0.9, 0.8, 1, 0.8 * (1 - k / len))
			end
		end
	end

	local function nameCard(W, t, title, sub, r, g, b)
		local inT = ease(t / 25)
		local outT = clamp((95 - t) / 15)
		local a = math.min(inT, outT)
		-- band just under the letterbox bar, clear of the boss; title + subtitle centred in it
		local top, bandH = BAR + 4, 48
		local th, sh = lineH(fBig), lineH(fText)
		local ty = top + math.floor((bandH - th - sh - 2) / 2)
		rect(0, top, W, bandH, 0, 0, 0, 0.75 * a)
		rect(W * (1 - inT), top, W, 1, r, g, b, a)
		rect(0, top + bandH - 1, W * inT, 1, r, g, b, a)
		local slide = (1 - inT) * 120
		local w = fBig:GetStringWidth(title)
		fBig:DrawStringScaled(title, math.floor((W - w) / 2 + slide), ty, 1, 1, KColor(r, g, b, a), 0, false)
		local sw = fText:GetStringWidth(sub)
		fText:DrawString(sub, math.floor((W - sw) / 2 - slide), ty + th + 2, KColor(0.9, 0.85, 1, a), 0, false)
	end

	-- one flipbook panel with a slow Ken Burns push
	local function drawPanel(seg, t, W, H, a)
		local s = panels[seg.panel]
		if not s or a <= 0 then return end
		local k = clamp((t - seg.start) / seg.dur)
		if FLIP_SYNC[seg.panel] then
			s:SetFrame("Play", math.floor(k * (FLIP_FRAMES - 1)))
		else
			s:SetFrame("Play", (t - seg.start) % FLIP_FRAMES)
		end
		local scale = 1.0 + 0.07 * k
		local drift = (seg.panel % 2 == 0 and -1 or 1) * 10 * k
		local cx, cy = W / 2 + drift, H / 2 - 4
		s.Scale = Vector(scale, scale)
		s.Color = Color(1, 1, 1, a, 0, 0, 0)
		s:Render(Vector(cx, cy), Vector.Zero, Vector.Zero)
	end

	local BAR_COLORS = {
		{ 0.62, 0.34, 1.0 }, -- Form I: violet
		{ 0.88, 0.86, 1.0 }, -- Form II: seraph white
		{ 1.0, 0.45, 0.18 }, -- Form III: burning gold-crimson
	}

	-- Altar's own boss bar: name plate, form notches, white damage trail, hit flash
	local function drawHpBar(W, H, d)
		local ratio = clamp(boss.HitPoints / boss.MaxHitPoints)
		if ratio < bar.last - 0.0005 then bar.hit = 1 end
		bar.last = ratio
		bar.trail = bar.trail > ratio and math.max(ratio, bar.trail - 0.0035) or ratio
		bar.hit = math.max(0, bar.hit - 0.1)
		bar.shown = math.min(1, bar.shown + 0.03)
		local e = ease(bar.shown)
		local bw, bh = math.floor(270 * e), 8
		local x, y = math.floor((W - bw) / 2), H - 20
		local c = BAR_COLORS[d.phase or 1]
		local pulse = 0.5 + 0.5 * math.sin(Isaac.GetFrameCount() / 10)

		local lh = lineH(fText)
		local form = FORMS[d.phase or 1]
		if d.desperate and (Isaac.GetFrameCount() // 20) % 2 == 0 then c = { 1, 1, 1 } end
		fText:DrawString("OBLIVION", x + 1, y - lh - 1, KColor(0, 0, 0, 0.8 * e), 0, false)
		fText:DrawString("OBLIVION", x, y - lh - 2, KColor(1, 0.92, 0.75, e), 0, false)
		local sub = form.title .. "  " .. form.sub
		local sw = fText:GetStringWidth(sub)
		fText:DrawString(sub, x + bw - sw, y - lh - 2, KColor(c[1], c[2], c[3], 0.85 * e), 0, false)

		rect(x - 3, y - 3, bw + 6, bh + 6, 0, 0, 0, 0.85 * e)
		rect(x - 2, y - 2, bw + 4, 1, 0.85, 0.7, 0.4, e)
		rect(x - 2, y + bh + 1, bw + 4, 1, 0.85, 0.7, 0.4, e)
		rect(x - 2, y - 2, 1, bh + 4, 0.85, 0.7, 0.4, e)
		rect(x + bw + 1, y - 2, 1, bh + 4, 0.85, 0.7, 0.4, e)
		rect(x, y, bw, bh, 0.08, 0.04, 0.12, e)
		rect(x, y, bw * bar.trail, bh, 1, 1, 1, 0.65 * e)
		rect(x, y, bw * ratio, bh, c[1], c[2], c[3], e)
		rect(x, y, bw * ratio, 2, 1, 1, 1, (0.25 + 0.15 * pulse) * e)
		rect(x, y + bh - 2, bw * ratio, 2, 0, 0, 0, 0.3 * e)
		if bar.hit > 0 then rect(x, y, bw * ratio, bh, 1, 1, 1, bar.hit * 0.5) end
		for _, k in ipairs({ 0.66, 0.33 }) do -- form notches
			rect(x + bw * k, y - 3, 1, bh + 6, 1, 0.85, 0.5, e)
			rect(x + bw * k - 1, y - 4, 3, 1, 1, 0.85, 0.5, e)
		end
		rect(x + bw * ratio - 1, y - 1, 2, bh + 2, 1, 1, 1, (0.4 + 0.4 * pulse) * e)
	end

	local function renderCombatFx(W, H)
		if not (boss and boss:Exists()) then return end
		local d = boss:GetData()
		if d.darken and d.darken > 0 then rect(0, 0, W, H, 0, 0, 0, 0.55 * d.darken) end
		if d.phase == 3 and not cs then -- Form III: pulsing ember vignette
			local p = 0.12 + 0.08 * math.sin(Isaac.GetFrameCount() / 12)
			for i = 0, 5 do
				local a = p * (1 - i / 6)
				rect(0, i * 4, W, 4, 1, 0.25, 0.05, a)
				rect(0, H - (i + 1) * 4, W, 4, 1, 0.25, 0.05, a)
				rect(i * 4, 0, 4, H, 1, 0.25, 0.05, a)
				rect(W - (i + 1) * 4, 0, 4, H, 1, 0.25, 0.05, a)
			end
		end
		-- judgement pillars: shrinking target ring, then a beam of light
		for _, pl in ipairs(pillars) do
			local sp = Isaac.WorldToScreen(pl.pos)
			if pl.t < pl.delay then
				local k = pl.t / pl.delay
				circle(sp.X, sp.Y, 34 - 16 * k, 1, 0.95, 0.6, 0.4 + 0.5 * k)
				circle(sp.X, sp.Y, 14, 1, 1, 1, 0.3 + 0.4 * ((pl.t % 6 < 3) and 1 or 0))
			else
				local k = 1 - (pl.t - pl.delay) / 14
				rect(sp.X - 9 * k, 0, 18 * k, sp.Y, 1, 0.95, 0.75, 0.85 * k)
				rect(sp.X - 3 * k, 0, 6 * k, sp.Y, 1, 1, 1, k)
				circle(sp.X, sp.Y, 26 * (2 - k), 1, 0.9, 0.6, k)
			end
		end
		-- supernova: the room fills with light except the safe zone
		if nova then
			local zp = Isaac.WorldToScreen(nova.zone)
			local k = clamp(nova.t / nova.len)
			rect(0, 0, W, H, 1, 0.85, 0.6, 0.25 * k)
			circle(zp.X, zp.Y, 48 * 0.75 + 4, 0.4, 1, 1, 0.9, 3)
			circle(zp.X, zp.Y, 48 * 0.75 - 2 + math.sin(nova.t / 4) * 2, 1, 1, 1, 0.6)
			if (nova.t // 15) % 2 == 0 then
				textC(fText, "GET TO THE LIGHT", 48, 0.5, 1, 1, 0.9, 1)
			end
		end
		if d.flash and d.flash > 0 then rect(0, 0, W, H, 1, 1, 0.9, d.flash) end
		if boss.Visible and not d.dying and (not cs or cs.kind == "phase") then drawHpBar(W, H, d) end
	end

	function mod:altarCutsceneRender()
		local W, H = Isaac.GetScreenWidth(), Isaac.GetScreenHeight()
		renderCombatFx(W, H)
		if not cs then
			drawSubtitle(W, H, false)
			return
		end
		local t = cs.t

		if cs.kind == "intro" then
			local r = t - cs.reveal
			if r < 0 then
				-- story: black screen, illustrated panels
				rect(0, 0, W, H, 0, 0, 0, math.min(1, t / 40))
				for _, seg in ipairs(cs.segs) do
					local a = clamp(math.min((t - seg.start) / 20, (seg.start + seg.dur - t) / 20))
					if t >= seg.start - 1 and t <= seg.start + seg.dur then drawPanel(seg, t, W, H, a) end
				end
			else
				local dark = 1 - math.min(0.15, r / 40)
				if r > 110 then dark = math.max(0.35, 0.85 - (r - 110) / 60) end
				if t > cs.len - 30 then dark = dark * (cs.len - t) / 30 end
				rect(0, 0, W, H, 0, 0, 0, dark)
				local c = Isaac.WorldToScreen(game:GetRoom():GetCenterPos() + Vector(0, -40))
				if r < 130 then
					local g = ease(r / 100)
					renderStars(c.X, c.Y, g)
					hole.Scale = Vector(g * 1.8, g * 1.8)
					hole.Color = Color(1, 1, 1, r > 110 and (130 - r) / 20 or 1, 0, 0, 0)
					hole:Render(c, Vector.Zero, Vector.Zero)
					hole:Update()
				end
				if r >= 110 and r < 140 then rect(0, 0, W, H, 1, 1, 1, 1 - (r - 110) / 30) end
				if r >= 140 and r < 240 then nameCard(W, r - 140, "OBLIVION", "DEVOURER OF STARS", 0.75, 0.5, 1) end
			end
			letterbox(W, H, math.min(t / 30, (cs.len - t) / 30))
			drawSubtitle(W, H, true)
			if t < cs.len - 40 then
				local skip = "ENTER to skip"
				fText:DrawString(skip, W - fText:GetStringWidth(skip) - 10, math.floor((BAR - lineH(fText)) / 2),
					KColor(0.6, 0.6, 0.7, 0.6), 0, false)
				if Input.IsButtonPressed(Keyboard.KEY_ENTER, 0) and t > 20 and not cs.enterHeld then skipIntro() end
				cs.enterHeld = Input.IsButtonPressed(Keyboard.KEY_ENTER, 0)
			end
		elseif cs.kind == "phase" then
			local flash = clamp(1 - math.abs(t - 50) / 14)
			rect(0, 0, W, H, 1, 0.9, 0.8, flash * 0.8)
			rect(0, 0, W, H, 0, 0, 0, 0.35 * clamp(math.min(t / 10, (cs.len - t) / 15)))
			local form = FORMS[cs.phase]
			if t > 45 then
				nameCard(W, math.min((t - 45) * 1.2, 95), form.title, form.sub, 1, cs.phase == 3 and 0.55 or 0.85, cs.phase == 3 and 0.3 or 1)
			end
			drawSubtitle(W, H, false)
		elseif cs.kind == "death" then
			letterbox(W, H, math.min(t / 30, (DEATH_LEN - t) / 30))
			drawSubtitle(W, H, true)
			if t >= 238 and t < 288 then rect(0, 0, W, H, 1, 1, 1, 1 - (t - 238) / 50) end
			if t >= 250 then
				local a = clamp(math.min((t - 250) / 20, (DEATH_LEN - t) / 20))
				textC(fBig, "OBLIVION HAS FALLEN", H * 0.3, 1, 0.85, 0.4, a, 1)
				textC(fText, "The stars return. Take what she swallowed.", H * 0.3 + 28, 0.9, 0.85, 1, a, 1)
			end
			rect(0, 0, W, H, 0, 0, 0, 0.25 * math.sin(t / DEATH_LEN * math.pi))
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_RENDER, mod.altarCutsceneRender)
end
