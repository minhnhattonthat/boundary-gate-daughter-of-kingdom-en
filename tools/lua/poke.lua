-- Write bytes into main RAM once at frame POKE_AT (after --state-in loads), e.g. to test a string in place.
--   emu.py ... --script tools/lua/poke.lua --var POKE_ADDR=0x8017F55F --var "POKE_HEX='41424300'" [--var POKE_AT=5]
local addr = assert(POKE_ADDR, "set --var POKE_ADDR=0x...")
local hex = assert(POKE_HEX, "set --var POKE_HEX='..'")
local at = POKE_AT or 5   -- not frame 1: --state-in may load after the first frame callback
local done = false
L.on_frame(function(f)
  if done or f < at then return end
  done = true
  local mem = PCSX.getMemPtr()
  local base = addr % 0x200000
  for i = 0, #hex / 2 - 1 do
    mem[base + i] = tonumber(hex:sub(i * 2 + 1, i * 2 + 2), 16)
  end
  L.log(string.format("poked %d bytes at %08X", #hex / 2, addr))
end)
