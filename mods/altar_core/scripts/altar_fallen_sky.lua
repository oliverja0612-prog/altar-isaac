-- Fallen Sky items: eight items in Oblivion's star-and-void style, plus the pickup
-- burst every Altar item gets. Art: AltarModManager/tools/make_sprites.py.
return function(A)
	local mod, game, sfx, ITEM = A.mod, A.game, A.sfx, A.ITEM

	local function has(p, key) return (ITEM[key] or -1) > 0 and p:HasCollectible(ITEM[key]) end
	-- Fallen Sky combos are listed in altar_combos.lua (loaded after this file)
	local function combo(p, key) return A.hasCombo ~= nil and A.COMBO_BY_KEY[key] ~= nil and A.hasCombo(p, key) end
	local SINGULARITY = Isaac.GetEntityVariantByName("Altar Singularity")
	local function num(p, key) return (ITEM[key] or -1) > 0 and p:GetCollectibleNum(ITEM[key]) or 0 end

	local function enemiesNear(pos, radius)
		local out = {}
		for _, e in ipairs(Isaac.FindInRadius(pos, radius, EntityPartition.ENEMY)) do
			if e:IsVulnerableEnemy() then out[#out + 1] = e end
		end
		return out
	end

	local function nearestEnemy(pos)
		local best, bestD
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			if e:IsVulnerableEnemy() and e:IsActiveEnemy(false) then
				local d = e.Position:Distance(pos)
				if not bestD or d < bestD then best, bestD = e, d end
			end
		end
		return best
	end

	local function fx(variant, pos, vel, color, scale)
		local e = Isaac.Spawn(EntityType.ENTITY_EFFECT, variant, 0, pos, vel or Vector.Zero, nil)
		if color then e.Color = color end
		if scale then e.SpriteScale = Vector(scale, scale) end
		return e
	end

	-- screen-space drawing (same 4x4 white pixel the boss cutscenes use)
	local px = Sprite()
	px:Load("gfx/altar/altar_pixel.anm2", true)
	px:Play("Idle", true)
	local function rect(x, y, w, h, r, g, b, a)
		if w <= 0 or h <= 0 or a <= 0 then return end
		px.Scale = Vector(w / 4, h / 4)
		px.Color = Color(r, g, b, a, 0, 0, 0)
		px:Render(Vector(math.floor(x), math.floor(y)), Vector.Zero, Vector.Zero)
	end
	local function circle(cx, cy, radius, r, g, b, a)
		local n = math.max(20, math.floor(radius * 1.4))
		for i = 0, n - 1 do
			local ang = i / n * math.pi * 2
			rect(cx + math.cos(ang) * radius - 1, cy + math.sin(ang) * radius * 0.75 - 1, 2, 2, r, g, b, a)
		end
	end

	local flashes = {} -- full-screen flashes: { r, g, b, a, decay }
	local function flash(r, g, b, a, decay) flashes[#flashes + 1] = { r, g, b, a, decay or 0.05 } end

	---------------------------------------------------------------------------
	-- Every Altar item announces itself: a burst in its own colour on pickup
	---------------------------------------------------------------------------

	local GLOW = {
		cosmic_overclock = { 0, 0.95, 1 }, black_hole_core = { 1, 0.66, 0.31 }, midas_engine = { 1, 0.85, 0.2 },
		glitched_crown = { 0.3, 1, 0.6 }, shatter_drive = { 0.7, 0.9, 1 }, debug_die = { 0.3, 1, 0.4 },
		supernova_heart = { 1, 0.45, 0.2 }, quantum_tears = { 0.4, 0.9, 1 }, phoenix_feather = { 1, 0.5, 0.15 },
		storm_core = { 1, 1, 0.4 }, vampire_fang = { 0.9, 0.1, 0.15 }, frost_nova = { 0.6, 0.9, 1 },
		inferno_halo = { 1, 0.55, 0.15 }, titan_blood = { 0.85, 0.15, 0.2 }, mirror_shard = { 0.85, 0.9, 1 },
		fourfold_clover = { 0.35, 1, 0.4 }, bullet_hell = { 1, 0.75, 0.3 }, colossus_tears = { 0.4, 0.6, 1 },
		toxic_core = { 0.5, 1, 0.3 }, satellite_beam = { 0.9, 0.3, 0.3 }, chronos_gear = { 1, 0.85, 0.5 },
		blast_heart = { 1, 0.4, 0.2 }, phantom_step = { 0.8, 0.8, 1 }, chaos_prism = { 1, 0.5, 1 },
		overcharger = { 0.4, 1, 0.5 }, ascension_sigil = { 1, 0.95, 0.6 }, nuke_button = { 1, 0.25, 0.2 },
		wormhole_key = { 0.7, 0.4, 1 }, balance_glove = { 0.75, 0.55, 1 }, seraph_bell = { 1, 0.95, 0.65 },
		treasure_geyser = { 1, 0.85, 0.25 }, event_horizon = { 0.75, 0.5, 1 },
		fallen_star = { 1, 0.86, 0.47 }, still_sky = { 0.67, 0.75, 1 }, oblivion_eye = { 0.75, 0.5, 1 },
		seraph_wings = { 0.95, 0.95, 1 }, nebula_heart = { 1, 0.47, 0.86 }, comet_tail = { 0.47, 0.78, 1 },
		rift_shard = { 0.86, 0.43, 1 }, dying_star = { 1, 0.47, 0.16 },
	}
	A.ITEM_GLOW = GLOW

	function mod:altarPickupBurst(p)
		local d = p:GetData()
		d.altarSeen = d.altarSeen or {}
		for _, info in ipairs(A.DATA) do
			local n = info.id > 0 and p:GetCollectibleNum(info.id) or 0
			local before = d.altarSeen[info.key]
			if before and n > before then
				local c = GLOW[info.key] or { 1, 1, 1 }
				A.burst(p.Position, c[1], c[2], c[3], 16, 6)
				A.flashFx(p.Position, c[1], c[2], c[3], 2.5, 18)
				flash(c[1], c[2], c[3], 0.3, 0.03)
				sfx:Play(SoundEffect.SOUND_HOLY, 0.5, 0, false, 1.3)
				if info.key == "nebula_heart" then
					p:AddMaxHearts(2)
					p:AddHearts(2)
				end
			end
			d.altarSeen[info.key] = n
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_PEFFECT_UPDATE, mod.altarPickupBurst)

	---------------------------------------------------------------------------
	-- Stats
	---------------------------------------------------------------------------

	function mod:altarSkyCache(p, flag)
		if flag == CacheFlag.CACHE_SPEED then
			p.MoveSpeed = p.MoveSpeed + 0.2 * num(p, "seraph_wings") + 0.3 * num(p, "comet_tail")
		elseif flag == CacheFlag.CACHE_FLYING then
			if has(p, "seraph_wings") then p.CanFly = true end
		end
	end
	mod:AddCallback(ModCallbacks.MC_EVALUATE_CACHE, mod.altarSkyCache)

	---------------------------------------------------------------------------
	-- Fallen Star: every 4th tear calls a star down on the nearest enemy
	---------------------------------------------------------------------------

	local falling = {} -- { pos, t, delay, dmg, owner }
	local STAR_DELAY = 20

	local function callStar(p, pos)
		falling[#falling + 1] = { pos = pos, t = 0, delay = STAR_DELAY, dmg = 6 + p.Damage * 3, owner = p }
		-- Meteor Shower: every star brings two more
		if combo(p, "meteor_shower") then
			for k = 1, 2 do
				local spot = game:GetRoom():GetClampedPosition(pos + RandomVector() * (30 + math.random() * 40), 10)
				falling[#falling + 1] = { pos = spot, t = -6 * k, delay = STAR_DELAY, dmg = 4 + p.Damage * 2, owner = p }
			end
		end
		sfx:Play(SoundEffect.SOUND_ANGEL_WING, 0.35, 0, false, 1.6)
	end

	-- tears this file fires itself re-enter MC_POST_FIRE_TEAR straight away (before any
	-- GetData mark can be set), so a flag stops them triggering more feathers forever
	local firing = false

	local function feather(p, pos, vel)
		firing = true
		local f = p:FireTear(pos, vel, false, true, false)
		firing = false
		f:GetData().altarFeather = true
		f.TearFlags = f.TearFlags | TearFlags.TEAR_SPECTRAL | TearFlags.TEAR_LIGHT_FROM_HEAVEN
		f.Color = Color(1, 1, 1, 1, 0.75, 0.75, 0.8)
		return f
	end

	-- Seraph Wings / Rift Shard hook into firing too
	function mod:altarSkyFire(tear)
		local p = tear.SpawnerEntity and tear.SpawnerEntity:ToPlayer()
		if not p or firing or tear:GetData().altarFeather then return end
		local d = p:GetData()
		d.altarSkyShots = (d.altarSkyShots or 0) + 1 -- own counter: altar_combos.lua counts d.altarShots

		if has(p, "fallen_star") and d.altarSkyShots % 4 == 0 then
			local target = nearestEnemy(p.Position)
			if target then callStar(p, target.Position) end
		end

		if has(p, "seraph_wings") and d.altarSkyShots % 3 == 0 then
			for _, ang in ipairs({ -25, 25 }) do
				local f = feather(p, tear.Position, tear.Velocity:Rotated(ang))
				f.Scale = f.Scale * 0.85
			end
		end

		local riftChance = (0.07 + math.max(0, p.Luck) * 0.012) * (combo(p, "nebula_rift") and 2 or 1)
		if has(p, "rift_shard") and math.random() < riftChance then
			tear:GetData().altarRift = p
			tear.Color = Color(0.6, 0.2, 1, 1, 0.35, 0, 0.55)
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_FIRE_TEAR, mod.altarSkyFire)

	local function updateStars()
		for i = #falling, 1, -1 do
			local s = falling[i]
			s.t = s.t + 1
			if s.t == s.delay then
				local owner = s.owner
				for _, e in ipairs(enemiesNear(s.pos, 60)) do
					e:TakeDamage(s.dmg, DamageFlag.DAMAGE_EXPLOSION, EntityRef(owner), 0)
				end
				A.flashFx(s.pos, 1, 0.9, 0.6, 2.8, 16)
				fx(EffectVariant.CRACKED_ORB_POOF, s.pos, nil, Color(1, 0.9, 0.5, 1, 0.6, 0.5, 0.2))
				A.burst(s.pos, 1, 0.85, 0.45, 12, 5)
				fx(EffectVariant.PLAYER_CREEP_HOLYWATER, s.pos, nil, Color(1, 0.9, 0.5, 0.7, 0.4, 0.3, 0), 1.2).CollisionDamage = 0
				game:ShakeScreen(5)
				sfx:Play(SoundEffect.SOUND_LIGHTBOLT, 0.6, 0, false, 1.2)
			end
			if s.t > s.delay + 12 then table.remove(falling, i) end
		end
	end

	local function renderStars()
		for _, s in ipairs(falling) do
			local sp = Isaac.WorldToScreen(s.pos)
			if s.t < s.delay then
				local k = math.max(0, s.t) / s.delay -- Meteor Shower stars start below 0
				circle(sp.X, sp.Y, 24 - 10 * k, 1, 0.9, 0.6, 0.3 + 0.5 * k)
				-- the star streaks in from the top-left, accelerating
				local e = k * k
				local hx, hy = sp.X - 140 * (1 - e), sp.Y - 260 * (1 - e)
				for j = 0, 12 do
					rect(hx + j * 140 / 260 * 4 * -1, hy - j * 4, 3 - j // 5, 3 - j // 5, 1, 0.95 - j * 0.03, 0.8 - j * 0.04, 0.9 * (1 - j / 13))
				end
				A.drawGlow(Vector(hx, hy), 0.55, 1, 0.9, 0.6, 0.85)
				rect(hx - 2, hy - 2, 5, 5, 1, 1, 1, 1)
			else
				local k = (s.t - s.delay) / 12
				A.drawGlow(sp, 1.8 * (1 - k) + 0.4, 1, 0.85, 0.5, 0.8 * (1 - k))
				circle(sp.X, sp.Y, 20 + 50 * k, 1, 0.85, 0.5, 0.8 * (1 - k))
			end
		end
	end

	---------------------------------------------------------------------------
	-- Rift Shard: a tear tears open a void beam across the room, both ways
	---------------------------------------------------------------------------

	function mod:altarRiftTear(tear)
		local p = tear:GetData().altarRift
		if not p or not p:Exists() then return end
		-- player-fired lasers: EntityLaser.ShootAngle makes enemy lasers that hit you too
		local ang = math.random(0, 179)
		local room = game:GetRoom()
		for _, a in ipairs({ ang, ang + 180 }) do
			local laser = p:FireTechLaser(tear.Position, LaserOffset.LASER_TECH1_OFFSET, Vector.FromAngle(a), false, false, p, 1.5)
			laser.Color = Color(0.5, 0.15, 1, 1, 0.35, 0, 0.6)
			laser:GetData().altarFriendly = true
			-- Nebula Rift: the beam leaves a line of nebula clouds
			if combo(p, "nebula_rift") then
				for k = 1, 12 do
					local spot = tear.Position + Vector.FromAngle(a):Resized(k * 40)
					if not room:IsPositionInRoom(spot, 0) then break end
					local cloud = fx(EffectVariant.PLAYER_CREEP_RED, spot, nil, Color(0.85, 0.35, 1, 0.85, 0.45, 0.1, 0.5), 1.2)
					cloud.CollisionDamage = 1 + p.Damage * 0.4
					cloud:ToEffect():SetTimeout(90)
				end
			end
		end
		A.burst(tear.Position, 0.8, 0.35, 1, 10, 5)
		fx(EffectVariant.CRACKED_ORB_POOF, tear.Position, nil, Color(0.6, 0.2, 1, 1, 0.4, 0, 0.6))
		sfx:Play(SoundEffect.SOUND_GLASS_BREAK, 0.5, 0, false, 1.4)
		game:ShakeScreen(3)
	end
	mod:AddCallback(ModCallbacks.MC_POST_ENTITY_REMOVE, mod.altarRiftTear, EntityType.ENTITY_TEAR)

	---------------------------------------------------------------------------
	-- Still Sky: time stops; enemy shots turn to stardust
	---------------------------------------------------------------------------

	local stillT = 0
	local STILL_LEN = 120

	local stillLen, stillOwner = STILL_LEN, nil

	mod:AddCallback(ModCallbacks.MC_USE_ITEM, function(_, _, _, p)
		p = p or Isaac.GetPlayer(0)
		-- Eternal Moment: twice as long, and frozen enemies take double damage
		stillLen = combo(p, "eternal_moment") and STILL_LEN * 2 or STILL_LEN
		stillT, stillOwner = stillLen, p
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			if e.Type == EntityType.ENTITY_PROJECTILE then
				A.burst(e.Position, 0.75, 0.8, 1, 4, 2)
				e:Remove()
			elseif e:IsActiveEnemy(false) and e:ToNPC() then
				e:ToNPC():AddFreeze(EntityRef(p), stillLen)
				e:SetColor(Color(0.6, 0.65, 0.9, 1, 0.1, 0.15, 0.35), stillLen, 1, true, false)
			end
		end
		flash(0.8, 0.85, 1, 0.7, 0.04)
		sfx:Play(SoundEffect.SOUND_FREEZE, 1, 0, false, 0.7)
		sfx:Play(SoundEffect.SOUND_STATIC, 0.4, 0, false, 0.6)
		return true
	end, ITEM.still_sky)

	local doubling = false
	function mod:altarStillDamage(ent, amount, flags, source, cd)
		if doubling or stillT <= 0 or ent:ToPlayer() or not ent:IsVulnerableEnemy() then return end
		if not (stillOwner and stillOwner:Exists() and combo(stillOwner, "eternal_moment")) then return end
		doubling = true
		ent:TakeDamage(amount, flags, source, cd)
		doubling = false
		A.burst(ent.Position, 0.67, 0.75, 1, 3, 2)
	end
	mod:AddCallback(ModCallbacks.MC_ENTITY_TAKE_DMG, mod.altarStillDamage)

	local function updateStill()
		if stillT <= 0 then return end
		stillT = stillT - 1
		-- shots fired into the stopped moment don't survive it either
		for _, e in ipairs(Isaac.FindByType(EntityType.ENTITY_PROJECTILE)) do
			A.burst(e.Position, 0.75, 0.8, 1, 3, 1.5)
			e:Remove()
		end
		if stillT == 0 then
			flash(1, 1, 1, 0.5, 0.06)
			sfx:Play(SoundEffect.SOUND_GLASS_BREAK, 0.8, 0, false, 1.1)
		end
	end

	---------------------------------------------------------------------------
	-- Eye of Oblivion: an orbiting void eye
	---------------------------------------------------------------------------

	local eye = Sprite()
	eye:Load("gfx/altar/bh_tear.anm2", true)
	eye:Play("Spin", true)

	local function updateEye(p)
		local d = p:GetData()
		local f = game:GetFrameCount()
		local pos = p.Position + Vector.FromAngle(f * 3.2):Resized(44)
		d.altarEye = pos
		for _, e in ipairs(enemiesNear(pos, 22)) do
			if f % 6 == 0 then
				e:TakeDamage(1 + p.Damage * 0.5, 0, EntityRef(p), 0)
				A.burst(e.Position, 0.7, 0.3, 1, 3, 2)
			end
		end
		for _, pr in ipairs(Isaac.FindInRadius(pos, 16, EntityPartition.BULLET)) do
			A.burst(pr.Position, 0.7, 0.3, 1, 4, 2)
			pr:Remove()
		end
		if f % 45 == 0 then
			local target = nearestEnemy(pos)
			if target then
				local laser = p:FireTechLaser(pos, LaserOffset.LASER_TECH1_OFFSET, (target.Position - pos):Normalized(), false, true, p, 1.5)
				laser.Color = Color(0.6, 0.2, 1, 1, 0.4, 0, 0.6)
				laser:GetData().altarFriendly = true
				sfx:Play(SoundEffect.SOUND_DOGMA_JACOBS_ZAP, 0.35, 0, false, 1.4)
				-- Abyssal Gaze: the eye opens a singularity where it looks
				if combo(p, "abyssal_gaze") then
					local hole = Isaac.Spawn(EntityType.ENTITY_EFFECT, SINGULARITY, 0, target.Position, Vector.Zero, p)
					hole:GetData().altarDamage = p.Damage * 2
					hole.DepthOffset = 20
					sfx:Play(SoundEffect.SOUND_BLACK_POOF, 0.5, 0, false, 1.2)
				end
			end
		end
		if f % 4 == 0 then
			local ember = fx(EffectVariant.EMBER_PARTICLE, pos, RandomVector() * 0.6, Color(0.5, 0.2, 1, 1, 0.3, 0, 0.5))
			ember.DepthOffset = -10
		end
	end

	function mod:altarEyeRender(p, offset)
		-- Dying Star: you glow like one
		local starT = p:GetData().altarStarT or 0
		if starT > 0 then
			local pulse = 0.5 + 0.5 * math.sin(game:GetFrameCount() * 0.4)
			local ps = Isaac.WorldToScreen(p.Position + Vector(0, -18)) + (offset or Vector.Zero)
			A.drawGlow(ps, 2.6 + pulse, 1, 0.6, 0.2, 0.35 + 0.15 * pulse)
			A.drawGlow(ps, 1.1, 1, 1, 0.85, 0.35)
		end
		local pos = p:GetData().altarEye
		if not pos or not has(p, "oblivion_eye") then return end
		local sp = Isaac.WorldToScreen(pos) + (offset or Vector.Zero)
		A.drawGlow(sp + Vector(0, -12), 1, 0.7, 0.35, 1, 0.5)
		eye.Scale = Vector(0.55, 0.55)
		eye:Render(sp + Vector(0, -12), Vector.Zero, Vector.Zero)
		-- the pupil follows the nearest enemy
		local target = nearestEnemy(pos)
		local look = target and (target.Position - pos):Resized(2) or Vector.Zero
		rect(sp.X - 1 + look.X, sp.Y - 13 + look.Y, 3, 3, 1, 0.9, 1, 1)
	end
	mod:AddCallback(ModCallbacks.MC_POST_PLAYER_RENDER, mod.altarEyeRender)

	---------------------------------------------------------------------------
	-- Nebula Heart, Comet Tail, Dying Star (per-player updates)
	---------------------------------------------------------------------------

	local NEBULA = Color(0.85, 0.35, 1, 0.85, 0.45, 0.1, 0.5)

	function mod:altarSkyKill(ent)
		if not ent:IsEnemy() then return end
		A.forEachPlayer(function(p)
			if not has(p, "nebula_heart") then return end
			local cloud = fx(EffectVariant.PLAYER_CREEP_RED, ent.Position, nil, NEBULA, 1.6)
			cloud.CollisionDamage = 1 + p.Damage * 0.4
			cloud:ToEffect():SetTimeout(120)
			A.burst(ent.Position, 1, 0.45, 0.9, 8, 3)
			local d = p:GetData()
			d.altarNebulaKills = (d.altarNebulaKills or 0) + 1
			if d.altarNebulaKills % 12 == 0 then
				p:AddHearts(1)
				A.burst(p.Position, 1, 0.5, 0.9, 14, 4)
				sfx:Play(SoundEffect.SOUND_VAMP_GULP, 0.6, 0, false, 1.3)
			end
		end)
	end
	mod:AddCallback(ModCallbacks.MC_POST_ENTITY_KILL, mod.altarSkyKill)

	local function updateComet(p)
		local d = p:GetData()
		local moving = p.Velocity:Length() > 2.5
		d.altarComet = moving and (d.altarComet or 0) + 1 or 0
		local f = game:GetFrameCount()
		if moving and f % 3 == 0 then
			fx(EffectVariant.EMBER_PARTICLE, p.Position, p.Velocity * -0.3 + RandomVector() * 0.5, Color(0.5, 0.8, 1, 1, 0.3, 0.5, 0.8))
		end
		if moving and f % 7 == 0 then
			local dust = fx(EffectVariant.PLAYER_CREEP_RED, p.Position, nil, Color(0.4, 0.7, 1, 0.7, 0.2, 0.4, 0.8), 0.7)
			dust.CollisionDamage = 0.5 + p.Damage * 0.2
			dust:ToEffect():SetTimeout(45)
		end
		if d.altarComet == 30 then
			sfx:Play(SoundEffect.SOUND_ANGEL_WING, 0.6, 0, false, 0.7)
			A.burst(p.Position, 0.5, 0.8, 1, 12, 5)
		end
		if d.altarComet >= 30 and f % 20 == 0 and combo(p, "meteor_shower") then
			local target = nearestEnemy(p.Position)
			if target then callStar(p, target.Position) end
		end
		if d.altarComet >= 30 then
			p:SetColor(Color(1, 1, 1, 1, 0.15, 0.3, 0.55), 2, 1, false, false)
			if f % 6 == 0 then
				for _, e in ipairs(enemiesNear(p.Position, 30)) do
					e:TakeDamage(3 + p.Damage * 1.5, 0, EntityRef(p), 0)
					e.Velocity = e.Velocity + p.Velocity:Resized(6)
					A.burst(e.Position, 0.5, 0.8, 1, 6, 4)
				end
			end
		end
	end

	local STAR_LEN = 150

	mod:AddCallback(ModCallbacks.MC_USE_ITEM, function(_, _, _, p)
		p = p or Isaac.GetPlayer(0)
		p:GetData().altarStarT = STAR_LEN
		flash(1, 0.8, 0.4, 0.6, 0.04)
		A.burst(p.Position, 1, 0.6, 0.2, 20, 7)
		sfx:Play(SoundEffect.SOUND_SUPERHOLY, 0.8, 0, false, 1.2)
		return true
	end, ITEM.dying_star)

	local function supernova(p)
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			if e.Type == EntityType.ENTITY_PROJECTILE then
				e:Remove()
			elseif e:IsVulnerableEnemy() then
				local dmg = 60 + p.Damage * 10
				if A.isBossLike(e) then dmg = math.min(dmg, e.MaxHitPoints * 0.25) end
				e:TakeDamage(dmg, DamageFlag.DAMAGE_EXPLOSION, EntityRef(p), 0)
				e:AddBurn(EntityRef(p), 90, p.Damage)
			end
		end
		A.flashFx(p.Position, 1, 0.8, 0.5, 6, 24)
		for i = 0, 7 do
			fx(EffectVariant.CRACKED_ORB_POOF, p.Position + Vector.FromAngle(i * 45):Resized(70), nil, Color(1, 0.7, 0.3, 1, 0.6, 0.3, 0))
		end
		A.burst(p.Position, 1, 0.65, 0.25, 32, 9)
		if combo(p, "heavens_fall") then
			local room = game:GetRoom()
			local targets = {}
			for _, e in ipairs(Isaac.GetRoomEntities()) do
				if e:IsVulnerableEnemy() then targets[#targets + 1] = e.Position end
			end
			for i = 1, 8 do
				local spot = targets[i] or room:GetRandomPosition(20)
				Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.CRACK_THE_SKY, 0, spot, Vector.Zero, p)
			end
		end
		flash(1, 1, 0.95, 1, 0.025)
		game:ShakeScreen(30)
		sfx:Play(SoundEffect.SOUND_EXPLOSION_STRONG, 1.2)
		sfx:Play(SoundEffect.SOUND_SUPERHOLY, 1, 0, false, 0.8)
	end

	local function updateDyingStar(p)
		local d = p:GetData()
		if not d.altarStarT or d.altarStarT <= 0 then return end
		d.altarStarT = d.altarStarT - 1
		local f = game:GetFrameCount()
		local pulse = 0.5 + 0.5 * math.sin(f * 0.4)
		p:SetColor(Color(1, 1, 1, 1, 0.6 + 0.3 * pulse, 0.35 + 0.2 * pulse, 0.05), 2, 1, false, false)
		if f % 2 == 0 then
			local a = f * 17
			fx(EffectVariant.EMBER_PARTICLE, p.Position + Vector.FromAngle(a):Resized(30), Vector.FromAngle(a):Resized(2),
				Color(1, 0.6, 0.2, 1, 0.6, 0.3, 0))
		end
		if f % 3 == 0 and combo(p, "heavens_fall") then
			feather(p, p.Position, Vector.FromAngle(f * 23):Resized(9))
		end
		if f % 5 == 0 then
			for _, e in ipairs(enemiesNear(p.Position, 85)) do
				e:TakeDamage(1 + p.Damage * 0.4, DamageFlag.DAMAGE_FIRE, EntityRef(p), 0)
				e:AddBurn(EntityRef(p), 60, p.Damage)
			end
		end
		if d.altarStarT == 0 then supernova(p) end
	end

	function mod:altarStarShield(ent, _, _, source)
		local p = ent:ToPlayer()
		if not p then return end
		if (p:GetData().altarStarT or 0) > 0 then return false end
		-- an Altar item's own beam never hurts you
		local src = source and source.Entity
		if src and src:GetData().altarFriendly then return false end
		-- Seraph Wings: getting hit throws out a ring of holy feathers
		if has(p, "seraph_wings") then
			for i = 0, 11 do feather(p, p.Position, Vector.FromAngle(i * 30):Resized(9)) end
			A.burst(p.Position, 1, 1, 1, 14, 5)
			sfx:Play(SoundEffect.SOUND_ANGEL_WING, 0.9)
		end
	end
	mod:AddCallback(ModCallbacks.MC_ENTITY_TAKE_DMG, mod.altarStarShield, EntityType.ENTITY_PLAYER)

	function mod:altarSkyPeffect(p)
		if has(p, "oblivion_eye") then updateEye(p) else p:GetData().altarEye = nil end
		if has(p, "comet_tail") then updateComet(p) end
		if has(p, "seraph_wings") and game:GetFrameCount() % 8 == 0 and p.Velocity:Length() > 1 then
			fx(EffectVariant.EMBER_PARTICLE, p.Position + Vector(0, -20), RandomVector() * 0.8 + Vector(0, 0.5),
				Color(1, 1, 1, 1, 0.8, 0.8, 0.85))
		end
		updateDyingStar(p)
	end
	mod:AddCallback(ModCallbacks.MC_POST_PEFFECT_UPDATE, mod.altarSkyPeffect)

	function mod:altarSkyUpdate()
		updateStars()
		updateStill()
		for i = #flashes, 1, -1 do
			local fl = flashes[i]
			fl[4] = fl[4] - fl[5]
			if fl[4] <= 0 then table.remove(flashes, i) end
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_UPDATE, mod.altarSkyUpdate)

	function mod:altarSkyRender()
		local W, H = Isaac.GetScreenWidth(), Isaac.GetScreenHeight()
		renderStars()
		if stillT > 0 then
			-- stopped time: the colour drains out and a clock face ticks round the player
			local a = math.min(1, stillT / 15, (stillLen - stillT + 1) / 8)
			rect(0, 0, W, H, 0.55, 0.6, 0.85, 0.22 * a)
			local sp = Isaac.WorldToScreen(Isaac.GetPlayer(0).Position)
			circle(sp.X, sp.Y - 10, 34, 0.85, 0.9, 1, 0.6 * a)
			local hand = math.rad(-90 + (stillLen - stillT) * 3)
			for k = 0, 10 do
				rect(sp.X + math.cos(hand) * k * 3, sp.Y - 10 + math.sin(hand) * k * 3 * 0.75, 2, 2, 1, 1, 1, 0.8 * a)
			end
		end
		for _, fl in ipairs(flashes) do rect(0, 0, W, H, fl[1], fl[2], fl[3], math.min(1, fl[4])) end
	end
	mod:AddCallback(ModCallbacks.MC_POST_RENDER, mod.altarSkyRender)

	function mod:altarSkyNewRoom()
		falling, flashes, stillT = {}, {}, 0
	end
	mod:AddCallback(ModCallbacks.MC_POST_NEW_ROOM, mod.altarSkyNewRoom)
end
