-- Event Horizon active item and the combo system (two or more Altar items
-- together unlock an extra effect, mostly extra beams).
return function(A)
	local mod, game, sfx, ITEM = A.mod, A.game, A.sfx, A.ITEM

	local SINGULARITY = Isaac.GetEntityVariantByName("Altar Singularity")
	local HORIZON = Isaac.GetEntityVariantByName("Altar Event Horizon")

	local function enemies(pos, radius)
		local out = {}
		local list = radius and Isaac.FindInRadius(pos, radius, EntityPartition.ENEMY) or Isaac.GetRoomEntities()
		for _, e in ipairs(list) do
			if e:IsVulnerableEnemy() then out[#out + 1] = e end
		end
		return out
	end

	local function nearest(pos, count)
		local list = enemies()
		table.sort(list, function(a, b) return a.Position:Distance(pos) < b.Position:Distance(pos) end)
		local out = {}
		for i = 1, math.min(count, #list) do out[i] = list[i] end
		return out
	end

	---------------------------------------------------------------------------
	-- Event Horizon
	---------------------------------------------------------------------------

	function A.spawnEventHorizon(p, pos, mini)
		p = p or Isaac.GetPlayer(0)
		pos = pos or game:GetRoom():FindFreeTilePosition(p.Position + p:GetAimDirection():Resized(90), 0)
		local e = Isaac.Spawn(EntityType.ENTITY_EFFECT, HORIZON, 0, pos, Vector.Zero, p)
		local d = e:GetData()
		d.altarLife = mini and 75 or 180
		d.altarScale = mini and 0.5 or 1
		d.altarDamage = p.Damage
		e.SpriteScale = Vector(0.05, 0.05)
		e.DepthOffset = -50
		sfx:Play(SoundEffect.SOUND_HELL_PORTAL1, mini and 0.4 or 1, 0, false, 0.7)
		if not mini then game:ShakeScreen(10) end
		return e
	end

	mod:AddCallback(ModCallbacks.MC_USE_ITEM, function(_, _, _, p)
		A.spawnEventHorizon(p)
		return true
	end, ITEM.event_horizon)

	function mod:altarHorizonUpdate(eff)
		local d = eff:GetData()
		local life, f = d.altarLife or 180, eff.FrameCount
		local full = d.altarScale or 1
		-- grow in, hold, collapse
		local s = full * math.min(1, f / 15, (life - f) / 15)
		eff.SpriteScale = Vector(math.max(0.05, s), math.max(0.05, s))
		local reach = 230 * full

		for _, e in ipairs(Isaac.FindInRadius(eff.Position, reach, EntityPartition.ENEMY)) do
			if e:IsVulnerableEnemy() then
				local dist = e.Position:Distance(eff.Position)
				local pull = (A.isBossLike(e) and 0.6 or 2.2) * (1 - dist / reach) + 0.3
				e.Velocity = e.Velocity * 0.85 + (eff.Position - e.Position):Resized(pull * 3)
				if dist < 55 * full and f % 3 == 0 then
					e:TakeDamage(2 + (d.altarDamage or 3.5) * 0.5, 0, EntityRef(eff.SpawnerEntity), 0)
				end
			end
		end
		-- swallow enemy shots
		for _, proj in ipairs(Isaac.FindInRadius(eff.Position, 160 * full, EntityPartition.BULLET)) do
			proj.Velocity = proj.Velocity * 0.8 + (eff.Position - proj.Position):Resized(3)
			if proj.Position:Distance(eff.Position) < 26 * full then proj:Remove() end
		end
		if f >= life then
			Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.SHOCKWAVE, 0, eff.Position, Vector.Zero, nil)
			sfx:Play(SoundEffect.SOUND_BLACK_POOF, 0.8)
			eff:Remove()
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_EFFECT_UPDATE, mod.altarHorizonUpdate, HORIZON)

	---------------------------------------------------------------------------
	-- Combos
	---------------------------------------------------------------------------

	A.COMBOS = {
		{ key = "singularity_storm", name = "Singularity Storm", items = { "black_hole_core", "storm_core" },
		  desc = "Every singularity fires 4 lightning lasers outward." },
		{ key = "overdrive", name = "Overdrive Cannon", items = { "cosmic_overclock", "bullet_hell" },
		  desc = "Every 8th tear also fires a Brimstone beam." },
		{ key = "satellite_array", name = "Satellite Array", items = { "satellite_beam", "quantum_tears" },
		  desc = "Lasers hit the 3 nearest enemies every 1.5 seconds." },
		{ key = "divine_judgement", name = "Divine Judgement", items = { "seraph_bell", "ascension_sigil" },
		  desc = "Holy beams strike 3 random enemies every 4 seconds." },
		{ key = "prism_lance", name = "Prism Lance", items = { "chaos_prism", "mirror_shard" },
		  desc = "Every 5th tear fires a rainbow laser." },
		{ key = "supermassive", name = "Supermassive", items = { "black_hole_core", "event_horizon" },
		  desc = "Every 3rd singularity opens a mini Event Horizon." },
		{ key = "solar_flare", name = "Solar Flare", items = { "phoenix_feather", "inferno_halo" },
		  desc = "8 Brimstone beams erupt around you every 5 seconds in combat." },
		{ key = "absolute_zero", name = "Absolute Zero", items = { "frost_nova", "chronos_gear" },
		  desc = "Freezes every normal enemy solid for 1.5 seconds, every 3 seconds." },
		{ key = "golden_god", name = "Golden God", items = { "midas_engine", "treasure_geyser", "fourfold_clover" },
		  desc = "Every hit can turn enemies to gold and kills drop 2 coins." },
		-- Fallen Sky combos (effects live in scripts/altar_fallen_sky.lua)
		{ key = "meteor_shower", name = "Meteor Shower", items = { "fallen_star", "comet_tail" },
		  desc = "Every star brings two more, and as a comet you call stars down on enemies as you pass." },
		{ key = "abyssal_gaze", name = "Abyssal Gaze", items = { "oblivion_eye", "black_hole_core" },
		  desc = "The Eye of Oblivion also opens a singularity on its target every time it fires." },
		{ key = "heavens_fall", name = "Heaven's Fall", items = { "seraph_wings", "dying_star" },
		  desc = "As a Dying Star you spray holy feathers in a spiral, and the supernova calls down 8 beams of light." },
		{ key = "eternal_moment", name = "Eternal Moment", items = { "still_sky", "chronos_gear" },
		  desc = "Stopped time lasts 8 seconds and frozen enemies take double damage." },
		{ key = "nebula_rift", name = "Nebula Rift", items = { "rift_shard", "nebula_heart" },
		  desc = "Rifts open twice as often and leave nebula clouds along each beam." },
	}
	A.COMBO_BY_KEY = {}
	for _, c in ipairs(A.COMBOS) do A.COMBO_BY_KEY[c.key] = c end

	local function hasCombo(p, key)
		for _, item in ipairs(A.COMBO_BY_KEY[key].items) do
			if not p:HasCollectible(ITEM[item]) then return false end
		end
		return true
	end
	A.hasCombo = hasCombo

	local function anyCombo(key)
		for i = 0, game:GetNumPlayers() - 1 do
			local p = Isaac.GetPlayer(i)
			if hasCombo(p, key) then return p end
		end
	end

	function A.giveCombo(key, p)
		p = p or Isaac.GetPlayer(0)
		for _, item in ipairs(A.COMBO_BY_KEY[key].items) do
			if not p:HasCollectible(ITEM[item]) then p:AddCollectible(ITEM[item], 0, true) end
		end
	end

	-- announce newly completed combos
	function mod:altarComboCheck(p)
		local d = p:GetData()
		d.altarCombos = d.altarCombos or {}
		for _, c in ipairs(A.COMBOS) do
			local on = hasCombo(p, c.key)
			-- skip the first frames so continuing a run doesn't re-announce old combos
			if on and not d.altarCombos[c.key] and A.banner and p.FrameCount > 15 then
				A.banner("COMBO UNLOCKED", c.name)
				sfx:Play(SoundEffect.SOUND_POWERUP_SPEWER_AMPLIFIED, 1)
				game:ShakeScreen(8)
			end
			d.altarCombos[c.key] = on
		end

		local f = game:GetFrameCount()
		local inCombat = #enemies() > 0

		if hasCombo(p, "satellite_array") and f % 45 == 0 then
			for _, e in ipairs(nearest(p.Position, 3)) do
				local l = p:FireTechLaser(p.Position, LaserOffset.LASER_TECH1_OFFSET, (e.Position - p.Position):Normalized(), false, true, p, 1.5)
				l.Color = Color(1, 0.4, 0.4, 1, 0.4, 0, 0)
			end
		end

		if hasCombo(p, "divine_judgement") and f % 120 == 0 and inCombat then
			local list = enemies()
			for _ = 1, math.min(3, #list) do
				local e = table.remove(list, math.random(#list))
				Isaac.Spawn(EntityType.ENTITY_EFFECT, EffectVariant.CRACK_THE_SKY, 0, e.Position, Vector.Zero, p)
			end
		end

		if hasCombo(p, "solar_flare") and f % 150 == 0 and inCombat then
			for i = 0, 7 do
				local laser = p:FireBrimstone(Vector.FromAngle(i * 45), p, 0.6)
				laser.Timeout = 12
			end
			sfx:Play(SoundEffect.SOUND_FIREDEATH_HISS, 1)
		end

		if hasCombo(p, "absolute_zero") and f % 90 == 0 then
			for _, e in ipairs(enemies()) do
				if not A.isBossLike(e) then e:AddFreeze(EntityRef(p), 45) end
			end
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_PEFFECT_UPDATE, mod.altarComboCheck)

	function mod:altarComboTear(tear)
		local p = tear.SpawnerEntity and tear.SpawnerEntity:ToPlayer()
		if not p then return end
		local d = p:GetData()
		d.altarShots = (d.altarShots or 0) + 1
		local dir = tear.Velocity:Normalized()
		if hasCombo(p, "overdrive") and d.altarShots % 8 == 0 then
			local laser = p:FireBrimstone(dir, p, 0.7)
			laser.Timeout = 10
		end
		if hasCombo(p, "prism_lance") and d.altarShots % 5 == 0 then
			local laser = p:FireTechLaser(p.Position, LaserOffset.LASER_TECH1_OFFSET, dir, false, false, p, 1.2)
			local r, g, b = A.hsv((d.altarShots % 30) / 30, 0.8, 1)
			laser.Color = Color(r, g, b, 1, r * 0.5, g * 0.5, b * 0.5)
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_FIRE_TEAR, mod.altarComboTear)

	local singularityCount = 0
	function mod:altarComboSingularity(eff)
		if eff.FrameCount ~= 1 then return end
		local p = eff.SpawnerEntity and eff.SpawnerEntity:ToPlayer()
		if not p then return end
		if hasCombo(p, "singularity_storm") then
			for i = 0, 3 do
				local l = p:FireTechLaser(eff.Position, LaserOffset.LASER_TECH1_OFFSET, Vector.FromAngle(i * 90 + eff.Index % 45), false, true, p, 0.8)
				l.Color = Color(1, 1, 0.5, 1, 0.4, 0.4, 0)
			end
		end
		if hasCombo(p, "supermassive") then
			singularityCount = singularityCount + 1
			if singularityCount % 3 == 0 then A.spawnEventHorizon(p, eff.Position, true) end
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_EFFECT_UPDATE, mod.altarComboSingularity, SINGULARITY)

	function mod:altarComboHit(ent)
		if not ent:IsVulnerableEnemy() then return end
		local p = anyCombo("golden_god")
		local npc = ent:ToNPC()
		if p and npc and math.random() < 0.35 then npc:AddMidasFreeze(EntityRef(p), 90) end
	end
	mod:AddCallback(ModCallbacks.MC_ENTITY_TAKE_DMG, mod.altarComboHit)

	function mod:altarComboKill(ent)
		if ent:IsEnemy() and anyCombo("golden_god") then
			for _ = 1, 2 do
				Isaac.Spawn(EntityType.ENTITY_PICKUP, PickupVariant.PICKUP_COIN, 0, ent.Position, RandomVector() * 3, nil)
			end
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_ENTITY_KILL, mod.altarComboKill)
end
