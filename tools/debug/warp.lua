-- Cold-boot warp for Boundary Gate, no debugger needed (docs/re/debug.md). Normally run by tools/debug/warp.py from
-- tools/debug/scenes.tsv, after the boot route (tools/routes/boot.txt: title -> New Game). Every step waits on RAM.
--
-- Globals (--var):
--   KIND  'event'  New Game loads EVENT<EVENT> instead of EVENT00: the exe's path literal is patched in RAM.
--         'loc'    New Game ends EVENT00 at once (op 0x19 written at the script pointer), then on map 0 the leftover
--                  DEB window (debug flag 0x8012B408) changes map; LOC (location word: 0x100|map, 0x200|room,
--                  0x800 ending, 0x1000 reset) with X, Y, DIR and return map RET replaces it during the fade, before
--                  the main loop (0x80016AD4) reads it. The game's own loader does the rest.
--         'battle' as 'loc' to map 0, then the DEB window's battle line with formation BATTLE (1-140).
--   VARS  '0=50,1b=5' story vars (u32 at 0x80126800 + 4*i, hex index) written at New Game and on arrival.
--   DEBUG 1 = keep the debug flag on (DEB in the field menu) for the whole run.
--   GOD   1 = no party member's HP may drop below its value at arrival (for --mash routes through fights).
--   HP    n = set every party member's HP to n on arrival (HP=1 + a battle + mash = game over).
--   STATUS '1,2,4' status byte of each party slot in order, set on arrival (status-effect rows).
--   WIPE_HOLD n = with HP: end the run n frames after every member's HP hits 0 (Game Over banner ~230-530 later).
--   AFTER '600 -;6 square;45 -' route steps (frames buttons) pressed after arrival (menus, shops).
--   HOLD  frames to run after arrival and AFTER, then the run ends here: final.png (+ --state-out) is that frame.
--   PRESHOT 1 = a shot f<frame>.png on the frame each AFTER press starts (a finished text page before it moves on).
-- Log lines "warp: ..." record each step; warp.py requires "warp: arrived". A FAILED line ends the run at once.
local M = PCSX.getMemPtr()
local function r8(a) return M[a % 0x200000] end
local function w8(a, v) M[a % 0x200000] = v % 256 end
local function r16(a) return r8(a) + r8(a + 1) * 256 end
local function w16(a, v) w8(a, v); w8(a + 1, math.floor(v / 256)) end
local function r32(a) return r16(a) + r16(a + 2) * 65536 end
local function w32(a, v) w16(a, v % 65536); w16(a + 2, math.floor(v / 65536)) end
local function rstr(a, n) local t = {} for i = 0, n - 1 do t[#t + 1] = string.char(r8(a + i)) end return table.concat(t) end

local LOCW, RETW, POSX, POSY, POSD = 0x80126C0A, 0x80126C0C, 0x80126C04, 0x80126C06, 0x80126C08
local VARBASE, SCRBASE, SCRPTR = 0x80126800, 0x80126468, 0x800CF250
local EVPATH, DBGFLAG, INBATTLE = 0x8001011C, 0x8012B408, 0x80129C00
local EV00 = 'EVMES0\\EVENT00.BIN'

local function set_vars()
  if not VARS or VARS == '' then return end
  for k, v in VARS:gmatch('(%x+)=(%d+)') do w32(VARBASE + 4 * tonumber(k, 16), tonumber(v)) end
end
local preshot = {}   -- frame -> true: PRESHOT shots, one per AFTER press
local function log(s) L.log(string.format('warp: %s (frame %d)', s, L.frame)) end
local function finish()
  L.shot('final.png'); L.log('final frame ' .. L.frame)
  if STATE_OUT then L.save_state(STATE_OUT) end
  L.finish(0)
end

-- DEB window locals: [value, 0, max] word triples at sp+0x130 (map, max 0x53), +0x13C (X, 0x17), +0x148 (Y, 0x17),
-- +0x154 (dir, 3), +0x160 (battle, 0x8C), found by the max pattern in the stack while the window waits for input.
local function deb_locals()
  for a = 0x801F0000, 0x801FFF00, 4 do
    if r32(a) == 0x53 and r32(a + 12) == 0x17 and r32(a + 24) == 0x17 and r32(a + 36) == 3 and r32(a + 48) == 0x8C then
      return a - 8
    end
  end
end
local function press_seq(seq)   -- 'square down*6 circle': each press 6 frames, then 30 idle
  for k in seq:gmatch('%S+') do
    local key, n = k:match('^(%a+)%*?(%d*)$')
    for _ = 1, tonumber(n) or 1 do L.press(key, 6); L.press('-', 30) end
  end
end

local stage, t0, lastptr, still, deb = 'boot', 0, nil, 0, nil
local marker = (KIND == 'loc' and LOC and LOC >= 0x101 and LOC <= 0x153) and (LOC % 256) or 0x53

-- Party: count u16 0x80126C0E, member order bytes 0x80126C10; member i at 0x80126C14 + 60*i: +2 HP (s16), +6 MP,
-- +8 EXP (u32), +0xC LV (u8). Max HP is computed (0x8002A598), not stored.
local PARTY_N, PARTY_ORDER, MEMBER = 0x80126C0E, 0x80126C10, 0x80126C14
local function members()
  local t = {}
  for s = 0, math.min(r16(PARTY_N), 4) - 1 do
    local i = r8(PARTY_ORDER + s)
    if i < 5 then t[#t + 1] = MEMBER + 60 * i + 2 end
  end
  return t
end
local godhp = {}

local function arrived(what)
  log('arrived ' .. what)
  local st = {}
  for v in (STATUS or ''):gmatch('%d+') do st[#st + 1] = tonumber(v) end
  for k, a in ipairs(members()) do
    if HP then w16(a, HP) end
    if st[k] then w8(a + 0x0B, st[k]) end   -- status byte 0x80126C21 + 0x3C*member (HP is at +2)
    godhp[a] = r16(a)
  end
  local at = L.frame
  for step in (AFTER or ''):gmatch('[^;]+') do
    local n, keys = step:match('^%s*(%d+)%s+(%S+)')
    if n then
      if PRESHOT == 1 and keys ~= '-' then preshot[at] = true end   -- the screen just before this press
      L.press(keys, tonumber(n)); at = at + tonumber(n)
    end
  end
  stage = 'after'
end
local function failed(why) log('FAILED: ' .. why); finish() end

L.on_frame(function(f)
  if preshot[f] then L.shot(string.format('f%06d.png', f)); preshot[f] = nil end
  if DEBUG == 1 or stage == 'field' or stage == 'deb' then w16(DBGFLAG, 1) end
  if GOD == 1 then
    for a, hp in pairs(godhp) do if r16(a) < hp or r16(a) >= 0x8000 then w16(a, hp) end end
  end
  local loc = r16(LOCW)
  if stage == 'boot' then
    if KIND == 'event' and rstr(EVPATH, #EV00) == EV00 then
      local p = string.format('EVMES%d\\EVENT%02d.BIN', math.floor(EVENT / 25), EVENT)
      for i = 1, #p do w8(EVPATH + i - 1, p:byte(i)) end
      w8(EVPATH + #p, 0)
    end
    if loc == 0x400 then   -- New Game: set by 0x80016A84 just before the event file loads
      set_vars(); stage, t0 = 'newgame', f
      log('new game' .. (KIND == 'event' and (', loading ' .. rstr(EVPATH, #EV00)) or ''))
    end
  elseif stage == 'newgame' then
    local ptr, base = r32(SCRPTR), r32(SCRBASE)
    if ptr == lastptr then still = still + 1 else still = 0 end
    lastptr = ptr
    local running = base >= 0x80010000 and ptr > base and ptr < base + 0x100000
    if KIND == 'event' then
      if running and still >= 4 then arrived('event ' .. EVENT) end
    elseif running and ptr == base + 0x1C1 and r8(base + 0x1C0) == 0x1E then
      -- EVENT00 starts "1e 00" (a fade that waits, then reads its operand: ptr sits on the operand). The next op
      -- byte at +0x1C2 becomes 0x19 = end script, so the prologue ends after that fade.
      w8(base + 0x1C2, 0x19)
      log('EVENT00 cut after its first op')
      stage, t0 = 'skip', f
    elseif running and ptr > base + 0x1C2 then
      failed(string.format('EVENT00 already past its first op (script +%X)', ptr - base))
    end
  elseif stage == 'skip' then   -- New Game puts the party on map 0 at 12,5 (0x80016AA8)
    if loc == 0x100 then stage, t0 = 'map0', f end
  elseif stage == 'map0' and f - t0 >= 240 then
    if KIND == 'loc' and LOC == 0x100 then
      w16(POSX, X or 12); w16(POSY, Y or 5); w16(POSD, DIR or 2); set_vars()
      stage, t0 = 'arrive', f
    else
      press_seq('square down*6 circle'); stage, t0 = 'field', f
    end
  elseif stage == 'field' then
    deb = deb_locals()
    if deb then
      log(string.format('DEB window, locals at %08X', deb))
      if KIND == 'battle' then
        w32(deb + 0x30, BATTLE); press_seq('down*4 circle')
      else
        w32(deb, marker)
        if X then w32(deb + 12, X) end
        if Y then w32(deb + 24, Y) end
        if DIR then w32(deb + 36, DIR) end
        press_seq('circle cross')   -- confirm the map line, close the field menu: the field loop exits
      end
      stage, t0 = 'deb', f
    elseif f - t0 > 900 then failed('DEB window never opened') end
  elseif stage == 'deb' then
    if KIND == 'battle' then
      if deb and r32(deb + 8) == 0x53 then w32(deb + 0x30, BATTLE) end   -- keep it until the window closes
      if r8(INBATTLE) == 1 then set_vars(); arrived('battle ' .. BATTLE) end
    elseif loc == 0x100 + marker then   -- DEB stored marker|0x100; swap in the real location during the fade
      w16(LOCW, LOC); w16(POSX, X or 0); w16(POSY, Y or 0); w16(POSD, DIR or 0)
      if RET then w16(RETW, RET) end
      set_vars()
      log(string.format('location %04X x %d y %d dir %d ret %04X', LOC, X or 0, Y or 0, DIR or 0, RET or 0))
      stage, t0 = 'arrive', f
    elseif deb and r32(deb + 8) == 0x53 then
      w32(deb, marker)
    end
    if stage == 'deb' and f - t0 > 1200 then failed('location never changed') end
  elseif stage == 'arrive' then
    if r16(LOCW) ~= LOC then failed(string.format('location is %04X', r16(LOCW)))
    elseif f - t0 >= 120 then arrived(string.format('loc %04X', LOC)) end
  elseif stage == 'after' then
    -- no AFTER steps: hold from arrival (the boot route's idle tail may still be queued)
    if L.route_done() or (AFTER or '') == '' then stage, t0 = 'hold', f end
  elseif stage == 'hold' then
    if WIPE_HOLD and HP and next(godhp) then   -- game over scene: end WIPE_HOLD frames after the party is wiped
      local alive = false
      for a in pairs(godhp) do if r16(a) > 0 and r16(a) < 0x8000 then alive = true end end
      if not alive then log('party wiped'); stage, t0, HOLD = 'hold2', f, WIPE_HOLD end
    end
    if stage == 'hold' and f - t0 >= (HOLD or 60) then finish() end
  elseif stage == 'hold2' then
    if f - t0 >= HOLD then finish() end
  end
end)
