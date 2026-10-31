-- Altar Core item effects, pedestal animation and black hole VFX.
return function(A)
	local mod, game, sfx, ITEM = A.mod, A.game, A.sfx, A.ITEM

	local function has(p, key) return p:HasCollectible(ITEM[key]) end
	local function num(p, key) return p:GetCollectibleNum(ITEM[key]) end

	local function enemiesNear(pos, radius)
		local out = {}
		for _, e in ipairs(Isaac.FindInRadius(pos, radius, EntityPartition.ENEMY)) do
			if e:IsVulnerableEnemy() then out[#out + 1] = e end
		end
		return out
	end

	local function roomEnemies()
		local out = {}
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			if e:IsVulnerableEnemy() then out[#out + 1] = e end
		end
		return out
	end

	local function fx(variant, pos, sub)
		return Isaac.Spawn(EntityType.ENTITY_EFFECT, variant, sub or 0, pos, Vector.Zero, nil)
	end

	---------------------------------------------------------------------------
	-- Stats
	---------------------------------------------------------------------------

	function mod:altarCache(p, flag)
		local oc = num(p, "cosmic_overclock")
		local bonus = A.statBonus

		if flag == CacheFlag.CACHE_DAMAGE then
			if oc > 0 then p.Damage = p.Damage * (2 ^ oc) + 2 * oc end
			p.Damage = p.Damage + 1.5 * num(p, "storm_core") + num(p, "vampire_fang") + 3 * num(p, "colossus_tears")
				+ num(p, "ascension_sigil")
			if has(p, "titan_blood") then p.Damage = p.Damage * 1.3 + 1 end
			if has(p, "bullet_hell") then p.Damage = p.Damage * 0.6 end
			p.Damage = p.Damage + bonus.damage
		elseif flag == CacheFlag.CACHE_FIREDELAY then
			if oc > 0 then p.MaxFireDelay = p.MaxFireDelay * (0.5 ^ oc) end
			if has(p, "bullet_hell") then p.MaxFireDelay = p.MaxFireDelay * 0.35 end
			p.MaxFireDelay = p.MaxFireDelay - num(p, "frost_nova") - 0.7 * num(p, "overcharger") - num(p, "ascension_sigil")
				- bonus.tears
			p.MaxFireDelay = math.max(0.5, p.MaxFireDelay)
		elseif flag == CacheFlag.CACHE_SPEED then
			p.MoveSpeed = p.MoveSpeed + 0.3 * oc + 0.2 * num(p, "phoenix_feather") + 0.15 * num(p, "chronos_gear")
				+ 0.4 * num(p, "phantom_step") + 0.2 * num(p, "ascension_sigil") - 0.1 * num(p, "titan_blood") + bonus.speed
		elseif flag == CacheFlag.CACHE_RANGE then
			p.TearRange = p.TearRange + 120 * num(p, "black_hole_core") + 60 * num(p, "ascension_sigil") + 40 * bonus.range
		elseif flag == CacheFlag.CACHE_SHOTSPEED then
			p.ShotSpeed = p.ShotSpeed - 0.15 * num(p, "black_hole_core") + 0.4 * num(p, "bullet_hell")
				+ 0.2 * num(p, "ascension_sigil") + bonus.shotspeed
		elseif flag == CacheFlag.CACHE_LUCK then
			p.Luck = p.Luck + num(p, "midas_engine") + 3 * num(p, "glitched_crown") + 7 * num(p, "fourfold_clover")
				+ 2 * num(p, "ascension_sigil") + bonus.luck
		elseif flag == CacheFlag.CACHE_FLYING then
			if has(p, "glitched_crown") or has(p, "phantom_step") or A.phaseWalk then p.CanFly = true end
		elseif flag == CacheFlag.CACHE_SIZE then
			if has(p, "titan_blood") then p.SpriteScale = p.SpriteScale * 1.25 end
		elseif flag == CacheFlag.CACHE_TEARFLAG then
			local f = p.TearFlags
			if has(p, "black_hole_core") then f = f | TearFlags.TEAR_HOMING | TearFlags.TEAR_SPECTRAL | TearFlags.TEAR_PIERCING end
			if has(p, "storm_core") then f = f | TearFlags.TEAR_JACOBS end
			if has(p, "frost_nova") then f = f | TearFlags.TEAR_ICE | TearFlags.TEAR_SLOW end
			if has(p, "inferno_halo") then f = f | TearFlags.TEAR_BURN end
			if has(p, "colossus_tears") then f = f | TearFlags.TEAR_KNOCKBACK end
			if has(p, "toxic_core") then f = f | TearFlags.TEAR_POISON end
			if has(p, "phantom_step") then f = f | TearFlags.TEAR_SPECTRAL end
			p.TearFlags = f
		elseif flag == CacheFlag.CACHE_TEARCOLOR then
			if has(p, "storm_core") then p.TearColor = Color(1, 1, 0.5, 1, 0.3, 0.3, 0) end
			if has(p, "frost_nova") then p.TearColor = Color(0.7, 0.9, 1, 1, 0.2, 0.3, 0.5) end
			if has(p, "inferno_halo") then p.TearColor = Color(1, 0.6, 0.3, 1, 0.5, 0.15, 0) end
			if has(p, "toxic_core") then p.TearColor = Color(0.5, 1, 0.3, 1, 0.1, 0.3, 0) end
		end
	end
	mod:AddCallback(ModCallbacks.MC_EVALUATE_CACHE, mod.altarCache)

	---------------------------------------------------------------------------
	-- One-time pickup bonuses
	---------------------------------------------------------------------------

	local ON_PICKUP = {
		supernova_heart = function(p) p:AddMaxHearts(2) p:AddHearts(2) end,
		titan_blood = function(p) p:AddMaxHearts(4) p:AddHearts(4) end,
		blast_heart = function(p) p:AddBombs(15) end,
		ascension_sigil = function(p) p:AddSoulHearts(2) end,
	}

	function mod:altarPeffect(p)
		local d = p:GetData()
		d.altarCounts = d.altarCounts or {}
		for key, fn in pairs(ON_PICKUP) do
			local n = num(p, key)
			local before = d.altarCounts[key]
			if before and n > before then
				for _ = 1, n - before do fn(p) end
			end
			d.altarCounts[key] = n
		end

		local frame = game:GetFrameCount()
		-- Toxic Core creep trail
		if has(p, "toxic_core") and frame % 5 == 0 and p.Velocity:Length() > 0.8 then
			local creep = Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.PLAYER_CREEP_GREEN, 0, p.Position, Vector.Zero, p)
			creep.CollisionDamage = 1 + p.Damage * 0.3
		end
		-- Inferno Halo aura
		if has(p, "inferno_halo") and frame % 20 == 0 then
			for _, e in ipairs(enemiesNear(p.Position, 85)) do
				e:TakeDamage(1 + p.Damage * 0.6, DamageFlag.DAMAGE_FIRE, EntityRef(p), 0)
				e:AddBurn(EntityRef(p), 60, p.Damage)
			end
			for i = 0, 5 do
				local ember = fx(EffectVariant.EMBER_PARTICLE, p.Position + Vector.FromAngle(i * 60 + frame * 7):Resized(60))
				ember.Velocity = RandomVector() * 1.5
			end
		end
		-- Chronos Gear: a slow clock ripple
		if has(p, "chronos_gear") and frame % 90 == 0 then
			local wave = fx(EffectVariant.SHOCKWAVE, p.Position)
			wave.Color = Color(1, 0.9, 0.6, 0.5, 0.4, 0.3, 0.1)
			wave.SpriteScale = Vector(0.5, 0.5)
		end
		-- Satellite Beam
		if has(p, "satellite_beam") and frame % 75 == 0 then
			local best, bestD
			for _, e in ipairs(roomEnemies()) do
				local dd = e.Position:Distance(p.Position)
				if not bestD or dd < bestD then best, bestD = e, dd end
			end
			if best then
				p:FireTechLaser(p.Position, LaserOffset.LASER_TECH1_OFFSET, (best.Position - p.Position):Normalized(), false, true, p, 2)
				sfx:Play(SoundEffect.SOUND_LASERRING, 0.5)
			end
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_PEFFECT_UPDATE, mod.altarPeffect)

	-- Chronos Gear: keep every enemy slowed
	function mod:altarNpcUpdate(npc)
		if npc.FrameCount % 15 ~= 0 or not npc:IsVulnerableEnemy() then return end
		local p = A.anyPlayerHas(ITEM.chronos_gear)
		if p then npc:AddSlowing(EntityRef(p), 30, 0.55, Color(0.75, 0.75, 1, 1, 0, 0, 0.15)) end
	end
	mod:AddCallback(ModCallbacks.MC_NPC_UPDATE, mod.altarNpcUpdate)

	---------------------------------------------------------------------------
	-- Tears
	---------------------------------------------------------------------------

	local PRISM_FLAGS = {
		TearFlags.TEAR_HOMING, TearFlags.TEAR_FREEZE, TearFlags.TEAR_CHARM, TearFlags.TEAR_CONFUSION,
		TearFlags.TEAR_FEAR, TearFlags.TEAR_BOOMERANG, TearFlags.TEAR_EXPLOSIVE, TearFlags.TEAR_QUADSPLIT,
		TearFlags.TEAR_LIGHT_FROM_HEAVEN, TearFlags.TEAR_BURN, TearFlags.TEAR_POISON, TearFlags.TEAR_JACOBS,
		TearFlags.TEAR_PIERCING, TearFlags.TEAR_ICE, TearFlags.TEAR_BURSTSPLIT,
	}

	-- Visual + flag tweaks applied to every tear a player shoots, including our extra ones.
	local function decorateTear(tear, p)
		local d = tear:GetData()
		if has(p, "cosmic_overclock") then
			local r, g, b = A.hsv((game:GetFrameCount() % 60) / 60, 0.8, 1)
			tear.Color = Color(r, g, b, 1, r * 0.3, g * 0.3, b * 0.3)
		end
		if has(p, "colossus_tears") then tear.Scale = tear.Scale * 1.8 end
		if has(p, "chaos_prism") then
			tear.TearFlags = tear.TearFlags | PRISM_FLAGS[math.random(#PRISM_FLAGS)]
			local r, g, b = A.hsv(math.random(), 0.7, 1)
			tear.Color = Color(r, g, b, 1, r * 0.25, g * 0.25, b * 0.25)
		end
		if has(p, "fourfold_clover") and math.random() < 0.15 then
			tear.CollisionDamage = tear.CollisionDamage * 3
			tear.Scale = tear.Scale * 1.3
			tear.Color = Color(1, 0.85, 0.2, 1, 0.5, 0.35, 0)
		end
		if has(p, "black_hole_core") then
			d.altarBH = true
			d.altarOwner = p
			tear.Color = Color(1, 1, 1, 0, 0, 0, 0) -- hidden; the black hole sprite is drawn instead
		end
	end

	local firingExtra = false

	function mod:altarFireTear(tear)
		local p = tear.SpawnerEntity and tear.SpawnerEntity:ToPlayer()
		if not p then return end
		decorateTear(tear, p)
		if firingExtra then return end
		firingExtra = true
		local vel = tear.Velocity
		if has(p, "quantum_tears") then
			for _, ang in ipairs({ -12, 12 }) do
				local t2 = p:FireTear(tear.Position, vel:Rotated(ang), false, true, false)
				decorateTear(t2, p)
				t2.Color = Color(0.75, 1, 1, 0.85, 0.05, 0.25, 0.35) -- other-timeline ghosts
			end
		end
		if has(p, "mirror_shard") then
			local back = p:FireTear(p.Position, vel * -1, false, true, false)
			decorateTear(back, p)
			back.Color = Color(0.9, 0.95, 1, 1, 0.3, 0.32, 0.38) -- mirror silver
		end
		firingExtra = false
	end
	mod:AddCallback(ModCallbacks.MC_POST_FIRE_TEAR, mod.altarFireTear)

	-- Black hole tears: pull enemies, render as spinning black holes
	local bhSprite = Sprite()
	bhSprite:Load("gfx/altar/bh_tear.anm2", true)
	bhSprite:Play("Spin", true)

	function mod:altarTearUpdate(tear)
		if not tear:GetData().altarBH then return end
		for _, e in ipairs(enemiesNear(tear.Position, 85)) do
			if not A.isBossLike(e) then
				e.Velocity = e.Velocity + (tear.Position - e.Position):Resized(0.8)
			end
		end
		if tear.FrameCount % 3 == 0 then
			local trail = fx(EffectVariant.EMBER_PARTICLE, tear.Position + tear.PositionOffset)
			trail.Color = Color(0.4, 0, 0.8, 1, 0.3, 0, 0.5)
			trail.Velocity = RandomVector() * 0.6
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_TEAR_UPDATE, mod.altarTearUpdate)

	function mod:altarTearRender(tear, offset)
		if not tear:GetData().altarBH then return end
		local pos = Isaac.WorldToScreen(tear.Position + tear.PositionOffset) + (offset or Vector.Zero)
		local s = 0.75 + tear.Scale * 0.35
		bhSprite.Scale = Vector(s, s)
		bhSprite:Render(pos, Vector.Zero, Vector.Zero)
	end
	mod:AddCallback(ModCallbacks.MC_POST_TEAR_RENDER, mod.altarTearRender)

	function mod:altarUpdate()
		bhSprite:Update()
	end
	mod:AddCallback(ModCallbacks.MC_POST_UPDATE, mod.altarUpdate)

	local SINGULARITY = Isaac.GetEntityVariantByName("Altar Singularity")
	local lastSingularity = -10

	function mod:altarTearRemoved(tear)
		local d = tear:GetData()
		if not d.altarBH or tear.FrameCount < 2 then return end
		local now = game:GetFrameCount()
		if now - lastSingularity < 4 then return end
		lastSingularity = now
		local e = Isaac.Spawn(EntityType.ENTITY_EFFECT, SINGULARITY, 0, tear.Position, Vector.Zero, d.altarOwner)
		e:GetData().altarDamage = d.altarOwner and d.altarOwner.Damage or 3.5
		e.DepthOffset = 20
		sfx:Play(SoundEffect.SOUND_BLACK_POOF, 0.4, 0, false, 1.4)
	end
	mod:AddCallback(ModCallbacks.MC_POST_ENTITY_REMOVE, mod.altarTearRemoved, EntityType.ENTITY_TEAR)

	function mod:altarSingularityUpdate(eff)
		local dmg = eff:GetData().altarDamage or 3.5
		for _, e in ipairs(enemiesNear(eff.Position, 95)) do
			if not A.isBossLike(e) then e.Velocity = e.Velocity * 0.8 + (eff.Position - e.Position):Resized(1.6) end
			if eff.FrameCount % 4 == 0 and e.Position:Distance(eff.Position) < 45 then
				e:TakeDamage(1 + dmg * 0.25, 0, EntityRef(eff.SpawnerEntity), 0)
			end
		end
		if eff:GetSprite():IsFinished("Burst") then eff:Remove() end
	end
	mod:AddCallback(ModCallbacks.MC_POST_EFFECT_UPDATE, mod.altarSingularityUpdate, SINGULARITY)

	---------------------------------------------------------------------------
	-- Damage
	---------------------------------------------------------------------------

	local phoenixUsed = {}

	local function supernova(p)
		fx(EffectVariant.BOMB_EXPLOSION, p.Position)
		fx(EffectVariant.SHOCKWAVE, p.Position)
		for _, e in ipairs(enemiesNear(p.Position, 130)) do
			e:TakeDamage(40 + p.Damage * 6, DamageFlag.DAMAGE_EXPLOSION, EntityRef(p), 0)
		end
		game:ShakeScreen(12)
		sfx:Play(SoundEffect.SOUND_EXPLOSION_STRONG, 0.9)
	end

	function mod:altarPlayerDamage(ent, amount, flags, source)
		local p = ent:ToPlayer()
		if not p then return end
		if A.godMode then return false end

		-- Spike Shield (Debug tab, on by default): spiked rocks and floor spikes can't hurt you.
		-- Sacrifice rooms are left alone, since paying blood there is the point.
		if A.spikeShield and game:GetRoom():GetType() ~= RoomType.ROOM_SACRIFICE then
			local fromGrid = not (source and source.Entity)
			if flags & DamageFlag.DAMAGE_SPIKES ~= 0 or (fromGrid and A.nearSpikedRock(p.Position)) then return false end
			-- anything that still gets through from the room itself goes in log.txt, to find what it was
			if fromGrid then
				local g = game:GetRoom():GetGridEntityFromPos(p.Position)
				Isaac.DebugString(string.format("[Altar Core] room damage: flags=%s grid=%s", tostring(flags), tostring(g and g:GetType())))
			end
		end

		if has(p, "blast_heart") and flags & DamageFlag.DAMAGE_EXPLOSION ~= 0 then
			A.burst(p.Position, 1, 0.45, 0.2, 8, 3) -- the blast washes off you
			return false
		end

		if has(p, "glitched_crown") and math.random() < 0.33 then
			for i = 0, 7 do
				decorateTear(p:FireTear(p.Position, Vector.FromAngle(i * 45):Resized(10), false, true, false), p)
			end
			p:SetMinDamageCooldown(60)
			sfx:Play(SoundEffect.SOUND_EDEN_GLITCH, 0.8)
			game:ShakeScreen(6)
			return false
		end

		local idx = p.ControllerIndex .. ":" .. p:GetPlayerType()
		local hp = p:GetHearts() + p:GetSoulHearts() + p:GetBoneHearts() * 2 + p:GetEternalHearts()
		if has(p, "phoenix_feather") and not phoenixUsed[idx] and amount >= hp then
			phoenixUsed[idx] = true
			p:SetFullHearts()
			p:AddSoulHearts(4)
			p:SetMinDamageCooldown(120)
			for i = 0, 11 do
				Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.RED_CANDLE_FLAME, 0,
					p.Position + Vector.FromAngle(i * 30):Resized(50), Vector.FromAngle(i * 30):Resized(6), p)
			end
			supernova(p)
			sfx:Play(SoundEffect.SOUND_SUPERHOLY, 1)
			return false
		end

		if has(p, "supernova_heart") then supernova(p) end
		if has(p, "phantom_step") then p:SetMinDamageCooldown(150) end
	end
	mod:AddCallback(ModCallbacks.MC_ENTITY_TAKE_DMG, mod.altarPlayerDamage, EntityType.ENTITY_PLAYER)

	function mod:altarEnemyDamage(ent)
		if not ent:IsVulnerableEnemy() then return end
		local midas = A.anyPlayerHas(ITEM.midas_engine)
		local npc = ent:ToNPC()
		if midas and npc and math.random() < 0.15 then
			npc:AddMidasFreeze(EntityRef(midas), 90)
		end
	end
	mod:AddCallback(ModCallbacks.MC_ENTITY_TAKE_DMG, mod.altarEnemyDamage)

	function mod:altarKill(ent)
		if not ent:IsEnemy() then return end
		if A.anyPlayerHas(ITEM.midas_engine) and math.random() < 0.4 then
			Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.ULTRA_GREED_BLING, 0, ent.Position, Vector.Zero, nil)
			Isaac.Spawn(EntityType.ENTITY_PICKUP, PickupVariant.PICKUP_COIN, 0, ent.Position, RandomVector() * 3, nil)
		end
		local vamp = A.anyPlayerHas(ITEM.vampire_fang)
		if vamp and math.random() < 1 / 6 then
			vamp:AddHearts(1)
			A.burst(ent.Position, 0.9, 0.05, 0.1, 10, 4)
			A.burst(vamp.Position, 1, 0.2, 0.25, 8, 2)
			sfx:Play(SoundEffect.SOUND_VAMP_GULP, 0.6)
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_ENTITY_KILL, mod.altarKill)

	function mod:altarRoomClear()
		A.forEachPlayer(function(p)
			if has(p, "supernova_heart") then p:AddHearts(1) end
			if has(p, "overcharger") then
				p:SetActiveCharge(p:GetActiveCharge(ActiveSlot.SLOT_PRIMARY) + num(p, "overcharger"), ActiveSlot.SLOT_PRIMARY)
				A.burst(p.Position, 0.4, 1, 0.5, 10, 3)
				sfx:Play(SoundEffect.SOUND_BATTERYCHARGE, 0.6)
			end
		end)
	end
	mod:AddCallback(ModCallbacks.MC_PRE_SPAWN_CLEAN_AWARD, mod.altarRoomClear)

	function mod:altarNewLevel()
		phoenixUsed = {}
	end
	mod:AddCallback(ModCallbacks.MC_POST_NEW_LEVEL, mod.altarNewLevel)

	---------------------------------------------------------------------------
	-- Actives
	---------------------------------------------------------------------------

	local function use(key, fn)
		mod:AddCallback(ModCallbacks.MC_USE_ITEM, function(_, _, rng, p)
			fn(p or Isaac.GetPlayer(0), rng)
			return true
		end, ITEM[key])
	end

	use("shatter_drive", function(p)
		for _, e in ipairs(roomEnemies()) do
			e:TakeDamage(p.Damage * 15 + 80, 0, EntityRef(p), 0)
			Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.CRACK_THE_SKY, 0, e.Position, Vector.Zero, p)
		end
		game:ShakeScreen(20)
		sfx:Play(SoundEffect.SOUND_GLASS_BREAK, 1.2)
	end)

	use("debug_die", function(p, rng)
		A.spawnRandomQ4(p, rng)
		A.burst(p.Position, 0.3, 1, 0.4, 14, 5)
		fx(EffectVariant.CRACKED_ORB_POOF, p.Position).Color = Color(0.3, 1, 0.4, 1, 0, 0.5, 0.1)
		sfx:Play(SoundEffect.SOUND_EDEN_GLITCH, 0.6)
	end)

	use("nuke_button", function(p)
		local room = game:GetRoom()
		for _, e in ipairs(roomEnemies()) do
			if A.isBossLike(e) then
				e:TakeDamage(e.MaxHitPoints * 0.4, DamageFlag.DAMAGE_EXPLOSION, EntityRef(p), 0)
			else
				e:Kill()
			end
		end
		for i = 0, 9 do
			fx(EffectVariant.BOMB_EXPLOSION, room:GetRandomPosition(20))
		end
		game:ShakeScreen(45)
		game:Darken(1, 20)
		sfx:Play(SoundEffect.SOUND_EXPLOSION_STRONG, 1.5)
	end)

	use("wormhole_key", function()
		local level = game:GetLevel()
		local idx = level:QueryRoomTypeIndex(RoomType.ROOM_TREASURE, false, RNG())
		if idx == level:GetCurrentRoomIndex() then
			idx = level:GetRandomRoomIndex(false, Random())
		end
		A.burst(Isaac.GetPlayer(0).Position, 0.7, 0.4, 1, 16, 6)
		sfx:Play(SoundEffect.SOUND_HELL_PORTAL1, 0.8)
		game:StartRoomTransition(idx, Direction.NO_DIRECTION, RoomTransitionAnim.TELEPORT)
	end)

	use("balance_glove", function(p)
		for _, e in ipairs(roomEnemies()) do
			if A.isBossLike(e) then
				e:TakeDamage(e.HitPoints * 0.5, 0, EntityRef(p), 0)
			elseif math.random() < 0.5 then
				fx(EffectVariant.POOF02, e.Position)
				e:Remove()
			end
		end
		game:ShakeScreen(10)
		sfx:Play(SoundEffect.SOUND_DEATH_CARD, 1)
	end)

	use("seraph_bell", function(p)
		for i = 0, 7 do
			Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.CRACK_THE_SKY, 0,
				p.Position + Vector.FromAngle(i * 45):Resized(80), Vector.Zero, p)
		end
		p:AddSoulHearts(2)
		sfx:Play(SoundEffect.SOUND_HOLY, 1)
	end)

	use("treasure_geyser", function(p)
		for i = 1, 12 do
			Isaac.Spawn(EntityType.ENTITY_PICKUP, PickupVariant.PICKUP_COIN, 0, p.Position, RandomVector() * (3 + math.random() * 4), nil)
		end
		Isaac.Spawn(EntityType.ENTITY_PICKUP, PickupVariant.PICKUP_BOMB, 0, p.Position, RandomVector() * 4, nil)
		Isaac.Spawn(EntityType.ENTITY_PICKUP, PickupVariant.PICKUP_KEY, 0, p.Position, RandomVector() * 4, nil)
		A.burst(p.Position, 1, 0.85, 0.25, 16, 6)
		for _ = 1, 4 do
			Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.ULTRA_GREED_BLING, 0, p.Position + RandomVector() * 20, Vector.Zero, nil)
		end
		sfx:Play(SoundEffect.SOUND_CASH_REGISTER, 1)
	end)

	---------------------------------------------------------------------------
	-- Animated pedestals
	---------------------------------------------------------------------------

	local FRAME_PATH = {}
	for _, info in ipairs(A.DATA) do
		local frames = {}
		for i = 0, 5 do frames[i] = "gfx/items/collectibles/altar/" .. info.key .. "_" .. i .. ".png" end
		FRAME_PATH[ITEM[info.key]] = frames
	end
	A.FRAME_PATH = FRAME_PATH

	function mod:altarPedestal(pickup)
		local frames = FRAME_PATH[pickup.SubType]
		if not frames then return end
		if game:GetLevel():GetCurses() & LevelCurse.CURSE_OF_BLIND ~= 0 then return end
		local frame = (game:GetFrameCount() // 4) % 6
		local d = pickup:GetData()
		if d.altarFrame == frame and d.altarSub == pickup.SubType then return end
		d.altarFrame, d.altarSub = frame, pickup.SubType
		local s = pickup:GetSprite()
		s:ReplaceSpritesheet(1, frames[frame])
		s:LoadGraphics()
	end
	mod:AddCallback(ModCallbacks.MC_POST_PICKUP_UPDATE, mod.altarPedestal, PickupVariant.PICKUP_COLLECTIBLE)
end
