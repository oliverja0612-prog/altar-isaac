-- Altar menu: gem button, animated panel (Mods / Items / Give / Debug / Settings),
-- stat overlay and toasts. Everything is drawn immediate-mode in MC_POST_RENDER.
return function(A)
	local mod, game, sfx, json = A.mod, A.game, A.sfx, A.json

	---------------------------------------------------------------------------
	-- Settings
	---------------------------------------------------------------------------

	local settings = {
		buttonCorner = 1,
		showButton = true,
		showOverlay = false,
		freezePlayer = true,
		accent = 1,
		smooth = true,
		portraitBoxes = {}, -- measured portrait sizes, so they never need measuring again
	}
	A.settings = settings

	local CORNERS = { "Bottom Left", "Top Center", "Right Edge", "Bottom Center" }
	local ACCENTS = {
		{ name = "Windows Blue", c = { 0.30, 0.76, 1.00 } },
		{ name = "Amethyst", c = { 0.68, 0.45, 1.00 } },
		{ name = "Gold",     c = { 1.00, 0.78, 0.30 } },
		{ name = "Cyan",     c = { 0.30, 0.88, 1.00 } },
		{ name = "Emerald",  c = { 0.32, 0.95, 0.55 } },
		{ name = "Crimson",  c = { 1.00, 0.36, 0.42 } },
	}

	local function saveSettings()
		-- keep the clipboard text the Altar app wrote into the same file
		local out = {}
		for k, v in pairs(settings) do out[k] = v end
		if mod:HasData() then
			local ok, data = pcall(json.decode, mod:LoadData())
			if ok and type(data) == "table" then out.clip = data.clip end
		end
		mod:SaveData(json.encode(out))
	end

	local function loadSettings()
		if not mod:HasData() then return end
		local ok, data = pcall(json.decode, mod:LoadData())
		if ok and type(data) == "table" then
			for k, v in pairs(data) do
				if settings[k] ~= nil then settings[k] = v end
			end
		end
		if not CORNERS[settings.buttonCorner] then settings.buttonCorner = 1 end
		if not ACCENTS[settings.accent] then settings.accent = 1 end
	end
	loadSettings()

	---------------------------------------------------------------------------
	-- Palette + drawing
	---------------------------------------------------------------------------

	-- Windows 11 dark mode palette
	local WHITE = { 1, 1, 1 }
	local TEXT = { 1, 1, 1 }
	local SUB = { 0.80, 0.80, 0.80 }
	local DIM = { 0.56, 0.56, 0.56 }
	local GREEN = { 0.42, 0.85, 0.42 }
	local RED = { 0.91, 0.28, 0.34 }
	local GOLD = { 1.0, 0.80, 0.32 }
	local BG = { 0.11, 0.11, 0.11 }
	local PANEL = { 0.125, 0.125, 0.125 }
	local SURFACE = { 0.176, 0.176, 0.176 }
	local SURFACE_HI = { 0.22, 0.22, 0.22 }
	local LINE = { 0.26, 0.26, 0.26 }
	local BLACK = { 0, 0, 0 }
	local CLOSE_RED = { 0.77, 0.17, 0.11 }
	local TERM_BG = { 0.047, 0.047, 0.047 }
	local TERM_TEXT = { 0.80, 0.80, 0.80 }

	local function accent() return ACCENTS[settings.accent].c end

	local function mix(a, b, t)
		return { a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t }
	end

	local function clamp(v, lo, hi) return math.max(lo or 0, math.min(hi or 1, v)) end
	local function easeOut(t) t = clamp(t) return 1 - (1 - t) ^ 3 end
	local function easeBack(t)
		t = clamp(t)
		local c = 1.6
		return 1 + (c + 1) * (t - 1) ^ 3 + c * (t - 1) ^ 2
	end

	local px = Sprite()
	px:Load("gfx/altar/altar_pixel.anm2", true)
	px:Play("Idle", true)

	local gem = Sprite()
	gem:Load("gfx/altar/altar_button.anm2", true)
	gem:Play("Idle", true)

	-- Loads the first font file that exists. Repentance+ dropped font/luamini.fnt,
	-- and a missing font draws nothing at all, so always keep fallbacks.
	local function loadFont(...)
		local f = Font()
		for _, path in ipairs({ ... }) do
			f:Load(path)
			local ok, loaded = pcall(f.IsLoaded, f)
			if not ok or loaded then return f end
		end
		return f
	end

	local fSmall = loadFont("font/pftempestasevencondensed.fnt", "font/terminus.fnt")
	local fMini = loadFont("font/luaminioutlined.fnt", "font/luamini.fnt", "font/pftempestasevencondensed.fnt")
	local fTitle = loadFont("font/upheaval.fnt", "font/teammeatfont16bold.fnt")
	-- monospace for the console, like cmd.exe
	local fMono = loadFont("font/terminus8.fnt", "font/terminus.fnt", "font/pftempestasevencondensed.fnt")

	-- measured line height so labels centre properly whatever font actually loaded
	local lineHeights = {}
	local function lineH(f)
		if not lineHeights[f] then
			local ok, h = pcall(f.GetLineHeight, f)
			lineHeights[f] = (ok and type(h) == 'number' and h > 0) and h or 10
		end
		return lineHeights[f]
	end

	local alpha = 1

	local function rect(x, y, w, h, c, a)
		if w <= 0 or h <= 0 then return end
		px.Scale = Vector(w / 4, h / 4)
		px.Color = Color(c[1], c[2], c[3], (a or 1) * alpha, 0, 0, 0)
		px:Render(Vector(math.floor(x + 0.5), math.floor(y + 0.5)), Vector.Zero, Vector.Zero)
	end

	-- 2px rounded corners
	local function rrect(x, y, w, h, c, a)
		rect(x + 2, y, w - 4, h, c, a)
		rect(x + 1, y + 1, w - 2, h - 2, c, a)
		rect(x, y + 2, w, h - 4, c, a)
	end

	local function frame(x, y, w, h, fill, border, a)
		rrect(x, y, w, h, border, a)
		rrect(x + 1, y + 1, w - 2, h - 2, fill, a)
	end

	-- 4px rounded corners for the window itself
	local function rwin(x, y, w, h, c, a)
		rect(x + 4, y, w - 8, h, c, a)
		rect(x + 2, y + 1, w - 4, h - 2, c, a)
		rect(x + 1, y + 2, w - 2, h - 4, c, a)
		rect(x, y + 4, w, h - 8, c, a)
	end

	local function text(font, str, x, y, c, a, boxW, center)
		font:DrawString(str, math.floor(x + 0.5), math.floor(y + 0.5), KColor(c[1], c[2], c[3], (a or 1) * alpha), boxW or 0, center or false)
	end

	local function wrap(font, str, maxW)
		local lines, line = {}, ""
		for word in tostring(str):gmatch("%S+") do
			local test = line == "" and word or (line .. " " .. word)
			if font:GetStringWidth(test) > maxW and line ~= "" then
				lines[#lines + 1] = line
				line = word
			else
				line = test
			end
		end
		if line ~= "" then lines[#lines + 1] = line end
		return lines
	end

	local function clip(font, str, maxW)
		if font:GetStringWidth(str) <= maxW then return str end
		while #str > 1 and font:GetStringWidth(str .. "..") > maxW do str = str:sub(1, -2) end
		return str .. ".."
	end

	-- 16x16 UI icons (gfx/altar/ic_<name>.png)
	local icons = {}
	local function icon(name, x, y, a, scale)
		local s = icons[name]
		if not s then
			s = Sprite()
			s:Load("gfx/altar/altar_icon16.anm2", false)
			s:ReplaceSpritesheet(0, "gfx/altar/ic_" .. name .. ".png")
			s:LoadGraphics()
			s:Play("Idle", true)
			icons[name] = s
		end
		s.Scale = Vector(scale or 1, scale or 1)
		s.Color = Color(1, 1, 1, (a or 1) * alpha, 0, 0, 0)
		s:Render(Vector(math.floor(x), math.floor(y)), Vector.Zero, Vector.Zero)
	end

	-- Boss / character portraits from the game's own files. Their sizes vary, so
	-- each one is measured once with GetTexel (a couple per frame to avoid
	-- hitches) and then scaled to fit its box.
	local portraits = {}
	local measureBudget = 0

	local function portrait(path)
		local p = portraits[path]
		if not p then
			local s = Sprite()
			s:Load("gfx/altar/altar_portrait.anm2", false)
			s:ReplaceSpritesheet(0, path)
			s:LoadGraphics()
			s:Play("Idle", true)
			p = { s = s }
			portraits[path] = p
			local cached = settings.portraitBoxes[path]
			if type(cached) == "table" and #cached >= 4 then
				p.box = { cached[1], cached[2], cached[3], cached[4] }
				p.empty = cached[5] == 1
			end
		end
		if not p.box and measureBudget > 0 then
			measureBudget = measureBudget - 1
			local minx, miny, maxx, maxy = 999, 999, -1, -1
			p.s.Scale = Vector(1, 1)
			local ok = pcall(function()
				for yy = 0, 252, 4 do
					for xx = 0, 252, 4 do
						if p.s:GetTexel(Vector(xx, yy), Vector.Zero, 0.1).Alpha > 0.1 then
							if xx < minx then minx = xx end
							if yy < miny then miny = yy end
							if xx > maxx then maxx = xx end
							if yy > maxy then maxy = yy end
						end
					end
				end
			end)
			if not ok then
				p.box = { 0, 0, 96, 96 }
			elseif maxx < 0 then
				p.empty = true
				p.box = { 0, 0, 1, 1 }
			else
				p.box = { minx, miny, maxx - minx + 4, maxy - miny + 4 }
			end
			if ok then
				settings.portraitBoxes[path] = { p.box[1], p.box[2], p.box[3], p.box[4], p.empty and 1 or 0 }
			end
		end
		return p
	end

	local function letterTile(name, x, y, size)
		local r, g, b = A.hsv(((name:byte(1) or 65) * 37 % 360) / 360, 0.5, 0.95)
		rrect(x, y, size, size, { r, g, b }, 0.85)
		text(fSmall, name:sub(1, 1):upper(), x, y + math.floor(size / 2) - 6, BG, 1, size, true)
	end

	local function drawPortrait(path, name, x, y, size, a)
		local p = path and portrait(path)
		if not p or not p.box or p.empty then
			letterTile(name, x, y, size)
			return
		end
		local bx, by, bw, bh = p.box[1], p.box[2], p.box[3], p.box[4]
		local s = math.min(size / bw, size / bh)
		p.s.Scale = Vector(s, s)
		p.s.Color = Color(1, 1, 1, (a or 1) * alpha, 0, 0, 0)
		p.s:Render(Vector(math.floor(x + (size - bw * s) / 2 - bx * s), math.floor(y + (size - bh * s) / 2 - by * s)),
			Vector.Zero, Vector.Zero)
	end

	-- 32x32 collectible icons; Altar items cycle through their animation frames
	local itemSprites = {}
	local function itemSprite(path)
		local s = itemSprites[path]
		if not s then
			s = Sprite()
			s:Load("gfx/altar/altar_icon.anm2", false)
			s:ReplaceSpritesheet(0, path)
			s:LoadGraphics()
			s:Play("Idle", true)
			itemSprites[path] = s
		end
		return s
	end

	local function drawItem(info, x, y, a, scale)
		local path = info.gfx
		local frames = A.FRAME_PATH and A.FRAME_PATH[info.id]
		if frames then path = frames[(Isaac.GetFrameCount() // 8) % 6] end
		if not path then return end
		local s = itemSprite(path)
		s.Scale = Vector(scale or 1, scale or 1)
		s.Color = Color(1, 1, 1, (a or 1) * alpha, 0, 0, 0)
		s:Render(Vector(math.floor(x), math.floor(y)), Vector.Zero, Vector.Zero)
	end

	---------------------------------------------------------------------------
	-- Animation state
	---------------------------------------------------------------------------

	local anims = {}
	-- Smoothly moves the value stored under id toward target and returns it.
	local function anim(id, target, speed)
		local v = anims[id]
		if v == nil or not settings.smooth then
			anims[id] = target
			return target
		end
		v = v + (target - v) * (speed or 0.25)
		if math.abs(target - v) < 0.002 then v = target end
		anims[id] = v
		return v
	end

	local ripples = {}
	local function ripple(x, y, w, h)
		ripples[#ripples + 1] = { x = x, y = y, w = w, h = h, t = 0 }
	end

	---------------------------------------------------------------------------
	-- Input
	---------------------------------------------------------------------------

	local M = { x = 0, y = 0, l = false, r = false, click = false, rclick = false, idle = 999 }

	local function updateMouse()
		local p = Isaac.WorldToScreen(Input.GetMousePosition(true))
		if math.abs(p.X - M.x) + math.abs(p.Y - M.y) > 2 then M.idle = 0 else M.idle = M.idle + 1 end
		M.x, M.y = p.X, p.Y
		local l = Input.IsMouseBtnPressed(Mouse.MOUSE_BUTTON_LEFT)
		local r = Input.IsMouseBtnPressed(Mouse.MOUSE_BUTTON_RIGHT)
		M.click = l and not M.l
		M.rclick = r and not M.r
		M.l, M.r = l, r
	end

	-- Edge-detected key presses (render runs at 60fps, game input at 30, so
	-- IsButtonTriggered can fire twice per press).
	local keyPrev = {}
	local function keyPressed(k)
		local now = Input.IsButtonPressed(k, 0)
		local was = keyPrev[k]
		keyPrev[k] = now
		return now and not was
	end

	local function hover(x, y, w, h)
		return M.x >= x and M.x < x + w and M.y >= y and M.y < y + h
	end

	---------------------------------------------------------------------------
	-- UI state
	---------------------------------------------------------------------------

	local TABS = {
		{ id = "mods", name = "Mods", sub = "Installed mods" },
		{ id = "items", name = "Items", sub = "Browse, give and spawn any item" },
		{ id = "give", name = "Give", sub = "Hearts, pickups and stat boosts" },
		{ id = "combos", name = "Combos", sub = "Item synergies with extra effects" },
		{ id = "warp", name = "Warp", sub = "Rooms, floors and any boss" },
		{ id = "player", name = "Player", sub = "Characters and curses" },
		{ id = "debug", name = "Debug", sub = "Live info, cheats and tools" },
		{ id = "console", name = "Console", sub = "Type commands  (F4)" },
		{ id = "settings", name = "Settings", sub = "Customize Altar" },
	}

	local ui = {
		open = false,
		openT = 0,
		tab = 1,
		tabT = 1,
		page = 0,
		tooltip = nil,
		toasts = {},
		frozePlayers = false,
		qty = 1,
		search = "",
		searchFocus = false,
		filter = 1,
		debugOn = {},
		input = "",
		consoleFocus = false,
		log = {},
		history = {},
		histPos = 0,
		warpMode = 1,
		playerMode = 1,
		banner = nil,
	}

	function A.banner(title, sub)
		ui.banner = { title = title, sub = sub, t = 0 }
	end

	local function consoleLog(input, output, isErr)
		if input then table.insert(ui.log, { "> " .. input, "in" }) end
		for line in tostring(output or ""):gmatch("[^\n]+") do
			table.insert(ui.log, { line, isErr and "err" or "out" })
		end
		while #ui.log > 60 do table.remove(ui.log, 1) end
	end
	A.consoleLog = consoleLog

	local function setOpen(open)
		if ui.open == open then return end
		ui.open = open
		ui.searchFocus = false
		ui.consoleFocus = false
		sfx:Play(open and SoundEffect.SOUND_PAPER_IN or SoundEffect.SOUND_PAPER_OUT, 0.7)
		if not open and ui.frozePlayers then
			A.forEachPlayer(function(p) p.ControlsEnabled = true end)
			ui.frozePlayers = false
		end
	end

	local function setTab(i)
		if ui.tab == i then return end
		ui.tab = i
		ui.tabT = 0
		ui.page = 0
		ui.searchFocus = false
		ui.consoleFocus = TABS[i].id == "console"
		sfx:Play(SoundEffect.SOUND_MENU_SCROLL, 0.5)
	end

	local function toast(msg, iconName)
		table.insert(ui.toasts, 1, { msg = msg, icon = iconName, t = 0, life = 150 })
		while #ui.toasts > 4 do table.remove(ui.toasts) end
	end
	A.toast = toast

	-- Fade + slide for the i-th element of a freshly opened tab.
	local function enter(i)
		return easeOut(ui.tabT * 2.2 - i * 0.07)
	end

	local function withEnter(i, fn)
		local saved = alpha
		local e = enter(i)
		alpha = saved * e
		fn(math.floor((1 - e) * 10))
		alpha = saved
	end

	---------------------------------------------------------------------------
	-- Widgets
	---------------------------------------------------------------------------

	-- Returns "left", "right" or nil.
	local function button(id, x, y, w, h, label, opts)
		opts = opts or {}
		local hov = hover(x, y, w, h)
		local hv = anim(id, hov and 1 or 0, 0.3)
		local press = anim(id .. ":p", 0, 0.15)
		-- flat Windows 11 button: 1px border, lighter fill on hover, darker on press
		local base, border
		if opts.on then
			base = mix(accent(), WHITE, hv * 0.15)
			border = mix(accent(), WHITE, 0.25)
		else
			base = mix(opts.bg or SURFACE, SURFACE_HI, hv)
			border = mix(LINE, accent(), hv * 0.35)
		end
		local lift = 0
		frame(x, y, w, h, base, border)
		rect(x + 2, y + h - 1, w - 4, 1, BLACK, 0.25)
		if press > 0.01 then rrect(x, y, w, h, BLACK, press * 0.25) end
		local tx = x
		local tw = w
		if opts.icon then
			icon(opts.icon, x + 2, y - lift + math.floor((h - 16) / 2), 1, opts.iconScale)
			tx, tw = x + 16, w - 16
		end
		if label and label ~= "" then
			local fc = opts.on and BG or (opts.color or TEXT)
			local font = opts.font or fMini
			local ty = y - lift + math.floor((h - lineH(font)) / 2)
			text(font, label, tx, ty, fc, 1, tw, true)
		end
		if hov and opts.tip then ui.tooltip = opts.tip end
		if hov and (M.click or (M.rclick and opts.right)) then
			anims[id .. ":p"] = 1
			ripple(x, y - lift, w, h)
			if not opts.silent then sfx:Play(SoundEffect.SOUND_BUTTON_PRESS, 0.45) end
			return M.click and "left" or "right"
		end
	end

	local function sectionLabel(str, x, y)
		text(fMini, str, x, y, accent())
		rect(x + fMini:GetStringWidth(str) + 4, y + 5, 40, 1, LINE)
	end

	local QTY_PRESETS = { 1, 5, 10, 25, 99 }

	local function qtyStepper(x, y)
		local w = 64
		frame(x, y, w, 14, SURFACE, LINE)
		if button("qty-", x + 1, y + 1, 13, 12, "-", { bg = SURFACE }) then ui.qty = math.max(1, ui.qty - 1) end
		if button("qty+", x + w - 14, y + 1, 13, 12, "+", { bg = SURFACE }) then ui.qty = math.min(99, ui.qty + 1) end
		local hov = hover(x + 14, y, w - 28, 14)
		text(fMini, "x" .. ui.qty, x + 14, y + 3, hov and accent() or TEXT, 1, w - 28, true)
		if hov then
			ui.tooltip = "Amount used by Give and Items. Click to cycle 1 / 5 / 10 / 25 / 99."
			if M.click then
				local nxt = QTY_PRESETS[1]
				for _, v in ipairs(QTY_PRESETS) do
					if v > ui.qty then nxt = v break end
				end
				ui.qty = nxt
				sfx:Play(SoundEffect.SOUND_BUTTON_PRESS, 0.45)
			end
		end
	end

	---------------------------------------------------------------------------
	-- Item catalogue
	---------------------------------------------------------------------------

	local getCatalogue = A.getCatalogue

	local FILTERS = {
		{ name = "All", test = function() return true end },
		{ name = "Altar", test = function(i) return i.altar end },
		{ name = "Q4", test = function(i) return i.q >= 4 end },
		{ name = "Active", test = function(i) return i.active end },
	}

	local function filteredItems()
		local out = {}
		local q = ui.search:lower()
		local f = FILTERS[ui.filter].test
		for _, info in ipairs(getCatalogue()) do
			if f(info) and (q == "" or info.lname:find(q, 1, true)) then out[#out + 1] = info end
		end
		return out
	end

	local function giveItem(info, n, spawn)
		local p = Isaac.GetPlayer(0)
		if spawn then
			n = math.min(n, 20)
			for _ = 1, n do A.spawnItem(info.id, p) end
			toast("Spawned " .. info.name .. (n > 1 and (" x" .. n) or ""), nil)
			sfx:Play(SoundEffect.SOUND_THUMBSUP, 0.6)
		else
			for _ = 1, n do p:AddCollectible(info.id, 0, true) end
			toast("Gave " .. info.name .. (n > 1 and (" x" .. n) or ""), nil)
			sfx:Play(SoundEffect.SOUND_POWERUP_SPEWER, 0.7)
		end
	end

	---------------------------------------------------------------------------
	-- Tabs
	---------------------------------------------------------------------------

	local function pager(x, y, w, total, perPage)
		local pages = math.max(1, math.ceil(total / perPage))
		ui.page = clamp(ui.page, 0, pages - 1)
		local label = (ui.page + 1) .. " / " .. pages
		if button("pg<", x + w - 64, y, 16, 12, "<") then ui.page = (ui.page - 1) % pages end
		text(fMini, label, x + w - 48, y + 2, SUB, 1, 32, true)
		if button("pg>", x + w - 16, y, 16, 12, ">") then ui.page = (ui.page + 1) % pages end
	end

	local function tabMods(x, y, w, h)
		local list = A.modList
		local rowH = 26
		local perPage = math.max(1, math.floor((h - 16) / (rowH + 3)))
		if #list == 0 then
			withEnter(0, function(dx)
				text(fSmall, "No mod list yet", x + dx, y + 40, SUB, 1, w, true)
				text(fMini, "Open Altar Mod Manager once to sync your mods here.", x + dx, y + 56, DIM, 1, w, true)
			end)
			return
		end
		for i = 1, perPage do
			local m = list[i + ui.page * perPage]
			if not m then break end
			withEnter(i, function(dx)
				local ry = y + (i - 1) * (rowH + 3)
				local rx = x + dx
				local hov = hover(rx, ry, w, rowH)
				local hv = anim("mod" .. i, hov and 1 or 0, 0.3)
				frame(rx, ry, w, rowH, mix(SURFACE, SURFACE_HI, hv), mix(LINE, accent(), hv * 0.7))
				local r, g, b = A.hsv(((m.name:byte(1) or 65) * 37 % 360) / 360, 0.5, 0.95)
				rrect(rx + 4, ry + 4, 18, 18, { r, g, b })
				text(fSmall, m.name:sub(1, 1):upper(), rx + 4, ry + 6, BG, 1, 18, true)
				local name = clip(fSmall, m.name, w - 120)
				text(fSmall, name, rx + 28, ry + 2, m.enabled and TEXT or DIM)
				text(fMini, "v" .. (m.version or "?"), rx + 32 + fSmall:GetStringWidth(name), ry + 5, GREEN)
				text(fMini, clip(fMini, m.folder or "", w - 100), rx + 28, ry + 15, DIM)
				local pill = m.enabled and "ON" or "OFF"
				rrect(rx + w - 34, ry + 8, 28, 11, m.enabled and GREEN or RED, 0.9)
				text(fMini, pill, rx + w - 34, ry + 10, BG, 1, 28, true)
				if hov then ui.tooltip = (m.description and m.description ~= "") and m.description or m.folder end
			end)
		end
		text(fMini, #list .. " mods - toggle them in Altar Mod Manager, then restart", x, y + h - 11, DIM)
		pager(x, y + h - 13, w, #list, perPage)
	end

	local function tabItems(x, y, w, h)
		-- search box
		local sw = 104
		local sh = hover(x, y, sw, 14)
		local sf = anim("searchF", ui.searchFocus and 1 or 0, 0.3)
		frame(x, y, sw, 14, SURFACE, mix(LINE, accent(), math.max(sf, sh and 0.4 or 0)))
		local shown = ui.search
		if shown == "" and not ui.searchFocus then
			text(fMini, "Search items...", x + 4, y + 3, DIM)
		else
			local caret = (ui.searchFocus and (Isaac.GetFrameCount() // 20) % 2 == 0) and "_" or ""
			text(fMini, clip(fMini, shown, sw - 12) .. caret, x + 4, y + 3, TEXT)
		end
		if sh then ui.tooltip = "Click and type to search. Enter or Esc to stop typing." end
		if M.click then
			ui.searchFocus = sh
		end

		-- filter chips
		local cx = x + sw + 4
		for i, f in ipairs(FILTERS) do
			local cw = fMini:GetStringWidth(f.name) + 10
			if button("flt" .. i, cx, y, cw, 14, f.name, { on = ui.filter == i }) then
				ui.filter = i
				ui.page = 0
				ui.tabT = 0.3
			end
			cx = cx + cw + 3
		end

		local list = filteredItems()
		local cell = 34
		local cols = math.max(1, math.floor((w + 2) / (cell + 2)))
		local gy = y + 18
		local rows = math.max(1, math.floor((h - 18 - 16) / (cell + 2)))
		local perPage = cols * rows
		ui.page = clamp(ui.page, 0, math.max(0, math.ceil(#list / perPage) - 1))
		local ox = x + math.floor((w - cols * (cell + 2) + 2) / 2)

		for slot = 0, perPage - 1 do
			local info = list[ui.page * perPage + slot + 1]
			if not info then break end
			local col, row = slot % cols, slot // cols
			withEnter(row * 2 + col * 0.4, function(dx)
				local cx2, cy2 = ox + col * (cell + 2) + dx, gy + row * (cell + 2)
				local hov = hover(cx2, cy2, cell, cell)
				local hv = anim("it" .. slot, hov and 1 or 0, 0.3)
				local border = info.altar and mix(LINE, GOLD, 0.35 + hv * 0.5) or mix(LINE, accent(), hv)
				frame(cx2, cy2 - math.floor(hv + 0.5), cell, cell, mix(SURFACE, SURFACE_HI, hv), border)
				drawItem(info, cx2 + 1, cy2 + 1 - math.floor(hv * 2 + 0.5), 1)
				if hov then
					ui.tooltip = info.name .. "  [Q" .. info.q .. "]  " .. (info.desc or "") .. "   L: give x" .. ui.qty .. "  R: spawn"
					if M.click then giveItem(info, ui.qty, false) ripple(cx2, cy2, cell, cell)
					elseif M.rclick then giveItem(info, ui.qty, true) ripple(cx2, cy2, cell, cell) end
				end
			end)
		end
		if #list == 0 then
			text(fSmall, "No items match", x, gy + 50, SUB, 1, w, true)
		end
		text(fMini, #list .. " items", x, y + h - 11, DIM)
		pager(x, y + h - 13, w, #list, perPage)
	end

	local HEARTS = {
		{ "heart_container", "Heart Container", function(p, n) p:AddMaxHearts(2 * n) end },
		{ "heart_red", "Red Heart", function(p, n) p:AddHearts(2 * n) end },
		{ "heart_soul", "Soul Heart", function(p, n) p:AddSoulHearts(2 * n) end },
		{ "heart_black", "Black Heart", function(p, n) if n > 0 then p:AddBlackHearts(2 * n) else p:AddSoulHearts(2 * n) end end },
		{ "heart_bone", "Bone Heart", function(p, n) p:AddBoneHearts(n) end },
		{ "heart_rotten", "Rotten Heart", function(p, n) p:AddRottenHearts(2 * n) end },
		{ "heart_golden", "Golden Heart", function(p, n) p:AddGoldenHearts(n) end },
		{ "heart_eternal", "Eternal Heart", function(p, n) p:AddEternalHearts(n) end },
		{ "heart_broken", "Broken Heart", function(p, n) p:AddBrokenHearts(n) end },
	}

	local function spawnPickups(variant, n)
		local p = Isaac.GetPlayer(0)
		for _ = 1, math.min(n, 30) do
			Isaac.Spawn(EntityType.ENTITY_PICKUP, variant, 0, p.Position, RandomVector() * (2 + math.random() * 3), nil)
		end
	end

	local PICKUPS = {
		{ "coin", "Coins", function(p, n) p:AddCoins(n) end, PickupVariant.PICKUP_COIN },
		{ "bomb", "Bombs", function(p, n) p:AddBombs(n) end, PickupVariant.PICKUP_BOMB },
		{ "key", "Keys", function(p, n) p:AddKeys(n) end, PickupVariant.PICKUP_KEY },
		{ "battery", "Charge", function(p)
			for slot = 0, 1 do
				local ok = pcall(function() p:FullCharge(slot, true) end)
				if not ok then p:SetActiveCharge(p:GetActiveCharge(slot) + 12, slot) end
			end
		end, PickupVariant.PICKUP_LIL_BATTERY },
		{ "card", "Cards", nil, PickupVariant.PICKUP_TAROTCARD },
		{ "pill", "Pills", nil, PickupVariant.PICKUP_PILL },
		{ "trinket", "Trinkets", nil, PickupVariant.PICKUP_TRINKET },
		{ "chest", "Chests", nil, PickupVariant.PICKUP_CHEST },
	}

	local STATS = {
		{ "stat_damage", "Damage", "damage", 0.5 },
		{ "stat_tears", "Tears", "tears", 0.5 },
		{ "stat_speed", "Speed", "speed", 0.1 },
		{ "stat_range", "Range", "range", 0.5 },
		{ "stat_shotspeed", "Shot Speed", "shotspeed", 0.1 },
		{ "stat_luck", "Luck", "luck", 1 },
	}

	local function tabGive(x, y, w, h)
		local p = Isaac.GetPlayer(0)
		local colW = math.floor((w - 8) / 2)
		local n = ui.qty

		-- hearts
		withEnter(0, function(dx) sectionLabel("HEARTS", x + dx, y) end)
		for i, hdef in ipairs(HEARTS) do
			withEnter(i, function(dx)
				local ry = y + 10 + (i - 1) * 17
				local rx = x + dx
				local hov = hover(rx, ry, colW, 16)
				local hv = anim("hr" .. i, hov and 1 or 0, 0.3)
				rrect(rx, ry, colW, 16, mix(SURFACE, SURFACE_HI, hv))
				icon(hdef[1], rx + 1, ry)
				text(fMini, hdef[2], rx + 20, ry + 4, TEXT)
				if button("h-" .. i, rx + colW - 33, ry + 2, 15, 12, "-", { bg = SURFACE_HI, tip = "Remove " .. n .. " " .. hdef[2] }) then
					hdef[3](p, -n)
				end
				if button("h+" .. i, rx + colW - 17, ry + 2, 15, 12, "+", { on = true, tip = "Add " .. n .. " " .. hdef[2] }) then
					hdef[3](p, n)
					toast("+" .. n .. " " .. hdef[2], hdef[1])
				end
			end)
		end

		-- pickups
		local rx0 = x + colW + 8
		withEnter(0, function(dx) sectionLabel("PICKUPS", rx0 + dx, y) end)
		local tw = math.floor((colW - 9) / 4)
		for i, pk in ipairs(PICKUPS) do
			local col, row = (i - 1) % 4, (i - 1) // 4
			withEnter(i * 0.6, function(dx)
				local tx, ty = rx0 + col * (tw + 3) + dx, y + 10 + row * 29
				local tip = pk[3] and ("L: add " .. n .. " " .. pk[2] .. "   R: spawn " .. n .. " as pickups")
					or ("Spawn " .. n .. " random " .. pk[2])
				local res = button("pk" .. i, tx, ty, tw, 27, "", { right = true, tip = tip })
				local lift = math.floor((anims["pk" .. i] or 0) + 0.5)
				icon(pk[1], tx + math.floor((tw - 16) / 2), ty + 1 - lift)
				text(fMini, pk[2], tx, ty + 17 - lift, SUB, 1, tw, true)
				if res == "left" and pk[3] then
					pk[3](p, n)
					toast("+" .. n .. " " .. pk[2], pk[1])
				elseif res then
					spawnPickups(pk[4], n)
				end
			end)
		end

		-- stats
		local sy = y + 10 + 2 * 29 + 4
		withEnter(3, function(dx) sectionLabel("STATS", rx0 + dx, sy) end)
		for i, st in ipairs(STATS) do
			withEnter(3 + i, function(dx)
				local ry = sy + 10 + (i - 1) * 15
				local rx = rx0 + dx
				rrect(rx, ry, colW, 14, SURFACE)
				icon(st[1], rx + 2, ry + 1, 1, 0.75)
				text(fMini, st[2], rx + 17, ry + 3, TEXT)
				local v = A.statBonus[st[3]]
				local vs = (v >= 0 and "+" or "") .. string.format(st[4] < 1 and "%.1f" or "%d", v)
				text(fMini, vs, rx + colW - 64, ry + 3, v == 0 and DIM or (v > 0 and GREEN or RED), 1, 30, true)
				if button("s-" .. i, rx + colW - 33, ry + 1, 15, 12, "-", { bg = SURFACE_HI }) then
					A.statBonus[st[3]] = v - st[4] * n
					A.refreshStats()
				end
				if button("s+" .. i, rx + colW - 17, ry + 1, 15, 12, "+", { on = true, tip = "+" .. (st[4] * n) .. " " .. st[2] }) then
					A.statBonus[st[3]] = v + st[4] * n
					A.refreshStats()
				end
			end)
		end
		local resetY = sy + 10 + #STATS * 15 + 2
		if resetY + 12 <= y + h and button("sreset", rx0, resetY, colW, 12, "Reset stat boosts") then
			for k in pairs(A.statBonus) do A.statBonus[k] = 0 end
			A.refreshStats()
		end
	end

	-- Debug ------------------------------------------------------------------

	local DEBUG_FLAGS = {
		{ n = 3, label = "Infinite HP" }, { n = 4, label = "High Damage" },
		{ n = 6, label = "Hitboxes" }, { n = 7, label = "Dmg Numbers" },
		{ n = 8, label = "Inf Charges" }, { n = 10, label = "Quick Kill" },
		{ n = 5, label = "Room Info" }, { n = 9, label = "High Luck" },
	}

	local ROOM_TYPES = {}
	for k, v in pairs(RoomType) do ROOM_TYPES[v] = k:gsub("ROOM_", ""):lower() end

	local fps, fpsFrames, fpsStamp = 0, 0, Isaac.GetTime()
	local function tickFps()
		fpsFrames = fpsFrames + 1
		local now = Isaac.GetTime()
		if now - fpsStamp >= 1000 then
			fps = math.floor(fpsFrames * 1000 / (now - fpsStamp) + 0.5)
			fpsFrames, fpsStamp = 0, now
		end
	end

	local function fmt(n) return string.format("%.2f", n) end

	local function statLines(p)
		local level, room = game:GetLevel(), game:GetRoom()
		local enemies, total = 0, 0
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			total = total + 1
			if e:IsVulnerableEnemy() then enemies = enemies + 1 end
		end
		return {
			{ "FPS", tostring(fps), fps >= 55 and GREEN or RED },
			{ "Floor", level:GetName() },
			{ "Room", tostring(level:GetCurrentRoomIndex()) .. " " .. (ROOM_TYPES[room:GetType()] or "?") },
			{ "Seed", game:GetSeeds():GetStartSeedString() },
			{ "Entities", total .. " (" .. enemies .. " foes)" },
			{ "Damage", fmt(p.Damage) },
			{ "Tears/s", fmt(30 / (p.MaxFireDelay + 1)) },
			{ "Speed", fmt(p.MoveSpeed) },
			{ "Range", fmt(p.TearRange / 40) },
			{ "Shot spd", fmt(p.ShotSpeed) },
			{ "Luck", fmt(p.Luck) },
			{ "Pos", math.floor(p.Position.X) .. ", " .. math.floor(p.Position.Y) },
			{ "Time", string.format("%d:%02d", game.TimeCounter // 1800, (game.TimeCounter // 30) % 60) },
		}
	end

	local function clearRoom()
		for _, e in ipairs(Isaac.GetRoomEntities()) do
			if e.Type ~= A.OBLIVION_TYPE and (e:IsVulnerableEnemy() or (e:IsEnemy() and e:IsActiveEnemy(false))) then e:Kill() end
		end
	end

	local function revealMap()
		local level = game:GetLevel()
		level:ApplyMapEffect()
		level:ApplyCompassEffect(true)
		level:ApplyBlueMapEffect()
		level:UpdateVisibility()
	end

	local function gotoRoom(roomType)
		local level = game:GetLevel()
		local idx
		if roomType == "start" then
			idx = level:GetStartingRoomIndex()
		else
			idx = level:QueryRoomTypeIndex(roomType, false, RNG())
		end
		setOpen(false)
		game:StartRoomTransition(idx, Direction.NO_DIRECTION, RoomTransitionAnim.TELEPORT)
	end

	local function useItem(id)
		local p = Isaac.GetPlayer(0)
		p:UseActiveItem(id, 0, -1)
	end

	local function tabDebug(x, y, w, h)
		local p = Isaac.GetPlayer(0)
		local leftW = 118
		withEnter(0, function(dx)
			frame(x + dx, y, leftW, h, SURFACE, LINE)
			text(fMini, "LIVE", x + dx + 5, y + 3, accent())
			local lh = 9
			for i, l in ipairs(statLines(p)) do
				local ly = y + 13 + (i - 1) * lh
				if ly + lh > y + h then break end
				text(fMini, l[1], x + dx + 5, ly, SUB)
				text(fMini, clip(fMini, tostring(l[2]), leftW - 52), x + dx + 48, ly, l[3] or TEXT)
			end
		end)

		local bx = x + leftW + 6
		local bw = math.floor((w - leftW - 6 - 3) / 2)
		local bh = 13
		local by = y

		local toggles = {
			{ "God Mode", A.godMode, function() A.godMode = not A.godMode end, "Ignore all damage" },
			{ "Phase Walk", A.phaseWalk, function()
				A.phaseWalk = not A.phaseWalk
				A.refreshStats()
				if not A.phaseWalk then
					A.forEachPlayer(function(pl)
						pl.GridCollisionClass = pl.CanFly and EntityGridCollisionClass.GRIDCOLL_WALLS or EntityGridCollisionClass.GRIDCOLL_GROUND
					end)
				end
			end, "Walk over rocks and pits" },
			{ "Spike Shield", A.spikeShield, function()
				A.spikeShield = not A.spikeShield
				if A.spikeShield then A.defuseSpikedRocks() end
			end,
			  "Spiked rocks and floor spikes can't hurt you (not in Sacrifice rooms)" },
		}
		for _, d in ipairs(DEBUG_FLAGS) do
			toggles[#toggles + 1] = { d.label, ui.debugOn[d.n], function()
				Isaac.ExecuteCommand("debug " .. d.n)
				ui.debugOn[d.n] = not ui.debugOn[d.n]
			end, "Console 'debug " .. d.n .. "' - disables achievements this run" }
		end

		withEnter(1, function(dx) sectionLabel("TOGGLES", bx + dx, by) end)
		by = by + 10
		for i, t in ipairs(toggles) do
			local col, row = (i - 1) % 2, (i - 1) // 2
			withEnter(1 + row, function(dx)
				if button("dt" .. i, bx + col * (bw + 3) + dx, by + row * (bh + 2), bw, bh, t[1], { on = t[2], tip = t[4] }) then t[3]() end
			end)
		end
		by = by + math.ceil(#toggles / 2) * (bh + 2) + 3

		local actions = {
			{ "Clear Room", clearRoom },
			{ "Full Heal", function() A.forEachPlayer(function(pl) pl:SetFullHearts() end) end },
			{ "Reveal Map", revealMap },
			{ "Reroll Items", function() useItem(CollectibleType.COLLECTIBLE_D6) end },
			{ "Reroll Foes", function() useItem(CollectibleType.COLLECTIBLE_D10) end },
			{ "Trapdoor", function()
				local room = game:GetRoom()
				Isaac.GridSpawn(GridEntityType.GRID_TRAPDOOR, 0, room:FindFreeTilePosition(p.Position + Vector(0, 40), 0), true)
			end },
			{ "Spawn Q4", function() A.spawnRandomQ4(p) end },
			{ "Kill Self", function() p:Die() setOpen(false) end },
		}
		withEnter(6, function(dx) sectionLabel("ACTIONS", bx + dx, by) end)
		by = by + 10
		for i, a in ipairs(actions) do
			local col, row = (i - 1) % 2, (i - 1) // 2
			withEnter(6 + row, function(dx)
				if button("da" .. i, bx + col * (bw + 3) + dx, by + row * (bh + 2), bw, bh, a[1]) then a[2]() end
			end)
		end
		by = by + math.ceil(#actions / 2) * (bh + 2) + 3

		local gotos = {
			{ "Boss", RoomType.ROOM_BOSS }, { "Item", RoomType.ROOM_TREASURE }, { "Shop", RoomType.ROOM_SHOP },
			{ "Secret", RoomType.ROOM_SECRET }, { "Start", "start" },
		}
		if by + 22 <= y + h then
			withEnter(11, function(dx) sectionLabel("TELEPORT", bx + dx, by) end)
			by = by + 10
			local gw = math.floor((bw * 2 + 3 - 4 * 2) / 5)
			for i, g in ipairs(gotos) do
				withEnter(11, function(dx)
					if button("dg" .. i, bx + (i - 1) * (gw + 2) + dx, by, gw, bh, g[1]) then gotoRoom(g[2]) end
				end)
			end
		end
	end

	-- Settings ---------------------------------------------------------------

	local function tabSettings(x, y, w, h)
		local rows = {
			{ "Menu button", settings.showButton and "Shown" or "Hidden (F2 only)", function() settings.showButton = not settings.showButton end },
			{ "Button position", CORNERS[settings.buttonCorner], function() settings.buttonCorner = settings.buttonCorner % #CORNERS + 1 end },
			{ "Stat overlay (F3)", settings.showOverlay and "On" or "Off", function() settings.showOverlay = not settings.showOverlay end },
			{ "Freeze player in menu", settings.freezePlayer and "On" or "Off", function() settings.freezePlayer = not settings.freezePlayer end },
			{ "Animations", settings.smooth and "Smooth" or "Instant", function() settings.smooth = not settings.smooth end },
		}
		for i, r in ipairs(rows) do
			withEnter(i, function(dx)
				local ry = y + (i - 1) * 21
				local hov = hover(x, ry, w, 18)
				local hv = anim("set" .. i, hov and 1 or 0, 0.3)
				frame(x + dx, ry, w, 18, mix(SURFACE, SURFACE_HI, hv * 0.6), LINE)
				text(fSmall, r[1], x + dx + 7, ry + 3, TEXT)
				if button("setb" .. i, x + dx + w - 96, ry + 3, 92, 12, r[2], { color = accent() }) then
					r[3]()
					saveSettings()
				end
			end)
		end

		local ay = y + #rows * 21 + 2
		withEnter(#rows + 1, function(dx)
			frame(x + dx, ay, w, 18, SURFACE, LINE)
			text(fSmall, "Accent colour", x + dx + 7, ay + 3, TEXT)
			for i, ac in ipairs(ACCENTS) do
				local sx = x + dx + w - 4 - (#ACCENTS - i + 1) * 15
				local sel = settings.accent == i
				local hv = anim("acc" .. i, (hover(sx, ay + 3, 12, 12) or sel) and 1 or 0, 0.3)
				if sel then rrect(sx - 1, ay + 2, 14, 14, WHITE, 0.9) end
				rrect(sx, ay + 3 - math.floor(hv + 0.5), 12, 12, ac.c)
				if hover(sx, ay + 3, 12, 12) then
					ui.tooltip = ac.name
					if M.click then
						settings.accent = i
						saveSettings()
						sfx:Play(SoundEffect.SOUND_BUTTON_PRESS, 0.45)
					end
				end
			end
		end)

		withEnter(#rows + 2, function(dx)
			local iy = ay + 26
			text(fMini, "Altar Core v" .. A.VERSION .. "  -  " .. #A.DATA .. " custom items", x + dx, iy, SUB)
			text(fMini, "F2 menu   F3 overlay   F4 console", x + dx, iy + 10, DIM)
		end)
	end

	-- Combos -----------------------------------------------------------------

	local function itemInfo(key)
		return { id = A.ITEM[key], gfx = "gfx/items/collectibles/" .. key .. ".png" }
	end

	local function tabCombos(x, y, w, h)
		local p = Isaac.GetPlayer(0)
		local rowH = 26
		local perPage = math.max(1, math.floor((h - 16) / (rowH + 2)))
		local list = A.COMBOS or {}
		for i = 1, perPage do
			local c = list[i + ui.page * perPage]
			if not c then break end
			withEnter(i, function(dx)
				local rx, ry = x + dx, y + (i - 1) * (rowH + 2)
				local on = A.hasCombo(p, c.key)
				local hov = hover(rx, ry, w, rowH)
				local hv = anim("cb" .. i, hov and 1 or 0, 0.3)
				local border = on and mix(GOLD, WHITE, 0.2 * math.sin(Isaac.GetFrameCount() / 10) + 0.2) or mix(LINE, accent(), hv)
				frame(rx, ry, w, rowH, mix(SURFACE, SURFACE_HI, hv), border)
				if on then rect(rx + 1, ry + 2, 2, rowH - 4, GOLD) end
				text(fSmall, c.name, rx + 7, ry + 1, on and GOLD or TEXT)
				text(fMini, clip(fMini, c.desc, w - 30 - #c.items * 17 - 44), rx + 7, ry + 14, SUB)
				local ix = rx + w - 46 - #c.items * 17
				for k, key in ipairs(c.items) do
					local owned = p:HasCollectible(A.ITEM[key])
					drawItem(itemInfo(key), ix + (k - 1) * 17, ry + 5, owned and 1 or 0.35, 0.5)
				end
				if button("cbg" .. i, rx + w - 42, ry + 6, 38, 14, on and "Active" or "Give", { on = on, tip = "Give every item in " .. c.name }) and not on then
					A.giveCombo(c.key, p)
				end
				if hov then ui.tooltip = c.name .. ": " .. c.desc end
			end)
		end
		local owned = 0
		for _, c in ipairs(list) do if A.hasCombo(p, c.key) then owned = owned + 1 end end
		text(fMini, owned .. " / " .. #list .. " combos active", x, y + h - 11, DIM)
		if button("cball", x + 92, y + h - 13, 60, 12, "Give all", { tip = "Unlock every combo at once" }) then
			for _, c in ipairs(list) do A.giveCombo(c.key, p) end
		end
		pager(x, y + h - 13, w, #list, perPage)
	end

	-- Warp -------------------------------------------------------------------

	-- Segmented sub-tab chips; returns nothing, updates ui[key].
	local function subTabs(x, y, names, key)
		local cx = x
		for i, m in ipairs(names) do
			local cw = fMini:GetStringWidth(m) + 14
			if button(key .. i, cx, y, cw, 14, m, { on = ui[key] == i }) and ui[key] ~= i then
				ui[key] = i
				ui.page = 0
				ui.tabT = 0.3
			end
			cx = cx + cw + 3
		end
	end

	-- Card with a portrait on the left and a wrapped name. Returns "left"/"right"/nil.
	local function portraitCard(id, x, y, w, h, path, name, opts)
		opts = opts or {}
		local hov = hover(x, y, w, h)
		local hv = anim(id, hov and 1 or 0, 0.3)
		local press = anim(id .. ":p", 0, 0.15)
		local lift = math.floor(hv + 0.5)
		local border = opts.on and accent() or mix(opts.warn and mix(LINE, GOLD, 0.5) or LINE, accent(), hv)
		rrect(x, y + 1, w, h, BLACK, 0.45)
		frame(x, y - lift, w, h, opts.on and mix(SURFACE_HI, accent(), 0.25) or mix(SURFACE, SURFACE_HI, hv), border)
		local ps = h - 6
		rrect(x + 3, y + 3 - lift, ps, ps, BG, 0.8)
		drawPortrait(path, name, x + 3, y + 3 - lift, ps, 1)
		local lines = wrap(fMini, name, w - ps - 10)
		local ty = y - lift + math.floor((h - #lines * 9) / 2) - 1
		for i = 1, math.min(2, #lines) do
			text(fMini, lines[i], x + ps + 7, ty + (i - 1) * 9, opts.warn and GOLD or TEXT)
		end
		if press > 0.01 then rrect(x, y - lift, w, h, WHITE, press * 0.3) end
		if hov and opts.tip then ui.tooltip = opts.tip end
		if hov and (M.click or (M.rclick and opts.right)) then
			anims[id .. ":p"] = 1
			ripple(x, y - lift, w, h)
			sfx:Play(SoundEffect.SOUND_BUTTON_PRESS, 0.45)
			return M.click and "left" or "right"
		end
	end

	local WARP_MODES = { "Rooms", "Floors", "Bosses" }

	local function tabBosses(x, y, w, h)
		local cols = 4
		local cw = math.floor((w - (cols - 1) * 3) / cols)
		local ch = 30
		local rows = math.max(1, math.floor((h - 16) / (ch + 3)))
		local perPage = cols * rows
		local list = A.BOSSES
		ui.page = clamp(ui.page, 0, math.max(0, math.ceil(#list / perPage) - 1))
		for slot = 0, perPage - 1 do
			local b = list[ui.page * perPage + slot + 1]
			if not b then break end
			local col, row = slot % cols, slot // cols
			withEnter(row * 0.8 + col * 0.3, function(dx)
				local file = A.BOSS_PORTRAIT[b[1]]
				local tip = "L: go to the boss room and fight " .. b[1] .. "   R: spawn here" .. (b[4] and "   (may be unstable)" or "")
				local res = portraitCard("bs" .. slot, x + col * (cw + 3) + dx, y + row * (ch + 3), cw, ch,
					A.bossPortraitPath(b), b[1], { tip = tip, right = true, warn = b[4] })
				if res then
					if res == "left" then setOpen(false) end
					A.fightBoss(b, res == "right")
					toast((res == "right" and "Spawned " or "Summoning ") .. b[1])
				end
			end)
		end
		text(fMini, #list .. " bosses  -  gold = may be unstable", x, y + h - 11, DIM)
		pager(x, y + h - 13, w, #list, perPage)
	end

	local function tabWarp(x, y, w, h)
		subTabs(x, y, WARP_MODES, "warpMode")
		local gy = y + 19
		local mode = ui.warpMode
		if mode == 3 then
			tabBosses(x, gy, w, h - 19)
			return
		end
		local cols = 3
		local bw = math.floor((w - (cols - 1) * 3) / cols)
		local bh = 13
		local rows = math.max(1, math.floor((h - 19 - 16) / (bh + 2)))
		local list = mode == 1 and A.ROOMS or A.FLOORS
		local perPage = cols * rows
		for slot = 0, perPage - 1 do
			local v = list[ui.page * perPage + slot + 1]
			if not v then break end
			local col, row = slot % cols, slot // cols
			withEnter(row * 0.8 + col * 0.3, function(dx)
				local bx, by = x + col * (bw + 3) + dx, gy + row * (bh + 2)
				local tip, opts
				if mode == 1 then
					tip = "Teleport to the " .. v[1] .. " room"
				elseif mode == 2 then
					tip = "Warp to " .. v[1] .. " (console 'stage " .. v[2] .. "' - disables achievements this run)"
				else
					tip = "L: teleport to the boss room and fight " .. v[1] .. "   R: spawn here" .. (v[4] and "   (may be unstable)" or "")
				end
				opts = { tip = tip, right = mode == 3, color = (mode == 3 and v[4]) and GOLD or nil }
				local res = button("wp" .. slot, bx, by, bw, bh, clip(fMini, v[1], bw - 4), opts)
				if res then
					if mode == 1 then setOpen(false) A.warpRoom(v)
					elseif mode == 2 then setOpen(false) A.warpFloor(v)
					else
						if res == "left" then setOpen(false) end
						A.fightBoss(v, res == "right")
						toast((res == "right" and "Spawned " or "Summoning ") .. v[1])
					end
				end
			end)
		end
		text(fMini, #list .. " " .. WARP_MODES[mode]:lower(), x, y + h - 11, DIM)
		pager(x, y + h - 13, w, #list, perPage)
	end

	-- Player -----------------------------------------------------------------

	local PLAYER_MODES = { "Characters", "Curses" }

	local function tabCharacters(x, y, w, h)
		local current = Isaac.GetPlayer(0):GetPlayerType()
		local cols = 4
		local cw = math.floor((w - (cols - 1) * 3) / cols)
		local ch = 26
		local rows = math.max(1, math.floor((h - 16) / (ch + 3)))
		local perPage = cols * rows
		local list = A.CHARS
		ui.page = clamp(ui.page, 0, math.max(0, math.ceil(#list / perPage) - 1))
		for slot = 0, perPage - 1 do
			local c = list[ui.page * perPage + slot + 1]
			if not c then break end
			local col, row = slot % cols, slot // cols
			withEnter(row * 0.8 + col * 0.3, function(dx)
				if portraitCard("ch" .. slot, x + col * (cw + 3) + dx, y + row * (ch + 3), cw, ch,
					"gfx/ui/stage/playerportrait_" .. c[3] .. ".png", c[1], { on = current == c[2], tip = "Become " .. c[1] }) then
					if A.setCharacter(c) then toast("You are now " .. c[1]) else toast("Can't change character in this game version") end
				end
			end)
		end
		text(fMini, #list .. " characters", x, y + h - 11, DIM)
		pager(x, y + h - 13, w, #list, perPage)
	end

	local function tabPlayer(x, y, w, h)
		subTabs(x, y, PLAYER_MODES, "playerMode")
		if ui.playerMode == 1 then
			tabCharacters(x, y + 19, w, h - 19)
			return
		end
		local cy = y + 19
		local bh = 14
		local level = game:GetLevel()
		local curses = level:GetCurses()
		withEnter(8, function(dx) sectionLabel("CURSES", x + dx, cy) end)
		local cw = math.floor((w - 4 * 3) / 5)
		for i, c in ipairs(A.CURSES) do
			local col, row = (i - 1) % 5, (i - 1) // 5
			withEnter(9, function(dx)
				local on = curses & c[2] ~= 0
				if button("cu" .. i, x + col * (cw + 3) + dx, cy + 10 + row * (bh + 2), cw, bh, c[1],
					{ on = on, tip = (on and "Remove" or "Add") .. " Curse of " .. c[1] }) then
					if on then level:RemoveCurses(c[2]) else level:AddCurse(c[2], true) end
				end
			end)
		end
		local col = #A.CURSES % 5
		local row = #A.CURSES // 5
		withEnter(9, function(dx)
			if button("cuoff", x + col * (cw + 3) + dx, cy + 10 + row * (bh + 2), cw * (5 - col) + 3 * (4 - col), bh, "Remove all curses") then
				level:RemoveCurses(level:GetCurses())
			end
		end)
	end

	-- Console ----------------------------------------------------------------

	local QUICK = { "help", "bosses", "combo all", "god", "heal", "blackhole", "q4 3", "map" }

	local function runConsole(line)
		if line:match("^%s*$") then return end
		local msg, isErr = A.runCommand(line)
		consoleLog(line, msg, isErr)
		table.insert(ui.history, line)
		ui.histPos = #ui.history + 1
		sfx:Play(isErr and SoundEffect.SOUND_THUMBS_DOWN or SoundEffect.SOUND_BUTTON_PRESS, 0.5)
	end

	local PROMPT = "C:\\Altar> "
	local BANNER = {
		{ "Altar Console [Version " .. A.VERSION .. "]", "out" },
		{ "(c) Altar. Type 'help'. Chain with ';'  e.g.  give overclock 3, sad onion; heal", "dim" },
		{ "", "out" },
	}

	local function tabConsole(x, y, w, h)
		local lineH = 10

		-- Windows Terminal tab strip
		frame(x, y, w, h, TERM_BG, LINE)
		rect(x + 1, y + 1, w - 2, 15, BG)
		frame(x + 3, y + 2, 118, 14, TERM_BG, LINE)
		rect(x + 4, y + 15, 116, 1, TERM_BG)
		text(fMono, ">_", x + 8, y + 4, accent())
		text(fMini, "Command Prompt", x + 22, y + 5, TEXT)
		text(fMini, "x", x + 110, y + 5, DIM)
		text(fMini, "+", x + 128, y + 5, DIM)
		-- quick commands on the right of the strip
		local qx = x + w - 3
		for i = #QUICK, 1, -1 do
			local q = QUICK[i]
			local qw = fMini:GetStringWidth(q) + 8
			qx = qx - qw - 2
			if qx < x + 142 then break end
			if button("q" .. i, qx, y + 3, qw, 11, q, { tip = "Run '" .. q .. "'", bg = BG }) then runConsole(q) end
		end

		-- scrollback: banner + log, newest at the bottom, then the live prompt line
		local top = y + 19
		local fit = math.floor((h - 22) / lineH) - 1
		local lines = {}
		for _, l in ipairs(BANNER) do lines[#lines + 1] = l end
		for _, l in ipairs(ui.log) do
			if l[2] == "in" then
				lines[#lines + 1] = { PROMPT .. l[1]:gsub("^> ", ""), "in" }
			else
				lines[#lines + 1] = l
			end
		end
		local first = math.max(1, #lines - fit + 1)
		for i = first, #lines do
			local l = lines[i]
			local c = l[2] == "err" and RED or l[2] == "dim" and DIM or l[2] == "in" and WHITE or TERM_TEXT
			text(fMono, clip(fMono, l[1], w - 10), x + 5, top + (i - first) * lineH, c)
		end

		-- prompt line with blinking block cursor and ghost autocomplete
		local iy = top + (math.min(#lines, fit)) * lineH
		local sugg = A.suggest(ui.input)
		ui.firstSuggestion = sugg[1] and sugg[1].text
		local shown = clip(fMono, PROMPT .. ui.input, w - 20)
		text(fMono, shown, x + 5, iy, WHITE)
		local cx = x + 5 + fMono:GetStringWidth(shown)
		local ghost = ui.firstSuggestion and ui.firstSuggestion:sub(1, #ui.input):lower() == ui.input:lower()
			and ui.firstSuggestion:sub(#ui.input + 1) or ""
		if ghost ~= "" and ui.consoleFocus then
			text(fMono, clip(fMono, ghost, x + w - cx - 12), cx + 1, iy, DIM)
		end
		if ui.consoleFocus and (Isaac.GetFrameCount() // 30) % 2 == 0 then
			rect(cx + 1, iy + 1, 5, lineH - 2, TERM_TEXT)
		end
		if not ui.consoleFocus and ui.input == "" then
			text(fMono, "(click to type)", cx + 2, iy, DIM)
		end

		-- suggestion popup above the prompt (PowerShell style list)
		if ui.consoleFocus and #sugg > 0 and ui.input ~= "" then
			local n = math.min(5, #sugg)
			local pw2 = 0
			for i = 1, n do pw2 = math.max(pw2, fMini:GetStringWidth(sugg[i].label)) end
			pw2 = math.min(w - 20, pw2 + 12)
			local ph2 = n * 11 + 4
			local px2 = x + 5 + fMono:GetStringWidth(PROMPT)
			local py2 = math.max(top, iy - ph2 - 2)
			frame(px2, py2, pw2, ph2, SURFACE, LINE)
			for i = 1, n do
				local ry = py2 + 2 + (i - 1) * 11
				local hov = hover(px2, ry, pw2, 11)
				if i == 1 or hov then rect(px2 + 1, ry, pw2 - 2, 11, i == 1 and mix(SURFACE, accent(), 0.3) or SURFACE_HI) end
				text(fMini, clip(fMini, sugg[i].label, pw2 - 10), px2 + 5, ry + 1, TEXT)
				if hov and M.click then
					ui.input = sugg[i].text
					ui.consoleFocus = true
					M.click = false
				end
			end
		end

		local inside = hover(x, top, w, h - 19)
		if inside then ui.tooltip = "Enter: run   Tab: accept   Ctrl+V: paste   Up/Down: history   , more items   ; more commands" end
		if M.click then ui.consoleFocus = inside end
	end

	local TAB_DRAW = { tabMods, tabItems, tabGive, tabCombos, tabWarp, tabPlayer, tabDebug, tabConsole, tabSettings }

	---------------------------------------------------------------------------
	-- Panel
	---------------------------------------------------------------------------

	local function drawPanel(W, H)
		local t = ui.openT
		local e = easeOut(t)
		alpha = e
		rect(0, 0, W, H, BLACK, 0.6)

		local maxT = anim("maxT", ui.maxed and 1 or 0, 0.25)
		local pw = math.floor(math.min(430, W - 16) + (W - 8 - math.min(430, W - 16)) * maxT)
		local ph = math.floor(math.min(250, H - 12) + (H - 8 - math.min(250, H - 12)) * maxT)
		local x = math.floor((W - pw) / 2)
		local y = math.floor((H - ph) / 2 + (1 - easeBack(t)) * 18)
		local a = accent()
		local TB = 22 -- title bar height

		-- soft shadow, 1px border, Mica-tinted body
		for i = 1, 4 do rwin(x - i, y - i + 3, pw + i * 2, ph + i * 2, BLACK, 0.09) end
		rwin(x - 1, y - 1, pw + 2, ph + 2, LINE)
		rwin(x, y, pw, ph, mix(PANEL, a, 0.035))

		-- title bar: icon, title, minimize / maximize / close
		gem.Scale = Vector(0.5, 0.5)
		gem.Color = Color(1, 1, 1, alpha, 0, 0, 0)
		gem:Render(Vector(x + 7, y + 5), Vector.Zero, Vector.Zero)
		gem.Scale = Vector(1, 1)
		text(fMini, "Altar  -  " .. TABS[ui.tab].name, x + 24, y + 7, SUB)
		local function caption(id, cx0, kind)
			local hov = hover(cx0, y, 30, TB)
			local hv = anim(id, hov and 1 or 0, 0.35)
			if hv > 0.01 then rect(cx0, y + (kind == "close" and 0 or 0), 30, TB, kind == "close" and CLOSE_RED or SURFACE_HI, hv) end
			local gx, gy = cx0 + 11, y + 7
			if kind == "min" then
				rect(gx, gy + 4, 9, 1, TEXT)
			elseif kind == "max" then
				if ui.maxed then
					rect(gx + 2, gy, 7, 1, TEXT) rect(gx + 8, gy, 1, 7, TEXT)
					gx, gy = gx, gy + 2
				end
				rect(gx, gy, 7, 1, TEXT) rect(gx, gy + 6, 7, 1, TEXT)
				rect(gx, gy, 1, 7, TEXT) rect(gx + 6, gy, 1, 7, TEXT)
			else
				for k = 0, 8 do
					rect(gx + k, gy + k, 1, 1, TEXT)
					rect(gx + 8 - k, gy + k, 1, 1, TEXT)
				end
			end
			if hov and M.click then
				sfx:Play(SoundEffect.SOUND_BUTTON_PRESS, 0.4)
				return true
			end
		end
		if caption("capClose", x + pw - 30, "close") then setOpen(false) end
		if caption("capMax", x + pw - 60, "max") then ui.maxed = not ui.maxed end
		if caption("capMin", x + pw - 90, "min") then setOpen(false) end

		-- sidebar, Windows Settings style
		local sbw = 94
		local py = y + TB + 4
		gem.Color = Color(1, 1, 1, alpha, 0, 0, 0)
		gem:Render(Vector(x + 7, py + 1), Vector.Zero, Vector.Zero)
		text(fSmall, "Altar", x + 34, py + 2, TEXT)
		text(fMini, "v" .. A.VERSION .. " - Local", x + 34, py + 15, DIM)

		local navY, step = py + 32, 19
		local selY = anim("navSel", navY + (ui.tab - 1) * step, 0.3)
		rrect(x + 5, selY, sbw - 8, step - 2, SURFACE, 1)
		local pill = math.floor(6 + 4 * (1 - math.abs(selY - (navY + (ui.tab - 1) * step)) / step))
		rrect(x + 5, selY + math.floor((step - 2 - pill) / 2), 3, pill, a)
		for i, tab in ipairs(TABS) do
			local ty = navY + (i - 1) * step
			local hov = hover(x + 5, ty, sbw - 8, step - 2)
			local hv = anim("nav" .. i, hov and ui.tab ~= i and 1 or 0, 0.3)
			if hv > 0.01 then rrect(x + 5, ty, sbw - 8, step - 2, SURFACE, 0.6 * hv) end
			icon("tab_" .. tab.id, x + 13, ty + 2, ui.tab == i and 1 or 0.75, 0.75)
			text(fSmall, tab.name, x + 28, ty + 2, ui.tab == i and TEXT or SUB)
			if hov and M.click then setTab(i) end
		end

		-- content header: big page title like Windows Settings
		local cx, cw = x + sbw + 8, pw - sbw - 16
		local tab = TABS[ui.tab]
		withEnter(0, function(dx)
			fTitle:DrawStringScaled(tab.name, cx + dx, py + 1, 0.55, 0.55, KColor(1, 1, 1, alpha), 0, false)
			text(fMini, tab.sub, cx + dx, py + 13, DIM)
		end)
		if tab.id == "items" or tab.id == "give" then qtyStepper(cx + cw - 66, py + 2) end

		-- body
		local by = py + 26
		local bh = y + ph - 16 - by
		ui.tooltip = nil
		TAB_DRAW[ui.tab](cx, by, cw, bh)

		-- status bar
		local tipA = anim("tipA", ui.tooltip and 1 or 0, 0.25)
		rect(x + 1, y + ph - 14, pw - 2, 1, LINE)
		if ui.tooltip then ui.lastTip = ui.tooltip end
		local tip = ui.lastTip or ""
		text(fMini, clip(fMini, tip, pw - 90), x + 8, y + ph - 11, TEXT, tipA)
		if tipA < 0.99 then
			text(fMini, "Ready", x + 8, y + ph - 11, DIM, 1 - tipA)
		end
		text(fMini, "F2 close   F4 console", x + pw - 82, y + ph - 11, DIM)

		-- click ripples
		for i = #ripples, 1, -1 do
			local r = ripples[i]
			r.t = r.t + 0.08
			if r.t >= 1 then
				table.remove(ripples, i)
			else
				local g = math.floor(r.t * 4)
				frame(r.x - g, r.y - g, r.w + g * 2, r.h + g * 2, WHITE, WHITE, (1 - r.t) * 0.12)
			end
		end
		alpha = 1
	end

	---------------------------------------------------------------------------
	-- Overlay, button, toasts, cursor
	---------------------------------------------------------------------------

	local function drawOverlay(W)
		local lines = statLines(Isaac.GetPlayer(0))
		local ow, lh = 120, 9
		local x, y = W - ow - 6, 64
		frame(x, y, ow, #lines * lh + 8, BG, LINE, 0.85)
		rect(x + 1, y + 2, 2, #lines * lh + 4, accent(), 0.9)
		for i, l in ipairs(lines) do
			local ly = y + 4 + (i - 1) * lh
			text(fMini, l[1], x + 7, ly, SUB)
			text(fMini, clip(fMini, tostring(l[2]), ow - 56), x + 50, ly, l[3] or TEXT)
		end
	end

	local function buttonPos(W, H)
		local c = settings.buttonCorner
		if c == 1 then return 8, H - 34
		elseif c == 2 then return math.floor(W / 2) - 13, 4
		elseif c == 3 then return W - 34, math.floor(H / 2) - 13
		end
		return math.floor(W / 2) - 13, H - 34
	end

	local function drawMenuButton(W, H)
		local bx, by = buttonPos(W, H)
		local hov = hover(bx, by, 26, 26)
		local hv = anim("gemBtn", (hov or ui.open) and 1 or 0, 0.25)
		local pulse = (math.sin(Isaac.GetFrameCount() / 14) + 1) / 2
		local a = accent()
		local grow = math.floor(hv * 2 + 0.5)
		rrect(bx - 2 - grow, by - 2 - grow, 30 + grow * 2, 30 + grow * 2, a, 0.15 + pulse * 0.2 + hv * 0.4)
		frame(bx - grow, by - grow, 26 + grow * 2, 26 + grow * 2, BG, mix(LINE, a, hv), 0.92)
		local s = 1 + hv * 0.12
		gem.Scale = Vector(s, s)
		gem.Color = Color(1, 1, 1, 1, hv * 0.12, hv * 0.12, hv * 0.12)
		gem:Render(Vector(bx + 13 - 12 * s, by + 13 - 12 * s - hv), Vector.Zero, Vector.Zero)
		gem.Scale = Vector(1, 1)

		local tipT = anim("gemTip", (hov and not ui.open) and 1 or 0, 0.25)
		if tipT > 0.01 then
			local tip = "Altar menu  [F2]"
			local tw = fMini:GetStringWidth(tip) + 10
			local tx = math.min(bx + 32 + math.floor((1 - tipT) * -6), W - tw - 2)
			local saved = alpha
			alpha = tipT
			frame(tx, by + 7, tw, 13, BG, LINE, 0.95)
			text(fMini, tip, tx + 5, by + 10, TEXT)
			alpha = saved
		end
		if hov and M.click then setOpen(not ui.open) end
	end

	local function drawToasts(W)
		local y = 6
		for i = #ui.toasts, 1, -1 do
			local t = ui.toasts[i]
			t.t = t.t + 1
			if t.t > t.life then table.remove(ui.toasts, i) end
		end
		for i, t in ipairs(ui.toasts) do
			local inT = easeBack(t.t / 14)
			local outT = clamp((t.life - t.t) / 16)
			local a = math.min(easeOut(t.t / 10), outT)
			local tw = fSmall:GetStringWidth(t.msg) + 34
			local x = math.floor((W - tw) / 2)
			local ty = math.floor(y - (1 - inT) * 14)
			alpha = a
			frame(x, ty, tw, 20, BG, LINE, 0.95)
			rect(x + 2, ty + 18, (tw - 4) * (1 - t.t / t.life), 1, accent())
			if t.icon then
				icon(t.icon, x + 4, ty + 2)
			else
				gem.Scale = Vector(0.66, 0.66)
				gem.Color = Color(1, 1, 1, a, 0, 0, 0)
				gem:Render(Vector(x + 4, ty + 2), Vector.Zero, Vector.Zero)
				gem.Scale = Vector(1, 1)
			end
			text(fSmall, t.msg, x + 24, ty + 3, TEXT)
			alpha = 1
			y = y + math.floor(22 * a + 0.5)
		end
	end

	local function drawCursor(a)
		local x, y = math.floor(M.x), math.floor(M.y)
		local saved = alpha
		alpha = a
		for i = 0, 8 do rect(x - 1, y + i - 1, math.min(i, 6) + 3, 1, BLACK) end
		rect(x + 1, y + 8, 4, 4, BLACK)
		local c = M.l and accent() or WHITE
		for i = 0, 6 do rect(x, y + i, math.min(i, 5) + 1, 1, c) end
		rect(x + 2, y + 7, 2, 3, c)
		alpha = saved
	end

	---------------------------------------------------------------------------
	-- Keyboard text entry for item search
	---------------------------------------------------------------------------

	local LETTERS = {}
	for c = 65, 90 do LETTERS[#LETTERS + 1] = { c, string.char(c + 32) } end
	for c = 48, 57 do LETTERS[#LETTERS + 1] = { c, string.char(c) } end
	LETTERS[#LETTERS + 1] = { Keyboard.KEY_SPACE, " " }
	LETTERS[#LETTERS + 1] = { Keyboard.KEY_PERIOD, "." }
	LETTERS[#LETTERS + 1] = { Keyboard.KEY_MINUS, "-" }
	LETTERS[#LETTERS + 1] = { Keyboard.KEY_APOSTROPHE, "'" }
	LETTERS[#LETTERS + 1] = { Keyboard.KEY_COMMA, "," }
	LETTERS[#LETTERS + 1] = { Keyboard.KEY_SEMICOLON, ";" }

	-- Ctrl+V: the Lua sandbox can't read the Windows clipboard, so the Altar app
	-- forwards it into this mod's save file as "clip" and we read it from there.
	local function readClipboard()
		local ok, data = pcall(json.decode, mod:LoadData())
		if not ok or type(data) ~= "table" or type(data.clip) ~= "string" or data.clip == "" then return nil end
		local s = data.clip:gsub("[\r\n]+", "; "):gsub("[^%w%s%p]", "")
		return s:sub(1, 300)
	end

	local function paste(into)
		local clip = readClipboard()
		if not clip then
			toast("Nothing to paste - keep the Altar app open to link your clipboard")
			return into
		end
		sfx:Play(SoundEffect.SOUND_PAPER_IN, 0.4)
		return into .. clip
	end

	local function updateTyping()
		local typed = ""
		for _, k in ipairs(LETTERS) do
			if keyPressed(k[1]) then typed = typed .. k[2] end
		end
		local ctrl = Input.IsButtonPressed(Keyboard.KEY_LEFT_CONTROL, 0) or Input.IsButtonPressed(Keyboard.KEY_RIGHT_CONTROL, 0)
		local pasted = ctrl and typed:find("v", 1, true)
		if ctrl then typed = "" end
		if pasted and ui.open then
			if ui.consoleFocus then ui.input = paste(ui.input) elseif ui.searchFocus then ui.search = paste(ui.search) end
		end
		local back, enter = keyPressed(Keyboard.KEY_BACKSPACE), keyPressed(Keyboard.KEY_ENTER)
		local esc, tab = keyPressed(Keyboard.KEY_ESCAPE), keyPressed(Keyboard.KEY_TAB)
		local up, down = keyPressed(Keyboard.KEY_UP), keyPressed(Keyboard.KEY_DOWN)
		if not ui.open then return end

		if ui.searchFocus then
			if typed ~= "" and #ui.search < 24 then
				ui.search = ui.search .. typed
				ui.page = 0
			end
			if back then ui.search = ui.search:sub(1, -2) ui.page = 0 end
			if enter or esc then ui.searchFocus = false end
		elseif ui.consoleFocus then
			if typed ~= "" and #ui.input < 60 then ui.input = ui.input .. typed end
			if back then ui.input = ui.input:sub(1, -2) end
			if tab and ui.firstSuggestion then ui.input = ui.firstSuggestion end
			if up and #ui.history > 0 then
				ui.histPos = math.max(1, ui.histPos - 1)
				ui.input = ui.history[ui.histPos] or ""
			elseif down and #ui.history > 0 then
				ui.histPos = math.min(#ui.history + 1, ui.histPos + 1)
				ui.input = ui.history[ui.histPos] or ""
			end
			if enter then
				local line = ui.input
				ui.input = ""
				runConsole(line)
			end
			if esc then ui.consoleFocus = false end
		end
	end

	local function drawBanner(W, H)
		local b = ui.banner
		if not b then return end
		b.t = b.t + 1
		local life = 150
		if b.t > life then ui.banner = nil return end
		local inT = easeBack(b.t / 18)
		local a = math.min(easeOut(b.t / 12), clamp((life - b.t) / 20))
		alpha = a
		local cy = math.floor(H * 0.26)
		local bw = math.floor(260 * inT)
		local bx = math.floor((W - bw) / 2)
		rect(bx, cy - 4, bw, 40, BG, 0.85)
		rect(bx, cy - 4, bw, 1, GOLD)
		rect(bx, cy + 35, bw, 1, GOLD)
		local sweep = (b.t * 6) % (bw + 60) - 30
		rect(bx + math.max(0, sweep), cy - 4, math.min(18, math.max(0, bw - sweep)), 40, WHITE, 0.08)
		local title = b.title
		local tw = fTitle:GetStringWidth(title) * 0.5
		fTitle:DrawStringScaled(title, math.floor((W - tw) / 2), cy, 0.5, 0.5, KColor(GOLD[1], GOLD[2], GOLD[3], a), 0, false)
		text(fSmall, b.sub, 0, cy + 18, TEXT, 1, W, true)
		alpha = 1
	end

	---------------------------------------------------------------------------
	-- Callbacks
	---------------------------------------------------------------------------

	---------------------------------------------------------------------------
	-- Preloading: warm every portrait and item icon a few per frame after the
	-- run starts, so opening Warp / Player / Items never hitches.
	---------------------------------------------------------------------------

	function A.bossPortraitPath(b)
		local file = A.BOSS_PORTRAIT[b[1]]
		if not file then return nil end
		return file:find("^gfx/") and file or ("gfx/ui/boss/portrait_" .. file .. ".png")
	end

	local preload = { queue = nil, total = 0, done = 0, shownT = 0 }

	local function buildPreload()
		local q = {}
		for _, b in ipairs(A.BOSSES) do
			local path = A.bossPortraitPath(b)
			if path then q[#q + 1] = { "portrait", path } end
		end
		for _, c in ipairs(A.CHARS) do q[#q + 1] = { "portrait", "gfx/ui/stage/playerportrait_" .. c[3] .. ".png" } end
		for _, info in ipairs(A.getCatalogue()) do
			if info.gfx then q[#q + 1] = { "item", info.gfx } end
		end
		for _, info in ipairs(A.DATA) do
			for f = 0, 5 do q[#q + 1] = { "item", "gfx/items/collectibles/altar/" .. info.key .. "_" .. f .. ".png" } end
		end
		preload.queue, preload.total, preload.done = q, #q, 0
	end

	local function preloadStep()
		local q = preload.queue
		if not q or #q == 0 then return end
		local loads = 0
		while #q > 0 and loads < 10 do
			local job = q[#q]
			if job[1] == "portrait" then
				local p = portrait(job[2])
				if not p.box then break end -- waiting for this frame's measure budget
			else
				itemSprite(job[2])
			end
			q[#q] = nil
			preload.done = preload.done + 1
			loads = loads + 1
		end
		if #q == 0 then saveSettings() end
	end

	local function drawPreload(W, H)
		local active = preload.queue and #preload.queue > 0
		preload.shownT = anim("preloadT", active and 1 or 0, 0.1)
		if preload.shownT < 0.02 then return end
		local saved = alpha
		alpha = preload.shownT
		local w, x, y = 96, W - 104, H - 20
		frame(x, y, w, 12, BG, LINE, 0.9)
		local k = preload.total > 0 and preload.done / preload.total or 1
		rect(x + 2, y + 9, (w - 4) * k, 1, accent())
		text(fMini, "Loading assets  " .. math.floor(k * 100) .. "%", x + 5, y + 1, SUB)
		alpha = saved
	end

	function A.closeMenu() setOpen(false) end

	local cursorA = 0

	function mod:altarRender()
		measureBudget = 2
		if not preload.queue then buildPreload() end
		preloadStep()
		tickFps()
		updateMouse()
		local W, H = Isaac.GetScreenWidth(), Isaac.GetScreenHeight()

		local typing = ui.open and (ui.searchFocus or ui.consoleFocus)
		if keyPressed(Keyboard.KEY_F2) then setOpen(not ui.open) end
		if keyPressed(Keyboard.KEY_F4) then
			for i, tab in ipairs(TABS) do
				if tab.id == "console" then
					if ui.open and ui.tab == i then setOpen(false) else setOpen(true) setTab(i) ui.consoleFocus = true end
				end
			end
		end
		if keyPressed(Keyboard.KEY_F3) and not typing then
			settings.showOverlay = not settings.showOverlay
			saveSettings()
		end
		updateTyping()

		-- cutscenes own the screen
		local cutscene = A.cutsceneActive and A.cutsceneActive()
		if cutscene and ui.open then setOpen(false) end

		local paused = game:IsPaused() and not ui.open
		local speed = settings.smooth and 0.09 or 1
		ui.openT = ui.open and math.min(1, ui.openT + speed) or math.max(0, ui.openT - speed * 1.4)
		ui.tabT = math.min(1, ui.tabT + (settings.smooth and 0.06 or 1))

		if not cutscene then
			if settings.showOverlay and not paused and ui.openT == 0 then drawOverlay(W) end
			if ui.openT > 0 then drawPanel(W, H) end
			if (settings.showButton or ui.open) and not paused and game:GetHUD():IsVisible() then
				drawMenuButton(W, H)
			end
			drawPreload(W, H)
		end
		drawToasts(W)
		drawBanner(W, H)

		cursorA = anim("cursorA", (ui.open or M.idle < 90) and 1 or 0, 0.2)
		if cursorA > 0.01 then drawCursor(cursorA) end
	end
	mod:AddCallback(ModCallbacks.MC_POST_RENDER, mod.altarRender)

	function mod:altarFreeze(p)
		if ui.open and settings.freezePlayer then
			p.ControlsEnabled = false
			ui.frozePlayers = true
		end
		if A.phaseWalk then
			-- pass through rocks and pits but never out of the room
			p.GridCollisionClass = EntityGridCollisionClass.GRIDCOLL_WALLS
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_PLAYER_UPDATE, mod.altarFreeze)

	function mod:altarUiStart()
		loadSettings()
		local enabled = 0
		for _, m in ipairs(A.modList) do if m.enabled then enabled = enabled + 1 end end
		toast(#A.modList > 0 and ("Altar loaded - " .. enabled .. " mods enabled") or "Altar loaded - press F2")
	end
	mod:AddCallback(ModCallbacks.MC_POST_GAME_STARTED, mod.altarUiStart)

	function mod:altarUiExit()
		saveSettings()
		setOpen(false)
	end
	mod:AddCallback(ModCallbacks.MC_PRE_GAME_EXIT, mod.altarUiExit)

	function mod:altarUiNewRoom()
		if ui.frozePlayers and not ui.open then
			A.forEachPlayer(function(p) p.ControlsEnabled = true end)
			ui.frozePlayers = false
		end
	end
	mod:AddCallback(ModCallbacks.MC_POST_NEW_ROOM, mod.altarUiNewRoom)
end
